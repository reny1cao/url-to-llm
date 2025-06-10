"""Crawl management endpoints."""

from typing import Dict, List
from datetime import datetime
import os
import sys

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
import structlog

from ..models.auth import User
from ..services.auth import get_current_user
from ..services.rate_limit import RateLimitService

logger = structlog.get_logger()

router = APIRouter(prefix="/crawl", tags=["crawl"])


async def get_rate_limit_service():
    """Get rate limit service."""
    # For now, create a mock rate limit service
    # In production, you would get the actual Redis client
    import redis.asyncio as redis
    redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)
    return RateLimitService(redis_client)


class CrawlRequest(BaseModel):
    """Request to crawl a host."""
    url: HttpUrl
    max_pages: int = 100


class CrawlStatus(BaseModel):
    """Crawl job status."""
    job_id: str
    host: str
    status: str  # pending, running, completed, failed
    pages_crawled: int = 0
    pages_changed: int = 0
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


class TestCrawlRequest(BaseModel):
    """Test crawl request."""
    url: str


class TestCrawlResponse(BaseModel):
    """Test crawl response."""
    host: str
    manifest: str
    pages_crawled: int
    pages_changed: int


@router.post("/start", response_model=Dict[str, str])
async def start_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    rate_limit: RateLimitService = Depends(get_rate_limit_service),
):
    """Start a crawl job for a host."""
    # Check rate limit
    is_allowed, limit_info = await rate_limit.check_rate_limit(
        f"crawl:user:{current_user.id}",
        limit=10,  # 10 crawls per hour
        window_seconds=3600
    )
    
    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail="Crawl rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(limit_info.limit),
                "X-RateLimit-Remaining": str(limit_info.remaining),
                "X-RateLimit-Reset": limit_info.reset.isoformat(),
                "Retry-After": str(limit_info.retry_after),
            }
        )
    
    # Extract host from URL
    host = request.url.host
    
    # Create job ID
    job_id = f"crawl_{host}_{datetime.utcnow().timestamp()}"
    
    # Queue crawl job
    # In production, this would use a proper task queue like Celery
    background_tasks.add_task(run_crawl, job_id, host, request.max_pages)
    
    logger.info("Crawl job queued", job_id=job_id, host=host, user_id=current_user.id)
    
    return {"job_id": job_id, "status": "queued"}


@router.post("/test", response_model=TestCrawlResponse)
async def test_crawl(request: TestCrawlRequest):
    """Test endpoint to crawl a URL and get manifest directly."""
    from urllib.parse import urlparse
    from ..utils.simple_crawler import SimpleCrawler
    
    # Parse URL to get host
    parsed = urlparse(request.url)
    host = parsed.netloc
    
    if not host:
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    # Create simple crawler
    crawler = SimpleCrawler(max_pages=10)
    
    try:
        logger.info("Starting test crawl", url=request.url, host=host)
        
        # Run crawl
        crawl_result = await crawler.crawl_site(request.url)
        
        # Generate manifest
        manifest = crawler.generate_manifest(crawl_result)
        
        logger.info("Test crawl completed", 
                   host=host, 
                   pages_crawled=crawl_result["pages_crawled"])
        
        return TestCrawlResponse(
            host=host,
            manifest=manifest,
            pages_crawled=crawl_result["pages_crawled"],
            pages_changed=crawl_result["pages_crawled"]  # All pages are "new" in this simple implementation
        )
        
    except Exception as e:
        logger.error("Test crawl failed", url=request.url, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}", response_model=CrawlStatus)
async def get_crawl_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get status of a crawl job."""
    # In production, this would fetch from a job queue/database
    # For now, return mock data
    return CrawlStatus(
        job_id=job_id,
        host="example.com",
        status="completed",
        pages_crawled=50,
        pages_changed=5,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )


@router.get("/history", response_model=List[CrawlStatus])
async def get_crawl_history(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
):
    """Get user's crawl history."""
    # In production, this would query from database
    return []


async def run_crawl(job_id: str, host: str, max_pages: int):
    """Background task to run crawl."""
    logger.info("Starting crawl", job_id=job_id, host=host)
    # This would integrate with the actual crawler
    pass