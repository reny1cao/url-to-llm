"""Simplified web crawler using httpx and BeautifulSoup."""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
import structlog
import trafilatura

logger = structlog.get_logger()


class WebCrawler:
    """Asynchronous web crawler with rate limiting and robots.txt support."""
    
    # Common asset extensions to skip
    ASSET_EXTENSIONS = {
        '.js', '.css', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', 
        '.woff', '.woff2', '.ttf', '.eot', '.otf', '.map', '.json',
        '.pdf', '.zip', '.gz', '.tar', '.mp3', '.mp4', '.avi', '.mov',
        '.webp', '.webm', '.xml', '.txt', '.csv'
    }
    
    # Asset path patterns to skip
    ASSET_PATTERNS = [
        '/assets/', '/static/', '/js/', '/css/', '/images/', '/img/',
        '/fonts/', '/media/', '/files/', '/_next/', '/dist/', '/build/',
        '/public/', '/vendor/', '/node_modules/', '/lib/', '/scripts/'
    ]
    
    def __init__(
        self,
        max_pages: int = 100,
        rate_limit: float = 1.0,  # seconds between requests
        timeout: int = 30,
        follow_links: bool = True,
        respect_robots_txt: bool = True
    ):
        self.max_pages = max_pages
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.follow_links = follow_links
        self.respect_robots_txt = respect_robots_txt
        self.visited_urls: Set[str] = set()
        self.robot_parser: Optional[RobotFileParser] = None
        
    async def crawl(self, start_url: str, progress_callback=None) -> Dict:
        """Crawl a website starting from the given URL."""
        parsed = urlparse(start_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        host = parsed.netloc
        
        # Load robots.txt if required
        if self.respect_robots_txt:
            await self._load_robots_txt(base_url)
        
        # Initialize crawl queue
        queue = [start_url]
        pages = []
        pages_crawled = 0
        pages_failed = 0
        bytes_downloaded = 0
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while queue and pages_crawled < self.max_pages:
                url = queue.pop(0)
                
                # Skip if already visited
                if url in self.visited_urls:
                    continue
                
                # Skip if URL is an asset
                if self._is_asset_url(url):
                    logger.debug("Skipping asset URL", url=url)
                    continue
                    
                self.visited_urls.add(url)
                
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
                        
                        # Skip non-HTML content
                        if not any(ct in content_type for ct in ['text/html', 'application/xhtml']):
                            logger.info("Skipping non-HTML content", url=url, content_type=content_type)
                            continue
                        
                        content = response.text
                        content_size = len(content.encode('utf-8'))
                        bytes_downloaded += content_size
                        
                        # Parse the page
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Extract page data using Trafilatura + our methods
                        content_text = self._extract_content_with_trafilatura(content, soup)
                        
                        page_data = {
                            "url": url,
                            "title": self._extract_title(soup),
                            "description": self._extract_description(soup),
                            "content": content_text,
                            "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
                            "status_code": response.status_code,
                            "content_length": content_size,
                            "crawled_at": datetime.utcnow().isoformat() + "Z"
                        }
                        pages.append(page_data)
                        
                        # Extract links if following links
                        if self.follow_links and pages_crawled < self.max_pages:
                            links = self._extract_links(soup, base_url, host)
                            for link in links:
                                if link not in self.visited_urls and link not in queue:
                                    queue.append(link)
                    else:
                        pages_failed += 1
                        logger.warning("Failed to fetch page", url=url, status=response.status_code)
                        
                except Exception as e:
                    pages_failed += 1
                    logger.error("Error crawling page", url=url, error=str(e))
                
                # Progress callback
                if progress_callback:
                    await progress_callback(
                        pages_crawled=pages_crawled,
                        pages_discovered=len(self.visited_urls) + len(queue),
                        pages_failed=pages_failed,
                        bytes_downloaded=bytes_downloaded,
                        current_url=url
                    )
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit)
        
        return {
            "host": host,
            "pages_crawled": pages_crawled,
            "pages_failed": pages_failed,
            "pages": pages,
            "bytes_downloaded": bytes_downloaded,
            "crawl_complete": True
        }
    
    async def _load_robots_txt(self, base_url: str):
        """Load and parse robots.txt."""
        robots_url = urljoin(base_url, "/robots.txt")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(robots_url)
                if response.status_code == 200:
                    self.robot_parser = RobotFileParser()
                    self.robot_parser.parse(response.text.splitlines())
        except Exception as e:
            logger.warning("Failed to load robots.txt", url=robots_url, error=str(e))
    
    def _can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        if not self.respect_robots_txt or not self.robot_parser:
            return True
        return self.robot_parser.can_fetch("*", url)
    
    def _is_asset_url(self, url: str) -> bool:
        """Check if URL is likely an asset (JS, CSS, image, etc)."""
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        
        # Check extensions
        if any(path_lower.endswith(ext) for ext in self.ASSET_EXTENSIONS):
            return True
        
        # Check path patterns
        if any(pattern in path_lower for pattern in self.ASSET_PATTERNS):
            return True
        
        return False
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title with multiple fallbacks."""
        # Try multiple sources for title
        title = None
        
        # 1. Open Graph title
        og_title = soup.find('meta', property='og:title')
        if og_title:
            title = og_title.get('content', '').strip()
        
        # 2. Twitter title
        if not title:
            twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
            if twitter_title:
                title = twitter_title.get('content', '').strip()
        
        # 3. Regular title tag
        if not title:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
        
        # 4. H1 tag
        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
        
        return title or "Untitled"
    
    def _extract_content_with_trafilatura(self, html_content: str, soup: BeautifulSoup) -> str:
        """Extract content using Trafilatura with fallback to improved extraction."""
        trafilatura_content = None
        
        try:
            # Use Trafilatura for main content extraction
            # It returns clean, readable text in markdown format
            trafilatura_content = trafilatura.extract(
                html_content,
                include_formatting=True,
                include_links=False,
                output_format='markdown',
                target_language='en',
                deduplicate=True,
                include_images=False,
                include_tables=True,
                favor_precision=False  # Balance between precision and recall
            )
            
            if trafilatura_content:
                # Clean up the content a bit
                lines = trafilatura_content.split('\n')
                cleaned_lines = []
                
                for line in lines:
                    line = line.strip()
                    if line:
                        cleaned_lines.append(line)
                
                # Join with proper spacing
                trafilatura_content = '\n\n'.join(cleaned_lines)
                
                # Limit size if needed
                max_size = 20000
                if len(trafilatura_content) > max_size:
                    trafilatura_content = trafilatura_content[:max_size] + "\n\n[Content truncated...]"
                
                logger.info("Successfully extracted content with Trafilatura", 
                           content_length=len(trafilatura_content))
                return trafilatura_content
                
        except Exception as e:
            logger.warning("Trafilatura extraction failed, using fallback", error=str(e))
        
        # Fallback to our improved extraction if Trafilatura fails or returns nothing
        return self._extract_improved_content(soup)
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description with multiple fallbacks."""
        description = None
        
        # 1. Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '').strip()
        
        # 2. Open Graph description
        if not description:
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                description = og_desc.get('content', '').strip()
        
        # 3. Twitter description
        if not description:
            twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
            if twitter_desc:
                description = twitter_desc.get('content', '').strip()
        
        return description or ""
    
    def _extract_improved_content(self, soup: BeautifulSoup) -> str:
        """Extract main content with improved formatting for better readability."""
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 
                            'noscript', 'iframe', 'object', 'embed', 'form', 'button']):
            element.decompose()
        
        # Remove common noise elements by class/id
        noise_selectors = [
            '.nav', '.navigation', '.menu', '.sidebar', '.footer', 
            '.header', '.ads', '.advertisement', '.social', '.share',
            '.comment', '.comments', '#nav', '#navigation',
            '#menu', '#sidebar', '#footer', '#header', '#ads'
        ]
        
        for selector in noise_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        # Try to find main content areas first
        main_content = None
        content_selectors = [
            'main', 'article', '[role="main"]', '.main-content',
            '#main-content', '.content', '#content', '.post-content',
            '.entry-content', '.article-content', '.page-content'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                # Use the largest content area
                main_content = max(elements, key=lambda e: len(e.get_text(strip=True)))
                break
        
        # If no main content found, use body
        if not main_content:
            main_content = soup.find('body') or soup
        
        # Extract structured content
        content_parts = []
        
        # Process elements in order, preserving structure
        for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'blockquote', 'pre']):
            text = element.get_text(strip=True)
            
            if not text or len(text) < 10:  # Skip very short snippets
                continue
            
            # Clean up whitespace
            text = ' '.join(text.split())
            
            # Format based on element type
            if element.name.startswith('h'):
                # Add spacing around headings
                if content_parts:
                    content_parts.append("")  # Empty line before heading
                content_parts.append(text)
                content_parts.append("")  # Empty line after heading
            elif element.name in ['ul', 'ol']:
                # Format lists
                items = element.find_all('li')
                if items:
                    for item in items:
                        item_text = item.get_text(strip=True)
                        if item_text:
                            content_parts.append(f"• {item_text}")
                    content_parts.append("")  # Empty line after list
            elif element.name == 'blockquote':
                # Format blockquotes
                content_parts.append(f"> {text}")
                content_parts.append("")
            elif element.name == 'pre':
                # Preserve code blocks
                content_parts.append("```")
                content_parts.append(text)
                content_parts.append("```")
                content_parts.append("")
            else:
                # Regular paragraphs
                content_parts.append(text)
                if len(text) > 50:  # Add spacing after substantial paragraphs
                    content_parts.append("")
        
        # Join with newlines
        full_text = '\n'.join(content_parts)
        
        # Clean up excessive newlines
        while '\n\n\n' in full_text:
            full_text = full_text.replace('\n\n\n', '\n\n')
        
        # If we didn't get much content, try a simpler extraction
        if len(full_text) < 200:
            simple_text = main_content.get_text(separator='\n', strip=True)
            if len(simple_text) > len(full_text):
                full_text = simple_text
        
        # Limit content size
        max_size = 20000
        if len(full_text) > max_size:
            full_text = full_text[:max_size] + "\n\n[Content truncated...]"
        
        return full_text.strip()
    
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str, host: str) -> List[str]:
        """Extract internal links from the page."""
        links = []
        
        for tag in soup.find_all(['a']):
            href = tag.get('href')
            if href:
                # Convert to absolute URL
                absolute_url = urljoin(base_url, href)
                parsed = urlparse(absolute_url)
                
                # Only include links from the same host
                if parsed.netloc == host and parsed.scheme in ['http', 'https']:
                    # Skip if it's an asset based on extension
                    path_lower = parsed.path.lower()
                    if any(path_lower.endswith(ext) for ext in self.ASSET_EXTENSIONS):
                        continue
                    
                    # Skip if it matches asset patterns
                    if any(pattern in path_lower for pattern in self.ASSET_PATTERNS):
                        continue
                    
                    # Remove fragment
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    if parsed.query:
                        clean_url += f"?{parsed.query}"
                    links.append(clean_url)
        
        return list(set(links))[:50]  # Limit number of links