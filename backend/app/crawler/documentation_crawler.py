"""Enhanced web crawler for documentation hosting.

This module extends the basic crawler to support full documentation hosting,
including HTML preservation, asset downloading, and site structure extraction.
"""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from urllib.parse import urljoin, urlparse, urlunparse
from pathlib import Path
import mimetypes

import httpx
from bs4 import BeautifulSoup, Tag
import structlog
import trafilatura

from app.crawler.crawler import WebCrawler
from app.storage.s3_client import S3Client
from app.db import get_db_pool
import asyncpg

logger = structlog.get_logger()


class DocumentationCrawler(WebCrawler):
    """Enhanced crawler for full documentation hosting.
    
    This crawler extends the base WebCrawler with capabilities to:
    - Store full HTML content
    - Download and store documentation assets (images)
    - Extract and preserve site navigation structure
    - Track page relationships and links
    - Support incremental updates
    """
    
    def __init__(
        self,
        max_pages: int = 1000,
        rate_limit: float = 0.5,  # Faster for documentation sites
        timeout: int = 30,
        follow_links: bool = True,
        respect_robots_txt: bool = True,
        download_assets: bool = True,
        asset_types: Optional[Set[str]] = None
    ):
        super().__init__(max_pages, rate_limit, timeout, follow_links, respect_robots_txt)
        self.download_assets = download_assets
        self.asset_types = asset_types or {
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/svg+xml',
            'image/webp', 'application/pdf', 'video/mp4', 'video/webm'
        }
        self.s3_client = S3Client()
        self.site: Optional[Dict[str, Any]] = None
        self.page_map: Dict[str, Dict[str, Any]] = {}  # URL to Page mapping
        self.asset_map: Dict[str, Dict[str, Any]] = {}  # URL to Asset mapping
        self.navigation_items: List[Dict[str, Any]] = []
        self.page_links: List[Tuple[str, str, str, str]] = []  # (from_url, to_url, text, context)
        
    async def crawl_documentation(
        self, 
        start_url: str, 
        site_id: Optional[str] = None,
        incremental: bool = False,
        progress_callback=None
    ) -> Dict:
        """Crawl a documentation site and store all content.
        
        Args:
            start_url: The URL to start crawling from
            site_id: Existing site ID for incremental updates
            incremental: Whether to only update changed pages
            progress_callback: Async callback for progress updates
            
        Returns:
            Dict containing crawl results and statistics
        """
        # Parse the start URL
        parsed = urlparse(start_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        host = parsed.netloc
        
        # Get database pool
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Get or create site
            if site_id:
                site_row = await conn.fetchrow(
                    "SELECT * FROM sites WHERE id = $1", site_id
                )
                if not site_row:
                    raise ValueError(f"Site with ID {site_id} not found")
                self.site = dict(site_row)
            else:
                # Check if site already exists
                site_row = await conn.fetchrow(
                    "SELECT * FROM sites WHERE host = $1", host
                )
                
                if site_row:
                    self.site = dict(site_row)
                else:
                    # Create new site
                    site_row = await conn.fetchrow(
                        """
                        INSERT INTO sites (host, title, crawl_settings)
                        VALUES ($1, $2, $3)
                        RETURNING *
                        """,
                        host,
                        f"Documentation for {host}",
                        json.dumps({
                            "max_pages": self.max_pages,
                            "rate_limit": self.rate_limit,
                            "follow_links": self.follow_links,
                            "download_assets": self.download_assets
                        })
                    )
                    self.site = dict(site_row)
            
            # Create crawl history entry
            crawl_history_row = await conn.fetchrow(
                """
                INSERT INTO crawl_history (site_id, crawl_job_id, started_at)
                VALUES ($1, NULL, $2)
                RETURNING id
                """,
                self.site['id'],
                datetime.utcnow()
            )
            crawl_history_id = crawl_history_row['id']
            
            # Load existing pages for incremental updates
            if incremental:
                await self._load_existing_pages(conn)
            
            # Perform the crawl
            crawl_result = await self._crawl_with_storage(
                start_url, base_url, host, conn, crawl_history_id, progress_callback
            )
            
            # Update crawl history
            await conn.execute(
                """
                UPDATE crawl_history
                SET completed_at = $1, pages_added = $2, pages_updated = $3, stats = $4
                WHERE id = $5
                """,
                datetime.utcnow(),
                crawl_result['pages_added'],
                crawl_result['pages_updated'],
                json.dumps({
                    'total_pages': crawl_result['pages_crawled'],
                    'total_assets': len(self.asset_map),
                    'bytes_downloaded': crawl_result['bytes_downloaded'],
                    'errors': crawl_result.get('errors', [])
                }),
                crawl_history_id
            )
            
            # Update site statistics
            total_pages = await self._count_site_pages(conn)
            total_size = await self._calculate_site_size(conn)
            
            await conn.execute(
                """
                UPDATE sites
                SET last_crawled_at = $1, total_pages = $2, total_size_bytes = $3
                WHERE id = $4
                """,
                datetime.utcnow(),
                total_pages,
                total_size,
                self.site['id']
            )
            
            # Build navigation structure
            await self._build_navigation_structure(conn)
            
            # Save page links
            await self._save_page_links(conn)
            
            # Send completion notification via WebSocket
            from app.api.crawl_websocket import send_crawl_completed
            await send_crawl_completed(
                host=host,
                pages_crawled=crawl_result['pages_crawled'],
                pages_added=crawl_result['pages_added'],
                pages_updated=crawl_result['pages_updated'],
                errors=crawl_result.get('errors', [])
            )
            
            return {
                'site_id': str(self.site['id']),
                'host': host,
                'pages_crawled': crawl_result['pages_crawled'],
                'pages_added': crawl_result['pages_added'],
                'pages_updated': crawl_result['pages_updated'],
                'assets_downloaded': len(self.asset_map),
                'bytes_downloaded': crawl_result['bytes_downloaded'],
                'crawl_complete': True,
                'errors': crawl_result.get('errors', [])
            }
    
    async def _crawl_with_storage(
        self,
        start_url: str,
        base_url: str,
        host: str,
        conn: asyncpg.Connection,
        crawl_history_id: str,
        progress_callback
    ) -> Dict:
        """Perform the actual crawl with content storage."""
        # Initialize counters
        pages_crawled = 0
        pages_added = 0
        pages_updated = 0
        bytes_downloaded = 0
        errors = []
        
        # Initialize crawl queue
        queue = [start_url]
        processed_urls = set()
        
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            while queue and pages_crawled < self.max_pages:
                url = queue.pop(0)
                
                # Skip if already processed
                if url in processed_urls:
                    continue
                
                processed_urls.add(url)
                
                # Skip if URL is an asset
                if self._is_asset_url(url):
                    continue
                
                # Check robots.txt
                if not self._can_fetch(url):
                    logger.info("Blocked by robots.txt", url=url)
                    continue
                
                try:
                    # Fetch the page
                    response = await client.get(url)
                    pages_crawled += 1
                    
                    if response.status_code == 200:
                        # Check content type
                        content_type = response.headers.get('content-type', '').lower()
                        if not any(ct in content_type for ct in ['text/html', 'application/xhtml']):
                            logger.info("Skipping non-HTML content", url=url, content_type=content_type)
                            continue
                        
                        html_content = response.text
                        content_size = len(html_content.encode('utf-8'))
                        bytes_downloaded += content_size
                        
                        # Parse the page
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Process and store the page
                        page, is_new = await self._process_and_store_page(
                            conn, url, html_content, soup, response.headers
                        )
                        
                        if is_new:
                            pages_added += 1
                        else:
                            pages_updated += 1
                        
                        # Extract and queue links
                        if self.follow_links and pages_crawled < self.max_pages:
                            links = self._extract_links(soup, base_url, host)
                            for link in links:
                                if link not in processed_urls and link not in queue:
                                    queue.append(link)
                        
                        # Download assets if enabled
                        if self.download_assets:
                            await self._download_page_assets(conn, page, soup, base_url, client)
                        
                        # Extract navigation info
                        self._extract_navigation_info(page, soup)
                        
                        # Extract page links
                        self._extract_page_links(page, soup, base_url, host)
                        
                    else:
                        logger.warning("Failed to fetch page", url=url, status=response.status_code)
                        errors.append({
                            'url': url,
                            'error': f'HTTP {response.status_code}',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        
                except Exception as e:
                    logger.error("Error crawling page", url=url, error=str(e))
                    errors.append({
                        'url': url,
                        'error': str(e),
                        'timestamp': datetime.utcnow().isoformat()
                    })
                
                # Progress callback and WebSocket update
                pages_discovered = len(processed_urls) + len(queue)
                if progress_callback:
                    await progress_callback(
                        pages_crawled=pages_crawled,
                        pages_discovered=pages_discovered,
                        pages_added=pages_added,
                        pages_updated=pages_updated,
                        bytes_downloaded=bytes_downloaded,
                        current_url=url
                    )
                
                # Send WebSocket update
                from app.api.crawl_websocket import send_crawl_progress
                await send_crawl_progress(
                    host=host,
                    pages_crawled=pages_crawled,
                    pages_discovered=pages_discovered,
                    pages_added=pages_added,
                    pages_updated=pages_updated,
                    current_url=url,
                    bytes_downloaded=bytes_downloaded
                )
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit)
        
        return {
            'pages_crawled': pages_crawled,
            'pages_added': pages_added,
            'pages_updated': pages_updated,
            'bytes_downloaded': bytes_downloaded,
            'errors': errors
        }
    
    async def _process_and_store_page(
        self,
        conn: asyncpg.Connection,
        url: str,
        html_content: str,
        soup: BeautifulSoup,
        headers: Dict
    ) -> Tuple[Dict[str, Any], bool]:
        """Process a page and store its content."""
        # Calculate content hash
        content_hash = hashlib.sha256(html_content.encode()).hexdigest()
        
        # Extract path from URL
        parsed = urlparse(url)
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"
        
        # Check if page already exists
        existing_page = self.page_map.get(url)
        if existing_page and existing_page['content_hash'] == content_hash:
            # Content hasn't changed
            return existing_page, False
        
        # Extract metadata
        title = self._extract_title(soup)
        description = self._extract_description(soup)
        
        # Extract text content using Trafilatura
        markdown_content = self._extract_content_with_trafilatura(html_content, soup)
        
        # Prepare extracted text for search (first 10KB)
        extracted_text = markdown_content[:10240] if markdown_content else ""
        
        # Store HTML in S3
        # Normalize path to avoid double slashes
        normalized_path = path.rstrip('/') if path != '/' else ''
        html_key = f"sites/{self.site['host']}/pages{normalized_path}/index.html"
        markdown_key = f"sites/{self.site['host']}/pages{normalized_path}/content.md"
        
        try:
            await self.s3_client.upload_content(
                html_content.encode('utf-8'),
                html_key,
                content_type='text/html'
            )
            
            # Store markdown in S3
            if markdown_content:
                await self.s3_client.upload_content(
                    markdown_content.encode('utf-8'),
                    markdown_key,
                    content_type='text/markdown'
                )
        except Exception as e:
            logger.warning("Failed to upload to S3, storing inline", error=str(e))
            # Store content inline in database as fallback
            html_key = None
            markdown_key = None
        
        # Create or update page
        if existing_page:
            # Update existing page
            page_row = await conn.fetchrow("""
                UPDATE pages
                SET title = $1, description = $2, content_hash = $3,
                    html_storage_key = $4, markdown_storage_key = $5,
                    html_size_bytes = $6, markdown_size_bytes = $7,
                    extracted_text = $8, headers = $9, crawled_at = $10,
                    updated_at = $10
                WHERE id = $11
                RETURNING *
            """, title, description, content_hash, html_key,
                markdown_key if markdown_content else None,
                len(html_content.encode('utf-8')),
                len(markdown_content.encode('utf-8')) if markdown_content else None,
                extracted_text, json.dumps(dict(headers)), datetime.utcnow(), existing_page['id'])
            
            page = dict(page_row)
            self.page_map[url] = page
            is_new = False
        else:
            # Create new page
            page_row = await conn.fetchrow("""
                INSERT INTO pages (
                    site_id, url, path, title, description, content_hash,
                    html_storage_key, markdown_storage_key, html_size_bytes,
                    markdown_size_bytes, extracted_text, headers, crawled_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING *
            """, self.site['id'], url, path, title, description, content_hash,
                html_key, markdown_key if markdown_content else None,
                len(html_content.encode('utf-8')),
                len(markdown_content.encode('utf-8')) if markdown_content else None,
                extracted_text, json.dumps(dict(headers)), datetime.utcnow())
            
            page = dict(page_row)
            self.page_map[url] = page
            is_new = True
        
        return page, is_new
    
    async def _download_page_assets(
        self,
        conn: asyncpg.Connection,
        page: Dict[str, Any],
        soup: BeautifulSoup,
        base_url: str,
        client: httpx.AsyncClient
    ):
        """Download assets referenced by a page."""
        # Find all asset references
        asset_tags = {
            'img': 'src',
            'video': 'src',
            'source': 'src',
            'link': 'href'  # For stylesheets with images
        }
        
        for tag_name, attr_name in asset_tags.items():
            for tag in soup.find_all(tag_name):
                asset_url = tag.get(attr_name)
                if not asset_url:
                    continue
                
                # Make URL absolute
                asset_url = urljoin(base_url, asset_url)
                parsed = urlparse(asset_url)
                
                # Skip external assets
                if parsed.netloc != self.site['host']:
                    continue
                
                # Skip if already downloaded
                if asset_url in self.asset_map:
                    continue
                
                # Download the asset
                try:
                    response = await client.get(asset_url)
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '')
                        
                        # Check if it's a supported asset type
                        if not any(ct in content_type for ct in self.asset_types):
                            continue
                        
                        # Store the asset
                        await self._store_asset(
                            conn, asset_url, response.content, content_type
                        )
                        
                except Exception as e:
                    logger.warning("Failed to download asset", url=asset_url, error=str(e))
    
    async def _store_asset(
        self,
        conn: asyncpg.Connection,
        url: str,
        content: bytes,
        content_type: str
    ):
        """Store an asset in S3 and database."""
        # Calculate hash
        content_hash = hashlib.sha256(content).hexdigest()
        
        # Extract path
        parsed = urlparse(url)
        path = parsed.path or '/'
        
        # Normalize path to avoid double slashes
        normalized_path = path.rstrip('/') if path != '/' else ''
        
        # Generate S3 key
        storage_key = f"sites/{self.site['host']}/assets{normalized_path}"
        
        # Upload to S3
        await self.s3_client.upload_content(content, storage_key, content_type)
        
        # Create or update asset record
        try:
            asset_row = await conn.fetchrow("""
                INSERT INTO assets (
                    site_id, url, path, content_type, storage_key,
                    size_bytes, content_hash, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (site_id, path) DO UPDATE SET
                    url = EXCLUDED.url,
                    content_type = EXCLUDED.content_type,
                    storage_key = EXCLUDED.storage_key,
                    size_bytes = EXCLUDED.size_bytes,
                    content_hash = EXCLUDED.content_hash
                RETURNING *
            """, self.site['id'], url, path, content_type, storage_key,
                len(content), content_hash, json.dumps({}))
            
            asset = dict(asset_row)
            self.asset_map[url] = asset
        except Exception as e:
            logger.error("Failed to store asset", url=url, error=str(e))
    
    def _extract_navigation_info(self, page: Dict[str, Any], soup: BeautifulSoup):
        """Extract navigation information from the page."""
        # Look for common navigation patterns
        nav_selectors = [
            'nav', '.nav', '#nav', '.navigation', '#navigation',
            '.sidebar', '#sidebar', '.toc', '#toc', '.menu', '#menu'
        ]
        
        for selector in nav_selectors:
            nav_elements = soup.select(selector)
            for nav in nav_elements:
                # Extract navigation items
                links = nav.find_all('a')
                for link in links:
                    href = link.get('href')
                    if href:
                        self.navigation_items.append({
                            'page_id': page['id'],
                            'title': link.get_text(strip=True),
                            'url': href,
                            'path': urlparse(href).path
                        })
    
    def _extract_page_links(self, page: Dict[str, Any], soup: BeautifulSoup, base_url: str, host: str):
        """Extract internal links from the page content."""
        # Find all links in the main content
        content_areas = soup.select('main, article, .content, #content, .main-content')
        if not content_areas:
            content_areas = [soup]
        
        for content in content_areas:
            for link in content.find_all('a'):
                href = link.get('href')
                if not href:
                    continue
                
                # Make absolute
                absolute_url = urljoin(base_url, href)
                parsed = urlparse(absolute_url)
                
                # Only track internal links
                if parsed.netloc == host:
                    link_text = link.get_text(strip=True)
                    # Get surrounding context (parent paragraph or container)
                    parent = link.parent
                    context = parent.get_text(strip=True) if parent else ""
                    
                    self.page_links.append((
                        page['url'],
                        absolute_url,
                        link_text[:255],  # Limit text length
                        context[:500]  # Limit context length
                    ))
    
    async def _build_navigation_structure(self, conn: asyncpg.Connection):
        """Build hierarchical navigation structure from crawled pages."""
        # This is a simplified version - in production, you'd want more
        # sophisticated navigation extraction and organization
        
        # Group pages by path depth
        pages_by_depth = {}
        for page in self.page_map.values():
            depth = page['path'].count('/')
            if depth not in pages_by_depth:
                pages_by_depth[depth] = []
            pages_by_depth[depth].append(page)
        
        # Create navigation entries
        nav_map = {}  # path -> navigation row
        
        for depth in sorted(pages_by_depth.keys()):
            for page in pages_by_depth[depth]:
                # Find parent
                parent_path = str(Path(page['path']).parent)
                if parent_path == '.':
                    parent_path = '/'
                
                parent_nav = nav_map.get(parent_path)
                parent_id = parent_nav['id'] if parent_nav else None
                
                # Create navigation entry
                nav_row = await conn.fetchrow("""
                    INSERT INTO site_navigation (
                        site_id, page_id, parent_id, title, path, order_index, level
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING *
                """, self.site['id'], page['id'], parent_id,
                    page['title'] or Path(page['path']).name,
                    page['path'], 0, depth)
                
                nav = dict(nav_row)
                nav_map[page['path']] = nav
    
    async def _save_page_links(self, conn: asyncpg.Connection):
        """Save extracted page links to database."""
        # Convert URLs to page IDs
        url_to_page = {page['url']: page for page in self.page_map.values()}
        
        for from_url, to_url, link_text, context in self.page_links:
            from_page = url_to_page.get(from_url)
            to_page = url_to_page.get(to_url)
            
            if from_page and to_page and from_page['id'] != to_page['id']:
                # Check if link already exists
                existing = await conn.fetchrow("""
                    SELECT id FROM page_links
                    WHERE from_page_id = $1 AND to_page_id = $2
                """, from_page['id'], to_page['id'])
                
                if not existing:
                    await conn.execute("""
                        INSERT INTO page_links (from_page_id, to_page_id, link_text, link_context)
                        VALUES ($1, $2, $3, $4)
                    """, from_page['id'], to_page['id'], link_text, context)
    
    async def _load_existing_pages(self, conn: asyncpg.Connection):
        """Load existing pages for incremental updates."""
        rows = await conn.fetch("""
            SELECT * FROM pages WHERE site_id = $1
        """, self.site['id'])
        
        for row in rows:
            page = dict(row)
            self.page_map[page['url']] = page
    
    async def _count_site_pages(self, conn: asyncpg.Connection) -> int:
        """Count total pages for a site."""
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM pages
            WHERE site_id = $1 AND is_active = true
        """, self.site['id'])
        return count or 0
    
    async def _calculate_site_size(self, conn: asyncpg.Connection) -> int:
        """Calculate total size of site content."""
        # Sum page sizes
        page_size = await conn.fetchval("""
            SELECT COALESCE(SUM(COALESCE(html_size_bytes, 0) + COALESCE(markdown_size_bytes, 0)), 0)
            FROM pages WHERE site_id = $1
        """, self.site['id']) or 0
        
        # Sum asset sizes
        asset_size = await conn.fetchval("""
            SELECT COALESCE(SUM(size_bytes), 0)
            FROM assets WHERE site_id = $1
        """, self.site['id']) or 0
        
        return page_size + asset_size
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page title from HTML."""
        # Try different title sources
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        # Try h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        # Try og:title
        og_title = soup.find('meta', {'property': 'og:title'})
        if og_title and og_title.get('content'):
            return og_title['content']
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page description from HTML."""
        # Try meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content']
        
        # Try og:description
        og_desc = soup.find('meta', {'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            return og_desc['content']
        
        return None
    
    def _extract_content_with_trafilatura(self, html_content: str, soup: BeautifulSoup) -> Optional[str]:
        """Extract clean text content using Trafilatura."""
        try:
            # Use trafilatura to extract clean content
            extracted = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                include_images=False,
                include_links=True,
                output_format='markdown'
            )
            return extracted
        except Exception as e:
            logger.warning("Failed to extract content with trafilatura", error=str(e))
            # Fallback to basic text extraction
            return soup.get_text(strip=True, separator=' ')[:10000]