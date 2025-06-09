"""Main crawler implementation with BFS frontier and politeness controls."""

import asyncio
import xml.etree.ElementTree as ET
from collections import deque
from datetime import datetime, timedelta
from typing import Set, Dict, List, Optional, Deque
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
import structlog
from pydantic import BaseSettings

from .detector import ChangeDetector
from .fetcher import PageFetcher
from .storage import StorageAdapter, PageRecord
from .manifest import LLMManifest

logger = structlog.get_logger()


class CrawlerSettings(BaseSettings):
    """Crawler configuration settings."""
    
    database_url: str
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    proxy_pool_url: Optional[str] = None
    capsolver_api_key: Optional[str] = None
    crawl_rate_limit: int = 4  # requests per minute per host
    max_depth: int = 10
    max_pages_per_host: int = 10000
    
    class Config:
        env_file = ".env"


class URLFrontier:
    """Manages the URL frontier with BFS strategy."""
    
    def __init__(self, seed_urls: List[str]):
        self.queue: Deque[Tuple[str, int]] = deque()  # (url, depth)
        self.seen: Set[str] = set()
        self.host_last_access: Dict[str, datetime] = {}
        
        # Add seed URLs
        for url in seed_urls:
            self.add(url, 0)
            
    def add(self, url: str, depth: int) -> bool:
        """Add URL to frontier if not seen."""
        normalized = self._normalize_url(url)
        if normalized not in self.seen:
            self.seen.add(normalized)
            self.queue.append((normalized, depth))
            return True
        return False
        
    def get_next(self, rate_limit: int) -> Optional[Tuple[str, int]]:
        """Get next URL respecting rate limits."""
        now = datetime.utcnow()
        min_interval = timedelta(seconds=60 / rate_limit)
        
        # Try to find a URL we can crawl now
        for _ in range(len(self.queue)):
            if not self.queue:
                return None
                
            url, depth = self.queue.popleft()
            host = urlparse(url).netloc
            
            last_access = self.host_last_access.get(host)
            if last_access and (now - last_access) < min_interval:
                # Too soon, put it back
                self.queue.append((url, depth))
            else:
                # Can crawl this one
                self.host_last_access[host] = now
                return url, depth
                
        return None
        
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        # Remove fragment
        url = url.split('#')[0]
        # Remove trailing slash
        url = url.rstrip('/')
        # Convert to lowercase
        url = url.lower()
        return url
        
    def size(self) -> int:
        """Get frontier size."""
        return len(self.queue)


