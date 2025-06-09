"""LLM.txt manifest generator."""

import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

import structlog
from pydantic import BaseModel

from .storage import StorageAdapter

logger = structlog.get_logger()


class ManifestField(BaseModel):
    """Represents a field in the llm.txt manifest."""
    
    key: str
    value: str
    description: Optional[str] = None


class LLMManifest:
    """Generates and manages llm.txt manifests."""
    
    VERSION = "1.0"
    
    def __init__(self, storage: StorageAdapter):
        self.storage = storage
        
    async def generate_manifest(self, host: str) -> str:
        """Generate llm.txt manifest for a host."""
        logger.info("Generating manifest", host=host)
        
        # Get all pages for the host
        pages = await self.storage.get_host_pages(host)
        
        # Build manifest fields
        fields: List[ManifestField] = []
        
        # Version
        fields.append(ManifestField(
            key="Version",
            value=self.VERSION,
            description="LLM.txt specification version"
        ))
        
        # Site info
        fields.append(ManifestField(
            key="Site",
            value=f"https://{host}",
            description="Base URL of the website"
        ))
        
        # Generated timestamp
        fields.append(ManifestField(
            key="Generated",
            value=datetime.utcnow().isoformat() + "Z",
            description="Manifest generation timestamp"
        ))
        
        # Page count
        total_pages = len(pages)
        accessible_pages = len([p for p in pages if not p['is_blocked']])
        fields.append(ManifestField(
            key="Pages",
            value=str(total_pages),
            description="Total number of pages crawled"
        ))
        
        fields.append(ManifestField(
            key="Accessible-Pages",
            value=str(accessible_pages),
            description="Number of accessible pages"
        ))
        
        # Site policy (inferred from robots.txt)
        robots_content = await self.storage.get_from_s3(f"meta/{host}/robots.txt")
        if robots_content:
            fields.append(ManifestField(
                key="Site-Policy",
                value="robots.txt",
                description="Site crawling policy"
            ))
            
        # License detection (basic implementation)
        license_info = await self._detect_license(host, pages)
        if license_info:
            fields.append(ManifestField(
                key="License",
                value=license_info,
                description="Detected content license"
            ))
            
        # Content types
        content_types = self._get_content_types(pages)
        if content_types:
            fields.append(ManifestField(
                key="Content-Types",
                value=", ".join(content_types),
                description="Available content types"
            ))
            
        # Last crawled
        if pages:
            last_crawled = max(p['crawled_at'] for p in pages)
            fields.append(ManifestField(
                key="Last-Crawled",
                value=last_crawled.isoformat() + "Z",
                description="Most recent crawl timestamp"
            ))
            
        # Crawl frequency (placeholder)
        fields.append(ManifestField(
            key="Crawl-Frequency",
            value="daily",
            description="How often the site is crawled"
        ))
        
        # Page list
        fields.append(ManifestField(
            key="Pages-List",
            value=f"https://cdn.example.com/llm/{host}/pages.json",
            description="URL to detailed page listing"
        ))
        
        # API endpoint
        fields.append(ManifestField(
            key="API-Endpoint",
            value=f"https://api.example.com/tools/llm.fetch_page?host={host}",
            description="MCP API endpoint for page fetching"
        ))
        
        # Generate manifest content
        manifest_lines = []
        
        # Header
        manifest_lines.append("# LLM.txt Manifest")
        manifest_lines.append(f"# Generated for {host}")
        manifest_lines.append("")
        
        # Fields
        for field in fields:
            if field.description:
                manifest_lines.append(f"# {field.description}")
            manifest_lines.append(f"{field.key}: {field.value}")
            manifest_lines.append("")
            
        # Generate content hash
        content = "\n".join(manifest_lines)
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # Add hash field
        manifest_lines.insert(-1, f"Hash: {content_hash}")
        manifest_lines.insert(-1, "")
        
        # Final manifest
        manifest = "\n".join(manifest_lines)
        
        # Save to S3
        await self.storage.save_to_s3(
            f"llm/{host}/llm.txt",
            manifest.encode('utf-8'),
            content_type="text/plain"
        )
        
        # Also save pages.json
        await self._save_pages_json(host, pages)
        
        logger.info("Manifest generated", host=host, hash=content_hash[:8])
        return manifest
        
    async def _detect_license(self, host: str, pages: List[Dict]) -> Optional[str]:
        """Detect content license from pages."""
        # Check common license URLs
        license_urls = [
            '/license', '/license.html', '/license.txt',
            '/terms', '/terms.html', '/legal',
            '/copyright', '/copyright.html'
        ]
        
        for page in pages:
            parsed = urlparse(page['url'])
            if parsed.path.lower() in license_urls:
                # Found a license page
                content = await self.storage.get_from_s3(
                    f"pages/{host}{parsed.path}"
                )
                if content:
                    # Basic license detection
                    content_lower = content.decode('utf-8', errors='ignore').lower()
                    if 'creative commons' in content_lower:
                        if 'cc0' in content_lower:
                            return "CC0-1.0"
                        elif 'by-sa' in content_lower:
                            return "CC-BY-SA-4.0"
                        elif 'by-nc' in content_lower:
                            return "CC-BY-NC-4.0"
                        elif 'by' in content_lower:
                            return "CC-BY-4.0"
                    elif 'mit license' in content_lower:
                        return "MIT"
                    elif 'apache license' in content_lower:
                        return "Apache-2.0"
                    elif 'gnu general public' in content_lower:
                        return "GPL-3.0"
                        
        return None
        
    def _get_content_types(self, pages: List[Dict]) -> List[str]:
        """Get unique content types from pages."""
        types = set()
        for page in pages:
            if 'content_type' in page and page['content_type']:
                types.add(page['content_type'])
        return sorted(list(types))
        
    async def _save_pages_json(self, host: str, pages: List[Dict]):
        """Save detailed pages listing as JSON."""
        import json
        
        pages_data = []
        for page in pages:
            pages_data.append({
                "url": page['url'],
                "status": "accessible" if not page['is_blocked'] else "blocked",
                "last_crawled": page['crawled_at'].isoformat() + "Z",
                "content_hash": page['content_hash'][:16],  # First 16 chars
            })
            
        json_content = json.dumps({
            "host": host,
            "generated": datetime.utcnow().isoformat() + "Z",
            "pages": pages_data
        }, indent=2)
        
        await self.storage.save_to_s3(
            f"llm/{host}/pages.json",
            json_content.encode('utf-8'),
            content_type="application/json"
        )