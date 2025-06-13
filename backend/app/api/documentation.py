"""API endpoints for documentation hosting.

This module provides REST API endpoints for serving hosted documentation,
including pages, navigation, assets, and search functionality.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, BackgroundTasks
from fastapi.responses import RedirectResponse

import asyncpg
import structlog
import json

from app.core.config import settings
from app.db.session import get_db_pool
from app.storage import s3_client
from app.models.documentation_dto import (
    SiteResponse, PageResponse, NavigationResponse, 
    PageListResponse, SearchResponse, SiteCreateRequest,
    CrawlRequest
)

logger = structlog.get_logger()

router = APIRouter(prefix="/docs", tags=["documentation"])


@router.post("/crawl", response_model=Dict[str, Any])
async def start_documentation_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Start crawling a documentation site for hosting."""
    from app.crawler.documentation_crawler import DocumentationCrawler
    
    # Create crawler instance
    crawler = DocumentationCrawler(
        max_pages=request.max_pages,
        follow_links=request.follow_links,
        download_assets=request.download_assets,
        rate_limit=request.rate_limit
    )
    
    # Start crawl in background
    crawl_id = str(uuid4())
    
    async def run_crawl():
        try:
            logger.info("Starting documentation crawl", url=str(request.url))
            result = await crawler.crawl_documentation(
                str(request.url),
                incremental=request.incremental
            )
            logger.info("Documentation crawl completed", result=result)
        except Exception as e:
            logger.error("Documentation crawl failed", error=str(e))
    
    background_tasks.add_task(run_crawl)
    
    return {
        "crawl_id": crawl_id,
        "status": "started",
        "url": str(request.url)
    }