class Crawler:
    """Main crawler orchestrator."""
    
    def __init__(self, settings: CrawlerSettings):
        self.settings = settings
        self.storage = StorageAdapter(
            db_url=settings.database_url,
            s3_endpoint=settings.s3_endpoint,
            s3_access_key=settings.s3_access_key,
            s3_secret_key=settings.s3_secret_key,
            s3_bucket=settings.s3_bucket,
        )
        self.fetcher = PageFetcher(
            proxy_url=settings.proxy_pool_url,
            capsolver_key=settings.capsolver_api_key,
        )
        self.robot_parsers: Dict[str, RobotFileParser] = {}
        self.manifest_generator = LLMManifest(self.storage)
        
    async def initialize(self):
        """Initialize crawler components."""
        await self.storage.initialize()
        await self.fetcher.initialize()
        
    async def close(self):
        """Clean up resources."""
        await self.storage.close()
        await self.fetcher.close()
        
    async def crawl_host(self, host: str) -> Dict[str, any]:
        """Crawl a single host."""
        logger.info("Starting crawl", host=host)
        
        # Start crawl session
        session_id = await self.storage.start_crawl_session(host)
        
        # Initialize frontier with seed URLs
        seed_urls = [
            f"https://{host}/",
            f"https://{host}/index.html",
        ]
        frontier = URLFrontier(seed_urls)
        
        # Fetch robots.txt
        await self._load_robots_txt(host)
        
        # Parse sitemap if available
        await self._parse_sitemap(host, frontier)
        
        # Crawl statistics
        pages_crawled = 0
        pages_changed = 0
        
        try:
            while frontier.size() > 0 and pages_crawled < self.settings.max_pages_per_host:
                # Get next URL
                url_data = frontier.get_next(self.settings.crawl_rate_limit)
                if not url_data:
                    # No URLs available due to rate limiting
                    await asyncio.sleep(1)
                    continue
                    
                url, depth = url_data
                
                # Check robots.txt
                if not self._can_fetch(host, url):
                    logger.debug("Blocked by robots.txt", url=url)
                    continue
                    
                # Check depth limit
                if depth > self.settings.max_depth:
                    logger.debug("Max depth reached", url=url, depth=depth)
                    continue
                    
                # Fetch page
                try:
                    status_code, headers, content, error = await self.fetcher.fetch(url)
                    
                    # Get previous page info
                    prev_info = await self.storage.get_page_info(url)
                    
                    # Check if content changed
                    has_changed, reason = ChangeDetector.has_changed(
                        headers, content, prev_info
                    )
                    
                    # Create page record
                    page = PageRecord(
                        url=url,
                        host=host,
                        content_hash=StorageAdapter.compute_content_hash(
                            ChangeDetector.normalize_html(content)
                        ),
                        etag=headers.get('etag'),
                        last_modified=headers.get('last-modified'),
                        status_code=status_code,
                        headers=headers,
                        crawled_at=datetime.utcnow(),
                        is_blocked=(status_code in [403, 503]),
                        error_message=error,
                    )
                    
                    # Save page
                    was_updated = await self.storage.save_page(page)
                    if was_updated:
                        pages_changed += 1
                        
                    # Save content to S3 if changed
                    if has_changed and content:
                        s3_key = f"pages/{host}/{urlparse(url).path.lstrip('/')}"
                        if not s3_key.endswith('.html'):
                            s3_key += '/index.html'
                        await self.storage.save_to_s3(s3_key, content.encode('utf-8'))
                        
                    # Extract links if successful
                    if status_code == 200 and content:
                        links = self._extract_links(url, content)
                        for link in links:
                            if urlparse(link).netloc == host:
                                frontier.add(link, depth + 1)
                                
                    pages_crawled += 1
                    
                    if pages_crawled % 100 == 0:
                        logger.info(
                            "Crawl progress",
                            host=host,
                            pages_crawled=pages_crawled,
                            pages_changed=pages_changed,
                            frontier_size=frontier.size()
                        )
                        
                except Exception as e:
                    logger.error("Failed to crawl page", url=url, error=str(e))
                    
            # Complete session
            await self.storage.complete_crawl_session(
                session_id, pages_crawled, pages_changed
            )
            
            # Trigger manifest generation
            await self._generate_manifest(host)
            
            return {
                "host": host,
                "pages_crawled": pages_crawled,
                "pages_changed": pages_changed,
                "session_id": session_id,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error("Crawl failed", host=host, error=str(e))
            await self.storage.complete_crawl_session(
                session_id, pages_crawled, pages_changed, status="failed"
            )
            raise
            
    async def _load_robots_txt(self, host: str):
        """Load and parse robots.txt for host."""
        robots_content = await self.fetcher.fetch_robots_txt(host)
        if robots_content:
            parser = RobotFileParser()
            parser.parse(robots_content.splitlines())
            self.robot_parsers[host] = parser
            
    def _can_fetch(self, host: str, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        parser = self.robot_parsers.get(host)
        if parser:
            return parser.can_fetch("*", url)
        return True
        
    async def _parse_sitemap(self, host: str, frontier: URLFrontier):
        """Parse sitemap and add URLs to frontier."""
        sitemap_content = await self.fetcher.fetch_sitemap(host)
        if not sitemap_content:
            return
            
        try:
            root = ET.fromstring(sitemap_content)
            # Handle both sitemap and sitemap index
            namespaces = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Try URLs first
            urls = root.findall('.//sm:url/sm:loc', namespaces)
            for url_elem in urls:
                url = url_elem.text
                if url and urlparse(url).netloc == host:
                    frontier.add(url, 1)
                    
            # Try sitemap index
            sitemaps = root.findall('.//sm:sitemap/sm:loc', namespaces)
            for sitemap_elem in sitemaps:
                # Recursively fetch sub-sitemaps
                # (Implementation would go here)
                pass
                
        except Exception as e:
            logger.warning("Failed to parse sitemap", host=host, error=str(e))
            
    def _extract_links(self, base_url: str, content: str) -> List[str]:
        """Extract links from HTML content."""
        links = []
        soup = BeautifulSoup(content, 'lxml')
        
        for tag in soup.find_all(['a', 'link']):
            href = tag.get('href')
            if href:
                absolute_url = urljoin(base_url, href)
                # Filter out non-HTTP URLs
                if absolute_url.startswith(('http://', 'https://')):
                    links.append(absolute_url)
                    
        return links
        
    async def _generate_manifest(self, host: str):
        """Generate llm.txt manifest for host."""
        await self.manifest_generator.generate_manifest(host)