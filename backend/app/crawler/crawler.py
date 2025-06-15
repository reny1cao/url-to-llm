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
                favor_precision=False,  # Balance between precision and recall
                config=trafilatura.settings.use_config()  # Use default config with code block support
            )
            
            if trafilatura_content:
                # Clean up the content more carefully
                # Remove excessive empty lines but preserve formatting
                lines = trafilatura_content.split('\n')
                cleaned_lines = []
                empty_line_count = 0
                
                for line in lines:
                    # Don't strip the line - preserve indentation
                    if line.strip():  # Line has content
                        # Add back a single empty line if we had multiple
                        if empty_line_count > 0:
                            cleaned_lines.append('')
                        cleaned_lines.append(line)
                        empty_line_count = 0
                    else:  # Empty line
                        empty_line_count += 1
                
                # Join back with single newlines
                trafilatura_content = '\n'.join(cleaned_lines)
                
                # Post-process to fix common formatting issues
                import re
                
                # Fix Trafilatura's broken sentence formatting
                # These are based on actual issues found in comprehensive testing
                
                # 1. Fix ALL punctuation after inline code (most common issue)
                # Handles: `code`\n\n. or `code`\n\n, etc.
                trafilatura_content = re.sub(r'`\n\n([,\.;:!?\)])', r'`\1', trafilatura_content)
                
                # 2. Fix orphaned punctuation at start of lines
                # Handles: \n\n. Text or \n\n, text
                trafilatura_content = re.sub(r'\n\n([,\.;:!?])\s*', r'\1 ', trafilatura_content)
                
                # 3. Fix inline code breaking word flow
                # Handles: `int`\n\nand `float` -> `int` and `float`
                trafilatura_content = re.sub(r'`\n\n(and|or|but|with|to|from|in|on|at|for|of|as|by)\s+`', r'` \1 `', trafilatura_content)
                
                # 4. Fix broken sentences after closing parentheses or brackets
                trafilatura_content = re.sub(r'([)\]])\n\n([a-z])', r'\1 \2', trafilatura_content)
                
                # 5. Fix specific patterns that are clearly errors
                # When a line ends with common continuing words
                continuing_words = r'(the|a|an|and|or|but|with|in|on|at|to|for|of|as|by|from|that|which|who|when|where|if|then|than|is|are|was|were|have|has|had)'
                trafilatura_content = re.sub(rf'\b{continuing_words}\n\n([a-z])', r'\1 \2', trafilatura_content, flags=re.IGNORECASE)
                
                # 6. Fix code comments breaking flow
                # Handles: /* comment */\n\n.classname
                trafilatura_content = re.sub(r'(\*/)`?\n\n([\.#\w])', r'\1 \2', trafilatura_content)
                # Also fix when it's inside backticks
                trafilatura_content = re.sub(r'(\*/`)\n\n([\.#\w])', r'\1 \2', trafilatura_content)
                
                # 7. Ensure proper spacing after headings (safe - only adds spacing)
                trafilatura_content = re.sub(r'^(#{1,6}\s+[^\n]+)([A-Z][a-z])', r'\1\n\n\2', trafilatura_content, flags=re.MULTILINE)
                
                # 8. Fix numbered lists where number is separated from content
                # Handles: 1.\n\nContent -> 1. Content
                trafilatura_content = re.sub(r'^(\d+\.)\n\n([A-Z])', r'\1 \2', trafilatura_content, flags=re.MULTILINE)
                
                # 9. Fix cases where short words/numbers are orphaned
                # Handles: is\n2. or is\na 
                trafilatura_content = re.sub(r'\b(is|are|was|were|be|been|has|have|had|do|does|did)\n\n?([a-z0-9])', r'\1 \2', trafilatura_content, flags=re.IGNORECASE)
                
                # Fix code blocks that got merged with text
                # Look for patterns like "import { ... } from 'package'export" and add newlines
                trafilatura_content = re.sub(r"(import\s*{[^}]+}\s*from\s*['\"][^'\"]+['\"])([a-zA-Z])", r'\1\n\n\2', trafilatura_content)
                # Also handle other common code patterns
                trafilatura_content = re.sub(r"(}\s*\)\s*)(import|export|const|let|var|function)", r'\1\n\n\2', trafilatura_content)
                # Fix inline code that should be code blocks
                trafilatura_content = re.sub(r'`(yarn add [^`]+)`', r'```bash\n\1\n```', trafilatura_content)
                trafilatura_content = re.sub(r'`(npm install [^`]+)`', r'```bash\n\1\n```', trafilatura_content)
                
                # Limit size if needed
                max_size = 20000
                if len(trafilatura_content) > max_size:
                    trafilatura_content = trafilatura_content[:max_size] + "\n\n[Content truncated...]"
                
                # Check if there's likely code that should be in code blocks
                # Look for common code patterns not wrapped in ```
                code_patterns = [
                    r'import\s*{[^}]+}\s*from',
                    r'export\s+(default|const|function|class)',
                    r'const\s+\w+\s*=',
                    r'function\s+\w+\s*\(',
                ]
                
                likely_has_unwrapped_code = False
                for pattern in code_patterns:
                    if re.search(pattern, trafilatura_content):
                        # Check if this code is outside of code blocks
                        for match in re.finditer(pattern, trafilatura_content):
                            # Get text before match to count ``` 
                            text_before = trafilatura_content[:match.start()]
                            # If odd number of ``` before, we're inside a code block
                            if text_before.count('```') % 2 == 0:
                                likely_has_unwrapped_code = True
                                break
                
                if likely_has_unwrapped_code:
                    logger.info("Detected likely unwrapped code, wrapping in code blocks")
                    
                    # Try to wrap obvious code blocks
                    # First check if import is already in a code block
                    imports_to_wrap = []
                    for match in re.finditer(r'import\s*{[^}]+}\s*from\s*[\'"][^\'\"]+[\'"]', trafilatura_content):
                        # Check if this import is already in a code block
                        text_before = trafilatura_content[:match.start()]
                        if text_before.count('```') % 2 == 0:  # Even number means we're outside code blocks
                            imports_to_wrap.append(match)
                    
                    # Work backwards to avoid messing up indices
                    for match in reversed(imports_to_wrap):
                        import_text = match.group(0)
                        start = match.start()
                        end = match.end()
                        
                        # Look for export statement right after
                        remaining = trafilatura_content[end:]
                        export_match = re.match(r'\s*(export\s+default[^;{\n]+)', remaining)
                        
                        if export_match:
                            # Wrap import + export together
                            full_code = import_text + '\n' + export_match.group(1).strip()
                            trafilatura_content = (
                                trafilatura_content[:start] + 
                                '```javascript\n' + full_code + '\n```' +
                                trafilatura_content[end + export_match.end():]
                            )
                        else:
                            # Just wrap the import
                            trafilatura_content = (
                                trafilatura_content[:start] + 
                                '```javascript\n' + import_text + '\n```' +
                                trafilatura_content[end:]
                            )
                
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
        # Track processed elements to avoid duplicates
        processed = set()
        
        for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'blockquote', 'pre', 'code', 'div']):
            # Skip if already processed
            if element in processed:
                continue
                
            # Skip if this element is inside a pre tag (already processed)
            if element.name == 'code' and element.find_parent('pre'):
                continue
                
            text = element.get_text(strip=True)
            
            # For code/pre elements, get raw text
            if element.name in ['pre', 'code']:
                text = element.get_text(strip=False)  # Preserve formatting
            
            if not text or (element.name not in ['pre', 'code'] and len(text) < 10):  # Skip very short snippets except code
                continue
            
            # Clean up whitespace for non-code elements
            if element.name not in ['pre', 'code']:
                text = ' '.join(text.split())
            
            # Format based on element type
            if element.name.startswith('h'):
                # Add spacing around headings
                level = int(element.name[1])
                heading_prefix = '#' * level
                if content_parts:
                    content_parts.append("")  # Empty line before heading
                content_parts.append(f"{heading_prefix} {text}")
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
                # Preserve code blocks with language detection
                code_elem = element.find('code')
                lang = ''
                if code_elem and 'class' in code_elem.attrs:
                    classes = code_elem.get('class', [])
                    for cls in classes:
                        if cls.startswith('language-'):
                            lang = cls.replace('language-', '')
                            break
                
                content_parts.append(f"```{lang}")
                content_parts.append(text.strip())
                content_parts.append("```")
                content_parts.append("")
                # Mark all children as processed
                for child in element.find_all():
                    processed.add(child)
            elif element.name == 'code':
                # Inline code
                content_parts.append(f"`{text}`")
            elif element.name == 'div':
                # Only include divs with substantial content
                if len(text) > 50:
                    content_parts.append(text)
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