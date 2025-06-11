"""Integration module to connect the full crawler with the backend."""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from uuid import UUID

import structlog
from celery import current_task

# Add crawler module to path
crawler_path = Path(__file__).parent.parent.parent.parent / "crawler"
sys.path.insert(0, str(crawler_path))

from crawler.src.crawler import Crawler, CrawlerSettings
from crawler.src.storage import StorageAdapter

from ..repositories.jobs import JobRepository
from ..models.jobs import JobStatus
from ..db.session import get_db_pool
from ..core.config import settings

logger = structlog.get_logger()


class CrawlerIntegration:
    """Integrates the full crawler module with the backend."""
    
    def __init__(self):
        self.crawler = None
        self.job_repo = None
        
    async def initialize(self):
        """Initialize the crawler with backend settings."""
        # Create crawler settings from backend config
        crawler_settings = CrawlerSettings(
            database_url=settings.database_url,
            s3_endpoint=settings.s3_endpoint_url,
            s3_access_key=settings.s3_access_key,
            s3_secret_key=settings.s3_secret_key,
            s3_bucket=settings.s3_bucket,
            proxy_pool_url=getattr(settings, 'proxy_pool_url', None),
            capsolver_api_key=getattr(settings, 'capsolver_api_key', None),
            crawl_rate_limit=getattr(settings, 'crawl_rate_limit', 4),
            max_depth=getattr(settings, 'max_crawl_depth', 10),
            max_pages_per_host=getattr(settings, 'max_pages_per_host', 10000),
        )
        
        # Initialize crawler
        self.crawler = Crawler(crawler_settings)
        await self.crawler.initialize()
        
        # Initialize job repository
        db_pool = await get_db_pool()
        self.job_repo = JobRepository(db_pool)
        
    async def cleanup(self):
        """Clean up resources."""
        if self.crawler:
            await self.crawler.close()
            
    async def run_crawl(
        self,
        job_id: UUID,
        host: str,
        max_pages: int,
        follow_links: bool = True,
        respect_robots_txt: bool = True
    ) -> Dict[str, Any]:
        """Run a crawl job using the full crawler."""
        try:
            # Update job status to running
            await self.job_repo.update_job_status(
                job_id,
                JobStatus.RUNNING
            )
            
            # Set up progress callback
            async def progress_callback(**kwargs):
                """Report progress back to the job tracking system."""
                # Update Celery task state
                if current_task:
                    current_task.update_state(
                        state='PROGRESS',
                        meta={
                            'pages_crawled': kwargs.get('pages_crawled', 0),
                            'pages_discovered': kwargs.get('pages_discovered', 0),
                            'pages_failed': kwargs.get('pages_failed', 0),
                            'bytes_downloaded': kwargs.get('bytes_downloaded', 0),
                            'current_url': kwargs.get('current_url', '')
                        }
                    )
                
                # Update job progress in database
                await self.job_repo.update_job_progress(
                    job_id,
                    pages_crawled=kwargs.get('pages_crawled', 0),
                    pages_discovered=kwargs.get('pages_discovered', 0),
                    current_url=kwargs.get('current_url', '')
                )
            
            # Configure crawler for this job
            self.crawler.set_progress_callback(progress_callback)
            self.crawler.settings.max_pages_per_host = max_pages
            
            # Run the crawl
            logger.info("Starting crawl with full crawler", 
                       job_id=str(job_id), 
                       host=host,
                       max_pages=max_pages)
            
            result = await self.crawler.crawl_host(host)
            
            # Update job status to completed
            await self.job_repo.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                pages_crawled=result['pages_crawled'],
                pages_changed=result['pages_changed'],
                manifest_url=f"https://{settings.s3_endpoint_url}/{settings.s3_bucket}/manifests/{host}/llm.txt"
            )
            
            logger.info("Crawl completed successfully",
                       job_id=str(job_id),
                       host=host,
                       pages_crawled=result['pages_crawled'],
                       pages_changed=result['pages_changed'])
            
            return result
            
        except Exception as e:
            logger.error("Crawl failed",
                        job_id=str(job_id),
                        host=host,
                        error=str(e),
                        exc_info=True)
            
            # Update job status to failed
            await self.job_repo.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(e)
            )
            
            raise


async def run_integrated_crawl(
    job_id: str,
    host: str,
    max_pages: int,
    follow_links: bool = True,
    respect_robots_txt: bool = True
) -> Dict[str, Any]:
    """Async wrapper for running integrated crawl from Celery tasks."""
    integration = CrawlerIntegration()
    
    try:
        await integration.initialize()
        
        result = await integration.run_crawl(
            UUID(job_id),
            host,
            max_pages,
            follow_links,
            respect_robots_txt
        )
        
        return result
        
    finally:
        await integration.cleanup()