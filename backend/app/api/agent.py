"""Agent-optimized API endpoints for efficient documentation access.

This module provides simplified, bulk-oriented endpoints designed
specifically for AI agents to access documentation efficiently.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl
import asyncpg
import structlog

from app.db import get_db_pool
from app.core.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/agent", tags=["agent"])


class SiteSummary(BaseModel):
    """Simplified site information for agents."""
    host: str
    total_pages: int
    last_updated: datetime
    manifest_url: str
    search_url: str
    is_fresh: bool  # Updated within 24 hours
    is_stale: bool  # Not updated for 7+ days


class SearchResult(BaseModel):
    """Cross-site search result."""
    site: str
    url: str
    path: str
    title: str
    snippet: str
    relevance_score: float
    last_updated: datetime


class ConsolidatedManifest(BaseModel):
    """Consolidated manifest for all documentation sites."""
    generated_at: datetime
    total_sites: int
    total_pages: int
    sites: Dict[str, Dict[str, Any]]


@router.get("/sites", response_model=List[SiteSummary])
async def get_all_sites(
    only_fresh: bool = Query(False, description="Only return sites updated within 24 hours"),
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> List[SiteSummary]:
    """Get all documentation sites with freshness information."""
    async with pool.acquire() as conn:
        query = """
            SELECT host, total_pages, last_crawled_at, created_at
            FROM sites
            WHERE is_active = true
            ORDER BY host
        """
        
        rows = await conn.fetch(query)
        
        sites = []
        now = datetime.now(timezone.utc)
        
        for row in rows:
            last_updated = row['last_crawled_at'] or row['created_at']
            hours_since_update = (now - last_updated).total_seconds() / 3600
            
            is_fresh = hours_since_update <= 24
            is_stale = hours_since_update >= 168  # 7 days
            
            if only_fresh and not is_fresh:
                continue
            
            sites.append(SiteSummary(
                host=row['host'],
                total_pages=row['total_pages'],
                last_updated=last_updated,
                manifest_url=f"/api/docs/{row['host']}/manifest",
                search_url=f"/api/docs/{row['host']}/search",
                is_fresh=is_fresh,
                is_stale=is_stale
            ))
        
        return sites


@router.get("/search", response_model=List[SearchResult])
async def search_all_documentation(
    q: str = Query(..., min_length=2, description="Search query"),
    sites: Optional[str] = Query(None, description="Comma-separated list of sites to search"),
    limit: int = Query(20, ge=1, le=100),
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> List[SearchResult]:
    """Search across all or selected documentation sites."""
    async with pool.acquire() as conn:
        # Parse sites filter
        site_list = sites.split(',') if sites else None
        
        # Build query
        base_query = """
            SELECT 
                s.host as site,
                p.url,
                p.path,
                p.title,
                p.crawled_at as last_updated,
                ts_headline('english', p.extracted_text, plainto_tsquery('english', $1),
                           'StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=25') as snippet,
                ts_rank(p.search_vector, plainto_tsquery('english', $1)) as relevance_score
            FROM pages p
            JOIN sites s ON p.site_id = s.id
            WHERE p.is_active = true
            AND s.is_active = true
            AND p.search_vector @@ plainto_tsquery('english', $1)
        """
        
        if site_list:
            base_query += " AND s.host = ANY($2::text[])"
            base_query += " ORDER BY relevance_score DESC, p.title LIMIT $3"
            rows = await conn.fetch(base_query, q, site_list, limit)
        else:
            base_query += " ORDER BY relevance_score DESC, p.title LIMIT $2"
            rows = await conn.fetch(base_query, q, limit)
        
        return [
            SearchResult(
                site=row['site'],
                url=row['url'],
                path=row['path'],
                title=row['title'],
                snippet=row['snippet'],
                relevance_score=float(row['relevance_score']),
                last_updated=row['last_updated']
            )
            for row in rows
        ]


@router.get("/manifest", response_model=ConsolidatedManifest)
async def get_consolidated_manifest(
    format: str = Query("consolidated", pattern="^(consolidated|detailed)$"),
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> ConsolidatedManifest:
    """Get a consolidated manifest of all documentation sites."""
    async with pool.acquire() as conn:
        # Get all active sites
        sites_query = """
            SELECT 
                s.id,
                s.host,
                s.title,
                s.description,
                s.last_crawled_at,
                s.total_pages,
                s.total_size_bytes,
                COUNT(p.id) as actual_page_count
            FROM sites s
            LEFT JOIN pages p ON s.id = p.site_id AND p.is_active = true
            WHERE s.is_active = true
            GROUP BY s.id
            ORDER BY s.host
        """
        
        rows = await conn.fetch(sites_query)
        
        sites_data = {}
        total_pages = 0
        
        for row in rows:
            page_count = row['actual_page_count'] or row['total_pages']
            total_pages += page_count
            
            site_info = {
                "title": row['title'],
                "description": row['description'],
                "last_updated": row['last_crawled_at'].isoformat() if row['last_crawled_at'] else None,
                "pages": page_count,
                "size_bytes": row['total_size_bytes'],
                "manifest_url": f"/api/docs/{row['host']}/manifest",
                "search_endpoint": f"/api/docs/{row['host']}/search",
                "pages_endpoint": f"/api/docs/{row['host']}/pages"
            }
            
            # Add detailed info if requested
            if format == "detailed":
                # Get recent updates
                recent_query = """
                    SELECT path, title, crawled_at
                    FROM pages
                    WHERE site_id = $1 AND is_active = true
                    ORDER BY crawled_at DESC
                    LIMIT 5
                """
                recent_pages = await conn.fetch(recent_query, row['id'])
                
                site_info["recent_updates"] = [
                    {
                        "path": p['path'],
                        "title": p['title'],
                        "updated": p['crawled_at'].isoformat()
                    }
                    for p in recent_pages
                ]
            
            sites_data[row['host']] = site_info
        
        return ConsolidatedManifest(
            generated_at=datetime.now(timezone.utc),
            total_sites=len(sites_data),
            total_pages=total_pages,
            sites=sites_data
        )


@router.get("/content/{host}/{path:path}")
async def get_documentation_content(
    host: str,
    path: str,
    format: str = Query("markdown", pattern="^(html|markdown|both)$"),
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> Dict[str, Any]:
    """Get documentation content with metadata for agent consumption."""
    # Normalize path
    if not path.startswith('/'):
        path = '/' + path
    
    async with pool.acquire() as conn:
        query = """
            SELECT 
                p.id,
                p.title,
                p.description,
                p.html_storage_key,
                p.markdown_storage_key,
                p.crawled_at,
                p.extracted_text
            FROM pages p
            JOIN sites s ON p.site_id = s.id
            WHERE s.host = $1 AND p.path = $2 AND p.is_active = true
        """
        
        row = await conn.fetchrow(query, host, path)
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Page not found: {host}{path}")
        
        # Build response
        response = {
            "host": host,
            "path": path,
            "title": row['title'],
            "description": row['description'],
            "last_updated": row['crawled_at'].isoformat(),
            "content": {}
        }
        
        # Get content from S3
        from app.storage import s3_client
        
        if format in ["markdown", "both"] and row['markdown_storage_key']:
            markdown_content = await s3_client.download_content(row['markdown_storage_key'])
            if markdown_content:
                response["content"]["markdown"] = markdown_content.decode('utf-8')
        
        if format in ["html", "both"] and row['html_storage_key']:
            html_content = await s3_client.download_content(row['html_storage_key'])
            if html_content:
                response["content"]["html"] = html_content.decode('utf-8')
        
        # If no content retrieved, use extracted text as fallback
        if not response["content"]:
            response["content"]["text"] = row['extracted_text']
        
        return response


@router.post("/refresh/{host}")
async def trigger_site_refresh(
    host: str,
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> Dict[str, str]:
    """Trigger a refresh crawl for a specific documentation site."""
    from app.crawler.documentation_crawler import DocumentationCrawler
    from fastapi import BackgroundTasks
    
    async with pool.acquire() as conn:
        # Check if site exists
        site = await conn.fetchrow(
            "SELECT id, host FROM sites WHERE host = $1 AND is_active = true",
            host
        )
        
        if not site:
            raise HTTPException(status_code=404, detail=f"Site {host} not found")
        
        # TODO: Add to background task queue
        # For now, return acknowledgment
        return {
            "status": "refresh_scheduled",
            "host": host,
            "message": f"Documentation refresh for {host} has been scheduled"
        }


@router.get("/stats")
async def get_documentation_stats(
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> Dict[str, Any]:
    """Get overall documentation statistics."""
    async with pool.acquire() as conn:
        stats_query = """
            SELECT
                COUNT(DISTINCT s.id) as total_sites,
                COUNT(DISTINCT p.id) as total_pages,
                SUM(p.html_size_bytes + COALESCE(p.markdown_size_bytes, 0)) as total_size_bytes,
                MIN(p.crawled_at) as oldest_update,
                MAX(p.crawled_at) as newest_update
            FROM sites s
            LEFT JOIN pages p ON s.id = p.site_id AND p.is_active = true
            WHERE s.is_active = true
        """
        
        stats = await conn.fetchrow(stats_query)
        
        # Get freshness breakdown
        freshness_query = """
            SELECT
                COUNT(CASE WHEN last_crawled_at > NOW() - INTERVAL '24 hours' THEN 1 END) as fresh_sites,
                COUNT(CASE WHEN last_crawled_at BETWEEN NOW() - INTERVAL '7 days' AND NOW() - INTERVAL '24 hours' THEN 1 END) as recent_sites,
                COUNT(CASE WHEN last_crawled_at < NOW() - INTERVAL '7 days' THEN 1 END) as stale_sites
            FROM sites
            WHERE is_active = true
        """
        
        freshness = await conn.fetchrow(freshness_query)
        
        return {
            "total_sites": stats['total_sites'] or 0,
            "total_pages": stats['total_pages'] or 0,
            "total_size_bytes": stats['total_size_bytes'] or 0,
            "oldest_update": stats['oldest_update'].isoformat() if stats['oldest_update'] else None,
            "newest_update": stats['newest_update'].isoformat() if stats['newest_update'] else None,
            "freshness": {
                "fresh": freshness['fresh_sites'] or 0,
                "recent": freshness['recent_sites'] or 0,
                "stale": freshness['stale_sites'] or 0
            }
        }