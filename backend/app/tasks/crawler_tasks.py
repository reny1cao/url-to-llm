"""Crawler tasks for Celery."""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

from celery import Task
from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import get_db_pool
from app.repositories.jobs import JobRepository
from app.models.jobs import JobStatus, CrawlJob, JobProgress
from app.tasks.crawler_integration import run_integrated_crawl

logger = get_task_logger(__name__)


class CrawlerTask(Task):
    """Base task with database connection management."""
    _db_pool = None
    _job_repo = None
    
    @property
    def db_pool(self):
        if self._db_pool is None:
            # Create database pool synchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._db_pool = loop.run_until_complete(get_db_pool())
        return self._db_pool
    
    @property
    def job_repo(self):
        if self._job_repo is None:
            self._job_repo = JobRepository(self.db_pool)
        return self._job_repo


@celery_app.task(
    bind=True,
    base=CrawlerTask,
    name="app.tasks.crawler_tasks.run_crawl_task",
    max_retries=3,
    default_retry_delay=60
)
def run_crawl_task(
    self, 
    job_id: str,
    host: str,
    max_pages: int = 100,
    follow_links: bool = True,
    respect_robots_txt: bool = True
) -> Dict[str, Any]:
    """Run a crawl task asynchronously."""
    
    job_uuid = UUID(job_id)
    logger.info(f"Starting crawl task for job {job_id}, host: {host}")
    
    # Create event loop for async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Use the full crawler integration
        logger.info(f"Starting integrated crawl for {host}")
        
        # Run the integrated crawl
        result = loop.run_until_complete(
            run_integrated_crawl(
                job_id=job_id,
                host=host,
                max_pages=max_pages,
                follow_links=follow_links,
                respect_robots_txt=respect_robots_txt
            )
        )
        
        logger.info(f"Crawl completed successfully for {host}")
        return result
        
    except Exception as e:
        logger.error(f"Crawl failed for {host}: {str(e)}", exc_info=True)
        
        # Update job as failed
        loop.run_until_complete(
            self.job_repo.update_job_status(
                job_uuid,
                JobStatus.FAILED,
                error=str(e)
            )
        )
        
        # Retry if possible
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying crawl for {host} (attempt {self.request.retries + 1})")
            raise self.retry(exc=e)
        
        return {
            "status": "failed",
            "error": str(e),
            "host": host
        }
        
    finally:
        # Clean up event loop
        loop.close()


@celery_app.task(name="app.tasks.crawler_tasks.cleanup_old_jobs")
def cleanup_old_jobs():
    """Clean up old completed jobs (runs daily)."""
    logger.info("Starting cleanup of old jobs")
    
    # This would be implemented to clean up jobs older than X days
    # For now, just log
    logger.info("Cleanup completed")
    
    return {"status": "completed"}