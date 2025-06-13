"""Crawl management endpoints."""

from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
import structlog

from ..models.auth import User
from ..models.jobs import (
    JobCreateRequest, JobResponse, CrawlJob, JobFilter,
    JobStatus, JobProgress
)
from ..services.auth import get_current_user
from ..services.rate_limit import RateLimitService
from ..repositories.jobs import JobRepository
from ..dependencies import get_job_repository, get_rate_limit_service, get_crawler_service
from ..services.crawler_service import CrawlerService

logger = structlog.get_logger()

router = APIRouter(prefix="/crawl", tags=["crawl"])


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


@router.post("/start", response_model=JobResponse)
async def start_crawl(
    request: JobCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    rate_limit: RateLimitService = Depends(get_rate_limit_service),
    job_repo: JobRepository = Depends(get_job_repository),
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
    
    # Create crawl job
    job = CrawlJob(
        host=request.host,
        max_pages=request.max_pages,
        follow_links=request.follow_links,
        respect_robots_txt=request.respect_robots_txt,
        priority=request.priority,
        created_by=current_user.id
    )
    
    # Save job to database
    job = await job_repo.create_job(job)
    
    # Get crawler service from dependency
    crawler_service = await get_crawler_service(job_repo)
    
    # Start crawl in background
    job = await crawler_service.start_crawl(job, background_tasks)
    
    # Get queue position
    position = await job_repo.get_queue_position(job.id)
    
    logger.info("Crawl job created", 
                job_id=str(job.id), 
                host=job.host, 
                user_id=current_user.id)
    
    return JobResponse(
        job=job,
        position_in_queue=position
    )


@router.post("/test", response_model=TestCrawlResponse)
async def test_crawl(
    request: TestCrawlRequest,
    crawler_service: CrawlerService = Depends(get_crawler_service)
):
    """Test endpoint to crawl a URL and get manifest directly."""
    try:
        logger.info("Starting test crawl", url=request.url)
        
        # Run test crawl
        result = await crawler_service.run_test_crawl(request.url)
        
        logger.info("Test crawl completed", 
                   host=result["host"], 
                   pages_crawled=result["pages_crawled"])
        
        return TestCrawlResponse(
            host=result["host"],
            manifest=result["manifest"],
            pages_crawled=result["pages_crawled"],
            pages_changed=result["pages_changed"]
        )
        
    except Exception as e:
        logger.error("Test crawl failed", url=request.url, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}", response_model=JobResponse)
async def get_crawl_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    job_repo: JobRepository = Depends(get_job_repository),
):
    """Get status of a crawl job."""
    job = await job_repo.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if user owns this job
    if job.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get queue position if pending
    position = None
    if job.status == JobStatus.PENDING:
        position = await job_repo.get_queue_position(job_id)
    
    return JobResponse(
        job=job,
        position_in_queue=position
    )


@router.get("/history", response_model=List[CrawlJob])
async def get_crawl_history(
    limit: int = 10,
    offset: int = 0,
    status: Optional[JobStatus] = None,
    current_user: User = Depends(get_current_user),
    job_repo: JobRepository = Depends(get_job_repository),
):
    """Get user's crawl history."""
    filter = JobFilter(
        created_by=current_user.id,
        status=status
    )
    
    jobs = await job_repo.list_jobs(filter, limit=limit, offset=offset)
    return jobs


@router.get("/jobs/{job_id}/progress", response_model=List[JobProgress])
async def get_job_progress(
    job_id: UUID,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    job_repo: JobRepository = Depends(get_job_repository),
):
    """Get progress history for a job."""
    job = await job_repo.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if user owns this job
    if job.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    progress = await job_repo.get_job_progress_history(job_id, limit=limit)
    return progress


@router.post("/jobs/{job_id}/cancel", response_model=CrawlJob)
async def cancel_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    job_repo: JobRepository = Depends(get_job_repository),
):
    """Cancel a crawl job."""
    job = await job_repo.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if user owns this job
    if job.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if job can be cancelled
    if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel job in {job.status} state"
        )
    
    # Get crawler service and cancel job
    crawler_service = await get_crawler_service(job_repo)
    
    # Cancel the crawl
    success = await crawler_service.cancel_crawl(job_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to cancel job")
    
    # Get updated job
    job = await job_repo.get_job(job_id)
    return job


