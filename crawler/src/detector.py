"""Change detection logic for crawled pages."""

import re
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup
import structlog

logger = structlog.get_logger()


class ChangeDetector:
    """Detects changes in web pages using various strategies."""
    
    @staticmethod
    def normalize_html(html: str) -> str:
        """Normalize HTML for consistent comparison."""
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'noscript']):
            element.decompose()
            
        # Remove comments
        for comment in soup.find_all(text=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
            comment.extract()
            
        # Remove common dynamic elements
        for elem in soup.find_all(attrs={'class': re.compile(r'(timestamp|date|time|counter|views)', re.I)}):
            elem.decompose()
            
        # Remove tracking pixels and analytics
        for elem in soup.find_all(['img', 'iframe']):
            src = elem.get('src', '')
            if any(tracker in src.lower() for tracker in ['analytics', 'pixel', 'tracking', 'beacon']):
                elem.decompose()
                
        # Get text content and normalize whitespace
        text = soup.get_text(separator=' ', strip=True)
        text = ' '.join(text.split())
        
        return text
        
    @staticmethod
    def has_changed(
        current_headers: Dict[str, str],
        current_content: str,
        previous_info: Optional[Dict[str, any]]
    ) -> Tuple[bool, str]:
        """
        Determine if content has changed.
        
        Returns:
            Tuple of (has_changed, reason)
        """
        if not previous_info:
            return True, "new_page"
            
        # Check ETag first (most reliable)
        current_etag = current_headers.get('etag', '').strip('"')
        if current_etag and previous_info.get('etag'):
            if current_etag == previous_info['etag'].strip('"'):
                logger.debug("Page unchanged by ETag", etag=current_etag)
                return False, "etag_match"
            else:
                return True, "etag_changed"
                
        # Check Last-Modified header
        current_last_modified = current_headers.get('last-modified')
        if current_last_modified and previous_info.get('last_modified'):
            if current_last_modified == previous_info['last_modified']:
                logger.debug("Page unchanged by Last-Modified", last_modified=current_last_modified)
                return False, "last_modified_match"
                
        # Finally, check content hash
        from .storage import StorageAdapter
        current_hash = StorageAdapter.compute_content_hash(
            ChangeDetector.normalize_html(current_content)
        )
        
        if current_hash == previous_info.get('content_hash'):
            logger.debug("Page unchanged by content hash", hash=current_hash[:8])
            return False, "content_hash_match"
            
        return True, "content_changed"
        
    @staticmethod
    def extract_metadata(soup: BeautifulSoup) -> Dict[str, str]:
        """Extract relevant metadata from the page."""
        metadata = {}
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text(strip=True)
            
        # Meta description
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag:
            metadata['description'] = desc_tag.get('content', '')
            
        # OpenGraph data
        og_tags = soup.find_all('meta', attrs={'property': re.compile(r'^og:')})
        for tag in og_tags:
            prop = tag.get('property', '').replace('og:', '')
            metadata[f'og_{prop}'] = tag.get('content', '')
            
        # Canonical URL
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if canonical:
            metadata['canonical'] = canonical.get('href', '')
            
        # Author
        author_tag = soup.find('meta', attrs={'name': 'author'})
        if author_tag:
            metadata['author'] = author_tag.get('content', '')
            
        return metadata