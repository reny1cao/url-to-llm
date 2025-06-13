"""LLM manifest generator."""

import hashlib
from datetime import datetime
from typing import Dict, List


class ManifestGenerator:
    """Generate LLM.txt manifests from crawl results."""
    
    @staticmethod
    def generate(crawl_result: Dict) -> str:
        """Generate an LLM.txt manifest from crawl results."""
        host = crawl_result["host"]
        pages = crawl_result.get("pages", [])
        pages_count = len(pages)
        total_size = sum(page.get('content_length', 0) for page in pages)
        
        # Build manifest sections
        lines = [
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
            f"- **Crawl Depth:** {crawl_result.get('max_depth', 'unlimited')}",
            "",
            "## Site Structure",
            "",
        ]
        
        # Add site structure
        if pages:
            # Group pages by path depth
            root_pages = []
            path_pages = {}
            
            for page in pages:
                url = page['url']
                path = url.replace(f"https://{host}", "").replace(f"http://{host}", "")
                if not path or path == "/":
                    root_pages.append(page)
                else:
                    depth = path.count('/')
                    if depth not in path_pages:
                        path_pages[depth] = []
                    path_pages[depth].append(page)
            
            # Add root pages
            if root_pages:
                lines.append("### Root Level")
                lines.append("")
                for page in root_pages[:5]:
                    lines.append(f"- **{page['title'] or 'Homepage'}** - `/`")
                lines.append("")
            
            # Add pages by depth
            for depth in sorted(path_pages.keys())[:3]:
                lines.append(f"### Level {depth}")
                lines.append("")
                for page in path_pages[depth][:10]:
                    path = page['url'].replace(f"https://{host}", "").replace(f"http://{host}", "")
                    lines.append(f"- **{page['title'] or 'Untitled'}** - `{path}`")
                lines.append("")
        
        # Add page summaries
        lines.extend([
            "## Page Summaries",
            "",
        ])
        
        for i, page in enumerate(pages[:20], 1):
            lines.extend([
                f"### {i}. {page.get('title', 'Untitled Page')}",
                "",
                f"- **URL:** `{page['url']}`",
                f"- **Description:** {page.get('description', 'No description available')}",
                f"- **Size:** {page.get('content_length', 0):,} bytes",
                f"- **Content Hash:** `{page.get('content_hash', 'N/A')}`",
                f"- **Last Crawled:** {page.get('crawled_at', 'Unknown')}",
                "",
            ])
            
            # Add content preview
            if page.get('content'):
                content = page['content']
                
                # Create a better preview with first few paragraphs
                paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
                
                # Use first 2-3 meaningful paragraphs or first 1000 characters
                preview_paragraphs = []
                char_count = 0
                
                for paragraph in paragraphs[:5]:  # Max 5 paragraphs
                    if char_count + len(paragraph) > 1000:
                        break
                    preview_paragraphs.append(paragraph)
                    char_count += len(paragraph)
                
                if preview_paragraphs:
                    content_preview = '\n\n'.join(preview_paragraphs)
                    if len(content) > char_count:
                        content_preview += "\n\n[Content continues...]"
                else:
                    # Fallback to first 800 characters
                    content_preview = content[:800]
                    if len(content) > 800:
                        content_preview += "..."
                
                # Escape triple backticks in content to prevent markdown issues
                content_preview = content_preview.replace('```', '` ` `')
                
                lines.extend([
                    "**Content Preview:**",
                    "",
                    "```",
                    content_preview,
                    "```",
                    "",
                ])
        
        if pages_count > 20:
            lines.extend([
                f"> ... and {pages_count - 20} more pages",
                "",
            ])
        
        # Add usage guidelines
        lines.extend([
            "## Usage Guidelines",
            "",
            "This manifest provides a structured overview of the website's content for LLM consumption.",
            "It includes metadata, statistics, and content summaries to help LLMs understand the site structure.",
            "",
            "### Rate Limiting",
            "- Please respect rate limits when accessing this site",
            "- Recommended delay between requests: 1 second",
            "",
            "### Content License",
            "- Content is provided under the website's terms of service",
            "- Please check the website's robots.txt and terms for usage restrictions",
            "",
        ])
        
        # Add manifest verification
        manifest_content = "\n".join(lines)
        manifest_hash = hashlib.sha256(manifest_content.encode()).hexdigest()
        
        lines.extend([
            "## Verification",
            "",
            f"- **Manifest Hash:** `SHA256:{manifest_hash}`",
            f"- **Manifest Size:** {len(manifest_content)} bytes",
            "",
            "---",
            "",
            "*This manifest was generated by the URL-to-LLM system.*"
        ])
        
        return "\n".join(lines)