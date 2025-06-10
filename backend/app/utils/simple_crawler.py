"""Simple web crawler for testing purposes."""

import asyncio
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
import structlog

logger = structlog.get_logger()


class SimpleCrawler:
    """Basic web crawler implementation."""
    
    def __init__(self, max_pages: int = 10, timeout: int = 30):
        self.max_pages = max_pages
        self.timeout = timeout
        
    async def crawl_site(self, url: str) -> Dict:
        """Crawl a website and return basic information."""
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        host = parsed_url.netloc
        
        visited = set()
        to_visit = [url]
        pages = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while to_visit and len(pages) < self.max_pages:
                current_url = to_visit.pop(0)
                
                if current_url in visited:
                    continue
                    
                visited.add(current_url)
                
                try:
                    logger.info("Fetching page", url=current_url)
                    response = await client.get(current_url)
                    
                    if response.status_code == 200:
                        content = response.text
                        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
                        
                        # Parse HTML to extract links and content
                        soup = BeautifulSoup(content, 'html.parser')
                        title = soup.find('title')
                        title_text = title.get_text(strip=True) if title else "No title"
                        
                        # Extract main content
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.extract()
                        
                        # Get text content
                        text_content = soup.get_text(separator=' ', strip=True)
                        # Keep more content - 2000 chars for summary, full content for manifest
                        text_summary = text_content[:2000] + "..." if len(text_content) > 2000 else text_content
                        # Also store full content for manifest generation
                        full_content = text_content[:10000] + "..." if len(text_content) > 10000 else text_content
                        
                        # Extract meta description
                        meta_desc = soup.find('meta', attrs={'name': 'description'})
                        description = meta_desc.get('content', '') if meta_desc else ''
                        
                        page_info = {
                            "url": current_url,
                            "status_code": response.status_code,
                            "title": title_text,
                            "description": description,
                            "content_summary": text_summary,
                            "full_content": full_content,
                            "content_hash": content_hash,
                            "content_length": len(content),
                            "crawled_at": datetime.utcnow().isoformat() + "Z"
                        }
                        pages.append(page_info)
                        
                        # Extract links for further crawling
                        if len(pages) < self.max_pages:
                            links = self._extract_links(soup, base_url, host)
                            for link in links:
                                if link not in visited and link not in to_visit:
                                    to_visit.append(link)
                    else:
                        logger.warning("Failed to fetch page", url=current_url, status=response.status_code)
                        
                except Exception as e:
                    logger.error("Error fetching page", url=current_url, error=str(e))
                    
                # Rate limiting - wait between requests
                await asyncio.sleep(0.5)
        
        return {
            "host": host,
            "pages_crawled": len(pages),
            "pages": pages
        }
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str, host: str) -> List[str]:
        """Extract internal links from HTML."""
        links = []
        
        for tag in soup.find_all(['a']):
            href = tag.get('href')
            if href:
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                parsed = urlparse(absolute_url)
                
                # Only include links from the same host
                if parsed.netloc == host and parsed.scheme in ['http', 'https']:
                    # Remove fragment
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    if parsed.query:
                        clean_url += f"?{parsed.query}"
                    links.append(clean_url)
        
        return links[:20]  # Limit number of links to prevent explosion
    
    def generate_manifest(self, crawl_result: Dict) -> str:
        """Generate a simple LLM.txt manifest."""
        host = crawl_result["host"]
        pages = crawl_result["pages"]
        pages_count = len(pages)
        
        # Calculate total content size
        total_size = sum(page.get('content_length', 0) for page in pages)
        
        manifest_lines = [
            "# LLM.txt Manifest",
            f"Generated for {host}",
            f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "## Metadata",
            "",
            f"**Version:** 1.0",
            f"**Site:** https://{host}",
            f"**Generated:** {datetime.utcnow().isoformat()}Z",
            f"**Last-Modified:** {datetime.utcnow().isoformat()}Z",
            "",
            "## Statistics",
            "",
            f"- **Total Pages:** {pages_count}",
            f"- **Accessible Pages:** {pages_count}",
            f"- **Total Size:** {total_size:,} bytes",
            f"- **Average Page Size:** {total_size // pages_count if pages_count > 0 else 0:,} bytes",
            "",
            "## Content Information",
            "",
            "- **Content Types:** text/html",
            "- **Languages:** en",
            "- **Crawl Frequency:** on-demand",
            "- **Crawl Depth:** 1",
            "",
            "## Pages Summary",
            "",
        ]
        
        # Add page details
        for i, page in enumerate(pages[:10], 1):
            manifest_lines.extend([
                f"### Page {i}",
                "",
                f"- **URL:** `{page['url']}`",
                f"- **Title:** {page['title']}",
                f"- **Description:** {page.get('description', 'No description')}",
                f"- **Size:** {page.get('content_length', 0):,} bytes",
                f"- **Hash:** `{page['content_hash']}`",
                f"- **Last Crawled:** {page['crawled_at']}",
                "",
                "#### Content Preview",
                "",
                "```text",
                page.get('content_summary', 'No content available'),
                "```",
                "",
            ])
        
        if pages_count > 10:
            manifest_lines.extend([
                f"> ... and {pages_count - 10} more pages",
                "",
            ])
        
        # Add manifest hash
        manifest_content = "\n".join(manifest_lines)
        manifest_hash = hashlib.sha256(manifest_content.encode()).hexdigest()
        
        manifest_lines.extend([
            "## Verification",
            "",
            f"- **Manifest Hash:** `SHA256:{manifest_hash}`",
            f"- **Manifest Size:** {len(manifest_content)} bytes",
            "",
        ])
        
        # Add full content section
        manifest_lines.extend([
            "---",
            "",
            "# Full Page Content",
            "",
        ])
        
        for i, page in enumerate(pages, 1):
            # Use full content if available, otherwise use summary
            content = page.get('full_content', page.get('content_summary', 'No content available'))
            # Ensure content doesn't break markdown formatting
            content = content.replace('```', '\\`\\`\\`')
            
            manifest_lines.extend([
                f"## Page {i}: {page['title']}",
                "",
                f"**URL:** `{page['url']}`",
                "",
                "### Content",
                "",
                "```text",
                content,
                "```",
                "",
                "---",
                "",
            ])
        
        manifest_lines.extend([
            "",
            "## End of Manifest",
            "",
            f"*This manifest was automatically generated by the URL-to-LLM system.*"
        ])
        
        return "\n".join(manifest_lines)