@router.get("/", response_model=List[SiteResponse])
async def list_sites(
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> List[SiteResponse]:
    """List all documentation sites."""
    async with pool.acquire() as conn:
        query = """
            SELECT id, host, title, description, favicon_url, language,
                   is_active, created_at, updated_at, last_crawled_at,
                   total_pages, total_size_bytes
            FROM sites
            WHERE ($1::boolean IS NULL OR is_active = $1)
            ORDER BY host
        """
        
        rows = await conn.fetch(query, is_active)
        
        return [
            SiteResponse(
                id=row['id'],
                host=row['host'],
                title=row['title'],
                description=row['description'],
                favicon_url=row['favicon_url'],
                language=row['language'],
                is_active=row['is_active'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                last_crawled_at=row['last_crawled_at'],
                total_pages=row['total_pages'],
                total_size_bytes=row['total_size_bytes'],
                metadata=None  # Skip metadata in list view for performance
            )
            for row in rows
        ]


@router.get("/{host}", response_model=SiteResponse)
async def get_site(
    host: str,
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> SiteResponse:
    """Get a documentation site by host."""
    async with pool.acquire() as conn:
        query = """
            SELECT id, host, title, description, favicon_url, language,
                   is_active, created_at, updated_at, last_crawled_at,
                   total_pages, total_size_bytes, metadata
            FROM sites
            WHERE host = $1
        """
        
        row = await conn.fetchrow(query, host)
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Site {host} not found")
        
        return SiteResponse(
            id=row['id'],
            host=row['host'],
            title=row['title'],
            description=row['description'],
            favicon_url=row['favicon_url'],
            language=row['language'],
            is_active=row['is_active'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            last_crawled_at=row['last_crawled_at'],
            total_pages=row['total_pages'],
            total_size_bytes=row['total_size_bytes'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )


@router.get("/{host}/pages", response_model=PageListResponse)
async def list_pages(
    host: str,
    path_prefix: Optional[str] = Query(None, description="Filter by path prefix"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> PageListResponse:
    """List pages for a documentation site."""
    async with pool.acquire() as conn:
        # Get site
        site = await conn.fetchrow(
            "SELECT id FROM sites WHERE host = $1", host
        )
        if not site:
            raise HTTPException(status_code=404, detail=f"Site {host} not found")
        
        # Count total pages
        count_query = """
            SELECT COUNT(*) as total
            FROM pages
            WHERE site_id = $1 AND is_active = true
            AND ($2::text IS NULL OR path LIKE $2 || '%')
        """
        total = await conn.fetchval(count_query, site['id'], path_prefix)
        
        # Get pages
        query = """
            SELECT id, url, path, title, description, 
                   html_size_bytes, markdown_size_bytes,
                   crawled_at, updated_at
            FROM pages
            WHERE site_id = $1 AND is_active = true
            AND ($2::text IS NULL OR path LIKE $2 || '%')
            ORDER BY path
            LIMIT $3 OFFSET $4
        """
        
        rows = await conn.fetch(query, site['id'], path_prefix, limit, offset)
        
        pages = [
            PageResponse(
                id=row['id'],
                url=row['url'],
                path=row['path'],
                title=row['title'],
                description=row['description'],
                html_size_bytes=row['html_size_bytes'],
                markdown_size_bytes=row['markdown_size_bytes'],
                crawled_at=row['crawled_at'],
                updated_at=row['updated_at']
            )
            for row in rows
        ]
        
        return PageListResponse(
            pages=pages,
            total=total,
            limit=limit,
            offset=offset
        )


@router.get("/{host}/page/{path:path}")
async def get_page_content(
    host: str,
    path: str,
    format: str = Query("html", pattern="^(html|markdown|json)$"),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get the content of a specific documentation page."""
    # Normalize path
    if not path.startswith('/'):
        path = '/' + path
    
    async with pool.acquire() as conn:
        # Get page with site info
        query = """
            SELECT p.id, p.url, p.path, p.title, p.description,
                   p.html_storage_key, p.markdown_storage_key,
                   p.html_size_bytes, p.markdown_size_bytes,
                   p.metadata, p.crawled_at, p.updated_at,
                   s.host
            FROM pages p
            JOIN sites s ON p.site_id = s.id
            WHERE s.host = $1 AND p.path = $2 AND p.is_active = true
        """
        
        row = await conn.fetchrow(query, host, path)
        
        if not row:
            raise HTTPException(
                status_code=404, 
                detail=f"Page not found: {host}{path}"
            )
        
        # Return metadata if JSON format requested
        if format == "json":
            return PageResponse(
                id=row['id'],
                url=row['url'],
                path=row['path'],
                title=row['title'],
                description=row['description'],
                html_size_bytes=row['html_size_bytes'],
                markdown_size_bytes=row['markdown_size_bytes'],
                metadata=json.loads(row['metadata']) if row['metadata'] else None,
                crawled_at=row['crawled_at'],
                updated_at=row['updated_at']
            )
        
        # Get content from S3
        storage_key = (
            row['html_storage_key'] if format == "html" 
            else row['markdown_storage_key']
        )
        
        if not storage_key:
            raise HTTPException(
                status_code=404,
                detail=f"Content not available in {format} format"
            )
        
        content = await s3_client.download_content(storage_key)
        
        if not content:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve content from storage"
            )
        
        # Return appropriate response
        content_type = (
            "text/html; charset=utf-8" if format == "html"
            else "text/markdown; charset=utf-8"
        )
        
        # Encode title for HTTP header (latin-1 safe)
        safe_title = (row['title'] or "").encode('ascii', 'ignore').decode('ascii')
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "X-Page-Title": safe_title,
                "X-Page-Updated": row['updated_at'].isoformat()
            }
        )


@router.get("/{host}/navigation", response_model=List[NavigationResponse])
async def get_navigation(
    host: str,
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> List[NavigationResponse]:
    """Get the navigation structure for a documentation site."""
    async with pool.acquire() as conn:
        # Get site
        site = await conn.fetchrow(
            "SELECT id FROM sites WHERE host = $1", host
        )
        if not site:
            raise HTTPException(status_code=404, detail=f"Site {host} not found")
        
        # Get navigation tree
        query = """
            WITH RECURSIVE nav_tree AS (
                -- Root level items
                SELECT n.id, n.page_id, n.parent_id, n.title, n.path,
                       n.order_index, n.level, n.is_expanded, n.metadata,
                       p.url, p.description
                FROM site_navigation n
                JOIN pages p ON n.page_id = p.id
                WHERE n.site_id = $1 AND n.parent_id IS NULL
                
                UNION ALL
                
                -- Recursive children
                SELECT n.id, n.page_id, n.parent_id, n.title, n.path,
                       n.order_index, n.level, n.is_expanded, n.metadata,
                       p.url, p.description
                FROM site_navigation n
                JOIN pages p ON n.page_id = p.id
                JOIN nav_tree nt ON n.parent_id = nt.id
            )
            SELECT * FROM nav_tree
            ORDER BY level, order_index, path
        """
        
        rows = await conn.fetch(query, site['id'])
        
        # Build navigation tree
        nav_map = {}
        root_items = []
        
        for row in rows:
            nav_item = NavigationResponse(
                id=row['id'],
                page_id=row['page_id'],
                parent_id=row['parent_id'],
                title=row['title'],
                path=row['path'],
                url=row['url'],
                description=row['description'],
                order_index=row['order_index'],
                level=row['level'],
                is_expanded=row['is_expanded'],
                metadata=json.loads(row['metadata']) if row['metadata'] else None,
                children=[]
            )
            
            nav_map[nav_item.id] = nav_item
            
            if nav_item.parent_id:
                parent = nav_map.get(nav_item.parent_id)
                if parent:
                    parent.children.append(nav_item)
            else:
                root_items.append(nav_item)
        
        return root_items


@router.get("/{host}/search", response_model=SearchResponse)
async def search_documentation(
    host: str,
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> SearchResponse:
    """Search documentation content."""
    async with pool.acquire() as conn:
        # Get site
        site = await conn.fetchrow(
            "SELECT id FROM sites WHERE host = $1", host
        )
        if not site:
            raise HTTPException(status_code=404, detail=f"Site {host} not found")
        
        # Prepare search query for PostgreSQL full-text search
        # Convert user query to tsquery format
        search_query = ' & '.join(q.split())
        
        # Count total results
        count_query = """
            SELECT COUNT(*) as total
            FROM pages
            WHERE site_id = $1 
            AND is_active = true
            AND search_vector @@ plainto_tsquery('english', $2)
        """
        total = await conn.fetchval(count_query, site['id'], search_query)
        
        # Search pages
        query = """
            SELECT id, url, path, title, description,
                   ts_headline('english', extracted_text, plainto_tsquery('english', $2),
                              'StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=25') as snippet,
                   ts_rank(search_vector, plainto_tsquery('english', $2)) as rank
            FROM pages
            WHERE site_id = $1 
            AND is_active = true
            AND search_vector @@ plainto_tsquery('english', $2)
            ORDER BY rank DESC, title
            LIMIT $3 OFFSET $4
        """
        
        rows = await conn.fetch(query, site['id'], search_query, limit, offset)
        
        results = []
        for row in rows:
            results.append({
                'id': row['id'],
                'url': row['url'],
                'path': row['path'],
                'title': row['title'],
                'description': row['description'],
                'snippet': row['snippet'],
                'score': float(row['rank'])
            })
        
        return SearchResponse(
            query=q,
            results=results,
            total=total,
            limit=limit,
            offset=offset
        )


@router.get("/{host}/assets/{path:path}")
async def get_asset(
    host: str,
    path: str,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get a documentation asset (image, file, etc)."""
    # Normalize path
    if not path.startswith('/'):
        path = '/' + path
    
    async with pool.acquire() as conn:
        # Get asset info
        query = """
            SELECT a.storage_key, a.content_type, a.size_bytes
            FROM assets a
            JOIN sites s ON a.site_id = s.id
            WHERE s.host = $1 AND a.path = $2
        """
        
        row = await conn.fetchrow(query, host, path)
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Asset not found: {host}{path}"
            )
        
        # For production, redirect to CDN
        if settings.cdn_url and not settings.debug:
            cdn_url = f"{settings.cdn_url}/{row['storage_key']}"
            return RedirectResponse(url=cdn_url, status_code=302)
        
        # For development, serve from S3
        content = await s3_client.download_content(row['storage_key'])
        
        if not content:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve asset from storage"
            )
        
        return Response(
            content=content,
            media_type=row['content_type'],
            headers={
                "Cache-Control": "public, max-age=86400",  # 24 hours
                "Content-Length": str(row['size_bytes'])
            }
        )