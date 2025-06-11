"""Job tracking models for crawl tasks."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Job type enumeration."""
    CRAWL = "crawl"
    MANIFEST_GENERATION = "manifest_generation"
    SCHEDULED_CRAWL = "scheduled_crawl"


class CrawlJob(BaseModel):
    """Model for crawl job tracking."""
    id: UUID = Field(default_factory=uuid4)
    type: JobType = JobType.CRAWL
    status: JobStatus = JobStatus.PENDING
    host: str
    max_pages: int = 100
    follow_links: bool = True
    respect_robots_txt: bool = True
    
    # Task metadata
    celery_task_id: Optional[str] = None
    queue_name: str = "crawler"
    priority: int = 5  # 1-10, higher is more important
    
    # Progress tracking
    pages_crawled: int = 0
    pages_discovered: int = 0
    pages_failed: int = 0
    bytes_downloaded: int = 0
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    manifest_url: Optional[str] = None
    
    # User tracking
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class JobProgress(BaseModel):
    """Real-time job progress update."""
    job_id: UUID
    status: JobStatus
    pages_crawled: int
    pages_discovered: int
    pages_failed: int
    bytes_downloaded: int
    current_url: Optional[str] = None
    message: Optional[str] = None
    progress_percentage: float = 0.0
    estimated_time_remaining: Optional[int] = None  # seconds
    
    
class JobFilter(BaseModel):
    """Filter for job queries."""
    status: Optional[JobStatus] = None
    type: Optional[JobType] = None
    host: Optional[str] = None
    created_by: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    

class JobCreateRequest(BaseModel):
    """Request to create a new crawl job."""
    host: str
    max_pages: int = Field(default=100, ge=1, le=10000)
    follow_links: bool = True
    respect_robots_txt: bool = True
    priority: int = Field(default=5, ge=1, le=10)
    

class JobResponse(BaseModel):
    """Response for job queries."""
    job: CrawlJob
    estimated_duration: Optional[int] = None  # seconds
    position_in_queue: Optional[int] = None