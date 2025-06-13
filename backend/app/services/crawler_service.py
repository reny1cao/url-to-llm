"""Crawler service for managing crawl operations."""

import asyncio
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

import structlog
from fastapi import BackgroundTasks

from ..crawler import WebCrawler, ManifestGenerator
from ..crawler.documentation_crawler import DocumentationCrawler
from ..models.jobs import CrawlJob, JobStatus
from ..repositories.jobs import JobRepository
from ..services.storage import StorageService

logger = structlog.get_logger()


class CrawlerService:
    """Service for managing crawl operations."""
    
    def __init__(self, job_repo: JobRepository, storage: StorageService):
        self.job_repo = job_repo
        self.storage = storage
        self.active_crawls: Dict[UUID, asyncio.Task] = {}
    
    async def start_crawl(
        self,
        job: CrawlJob,
        background_tasks: BackgroundTasks
    ) -> CrawlJob:
        """Start a crawl job."""
        # Update job status to pending
        job = await self.job_repo.update_job_status(job.id, JobStatus.PENDING)
        
        # Add to background tasks
        background_tasks.add_task(
            self._run_crawl,
            job.id,
            job.host,
            job.max_pages,
            job.follow_links,
            job.respect_robots_txt
        )
        
        logger.info("Crawl job queued", job_id=str(job.id), host=job.host)
        return job
    
    async def _run_crawl(
        self,
        job_id: UUID,
        host: str,
        max_pages: int,
        follow_links: bool,
        respect_robots_txt: bool
    ):
        """Run the actual crawl operation."""
        logger.info("Starting crawl", job_id=str(job_id), host=host)
        
        try:
            # Update job status to running
            await self.job_repo.update_job_status(job_id, JobStatus.RUNNING)
            
            # Create crawler instance
            crawler = WebCrawler(
                max_pages=max_pages,
                follow_links=follow_links,
                respect_robots_txt=respect_robots_txt,
                rate_limit=1.0  # 1 second between requests
            )
            
            # Progress callback
            async def progress_callback(**kwargs):
                await self.job_repo.update_job_progress(
                    job_id,
                    pages_crawled=kwargs.get('pages_crawled', 0),
                    pages_discovered=kwargs.get('pages_discovered', 0),
                    current_url=kwargs.get('current_url', '')
                )
            
            # Start crawling
            start_url = f"https://{host}"
            crawl_result = await crawler.crawl(start_url, progress_callback)
            
            # Generate manifest
            manifest_generator = ManifestGenerator()
            manifest_content = manifest_generator.generate(crawl_result)
            
            # Store manifest
            manifest_url = await self.storage.put_manifest(host, manifest_content)
            
            # Update job as completed
            await self.job_repo.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                pages_crawled=crawl_result['pages_crawled'],
                pages_changed=crawl_result['pages_crawled'],  # For simplicity
                manifest_url=manifest_url
            )
            
            logger.info(
                "Crawl completed successfully",
                job_id=str(job_id),
                host=host,
                pages_crawled=crawl_result['pages_crawled']
            )
            
        except Exception as e:
            logger.error(
                "Crawl failed",
                job_id=str(job_id),
                host=host,
                error=str(e),
                exc_info=True
            )
            
            # Update job as failed
            await self.job_repo.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(e)
            )
    
    async def cancel_crawl(self, job_id: UUID) -> bool:
        """Cancel a running crawl job."""
        # Check if job exists and is cancellable
        job = await self.job_repo.get_job(job_id)
        if not job or job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
            return False
        
        # Update job status
        await self.job_repo.update_job_status(job_id, JobStatus.CANCELLED)
        
        # If there's an active task, cancel it
        if job_id in self.active_crawls:
            task = self.active_crawls[job_id]
            task.cancel()
            del self.active_crawls[job_id]
        
        logger.info("Crawl job cancelled", job_id=str(job_id))
        return True
    
    async def run_test_crawl(self, url: str) -> Dict:
        """Run a quick test crawl without creating a job."""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        host = parsed.netloc
        
        if not host:
            raise ValueError("Invalid URL")
        
        # Create a limited crawler
        crawler = WebCrawler(
            max_pages=10,
            follow_links=True,
            respect_robots_txt=True,
            rate_limit=0.5  # Faster for testing
        )
        
        # Run crawl
        crawl_result = await crawler.crawl(url)
        
        # Generate manifest
        manifest_generator = ManifestGenerator()
        manifest = manifest_generator.generate(crawl_result)
        
        return {
            "host": host,
            "manifest": manifest,
            "pages_crawled": crawl_result['pages_crawled'],
            "pages_changed": crawl_result['pages_crawled']
        }