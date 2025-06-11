"""Job repository for database operations."""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

import asyncpg

from ..models.jobs import CrawlJob, JobStatus, JobFilter, JobType


class JobRepository:
    """Repository for job-related database operations."""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def create_job(
        self,
        host: str,
        max_pages: int,
        follow_links: bool,
        respect_robots_txt: bool,
        created_by: Optional[str] = None,
        priority: int = 5,
        job_type: JobType = JobType.CRAWL
    ) -> CrawlJob:
        """Create a new job in the database."""
        
        query = """
            INSERT INTO jobs (
                host, max_pages, follow_links, respect_robots_txt,
                created_by, priority, type, status, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                host,
                max_pages,
                follow_links,
                respect_robots_txt,
                created_by,
                priority,
                job_type,
                JobStatus.PENDING,
                datetime.utcnow()
            )
            
            return self._row_to_job(row)
    
    async def get_job(self, job_id: UUID) -> Optional[CrawlJob]:
        """Get a job by ID."""
        
        query = "SELECT * FROM jobs WHERE id = $1"
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, job_id)
            
            if row:
                return self._row_to_job(row)
            return None
    
    async def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        celery_task_id: Optional[str] = None,
        error: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        manifest_url: Optional[str] = None
    ):
        """Update job status and related fields."""
        
        updates = ["status = $2", "updated_at = $3"]
        values = [job_id, status, datetime.utcnow()]
        param_count = 3
        
        if celery_task_id is not None:
            param_count += 1
            updates.append(f"celery_task_id = ${param_count}")
            values.append(celery_task_id)
        
        if status == JobStatus.RUNNING and "started_at = " not in updates:
            param_count += 1
            updates.append(f"started_at = ${param_count}")
            values.append(datetime.utcnow())
        
        if status in (JobStatus.COMPLETED, JobStatus.FAILED):
            param_count += 1
            updates.append(f"completed_at = ${param_count}")
            values.append(datetime.utcnow())
        
        if error is not None:
            param_count += 1
            updates.append(f"error = ${param_count}")
            values.append(error)
        
        if result is not None:
            param_count += 1
            updates.append(f"result = ${param_count}")
            values.append(json.dumps(result))
        
        if manifest_url is not None:
            param_count += 1
            updates.append(f"manifest_url = ${param_count}")
            values.append(manifest_url)
        
        query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = $1"
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(query, *values)
    
    async def update_job_progress(
        self,
        job_id: UUID,
        pages_crawled: int,
        pages_discovered: int,
        pages_failed: int,
        bytes_downloaded: int,
        current_url: Optional[str] = None
    ):
        """Update job progress metrics."""
        
        query = """
            UPDATE jobs 
            SET pages_crawled = $2,
                pages_discovered = $3,
                pages_failed = $4,
                bytes_downloaded = $5,
                updated_at = $6
            WHERE id = $1
        """
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                job_id,
                pages_crawled,
                pages_discovered,
                pages_failed,
                bytes_downloaded,
                datetime.utcnow()
            )
    
    async def list_jobs(
        self,
        filter_params: JobFilter,
        limit: int = 100,
        offset: int = 0
    ) -> List[CrawlJob]:
        """List jobs with filtering."""
        
        conditions = []
        values = []
        param_count = 0
        
        if filter_params.status:
            param_count += 1
            conditions.append(f"status = ${param_count}")
            values.append(filter_params.status)
        
        if filter_params.type:
            param_count += 1
            conditions.append(f"type = ${param_count}")
            values.append(filter_params.type)
        
        if filter_params.host:
            param_count += 1
            conditions.append(f"host ILIKE ${param_count}")
            values.append(f"%{filter_params.host}%")
        
        if filter_params.created_by:
            param_count += 1
            conditions.append(f"created_by = ${param_count}")
            values.append(filter_params.created_by)
        
        if filter_params.created_after:
            param_count += 1
            conditions.append(f"created_at >= ${param_count}")
            values.append(filter_params.created_after)
        
        if filter_params.created_before:
            param_count += 1
            conditions.append(f"created_at <= ${param_count}")
            values.append(filter_params.created_before)
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        param_count += 1
        limit_param = f"${param_count}"
        values.append(limit)
        
        param_count += 1
        offset_param = f"${param_count}"
        values.append(offset)
        
        query = f"""
            SELECT * FROM jobs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT {limit_param} OFFSET {offset_param}
        """
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *values)
            
            return [self._row_to_job(row) for row in rows]
    
    async def get_pending_jobs(self, limit: int = 10) -> List[CrawlJob]:
        """Get pending jobs for processing."""
        
        query = """
            SELECT * FROM jobs
            WHERE status = $1
            ORDER BY priority DESC, created_at ASC
            LIMIT $2
        """
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, JobStatus.PENDING, limit)
            
            return [self._row_to_job(row) for row in rows]
    
    async def count_jobs_in_queue(self, created_by: Optional[str] = None) -> int:
        """Count jobs in queue (pending or running)."""
        
        if created_by:
            query = """
                SELECT COUNT(*) FROM jobs
                WHERE status IN ($1, $2) AND created_by = $3
            """
            values = [JobStatus.PENDING, JobStatus.RUNNING, created_by]
        else:
            query = """
                SELECT COUNT(*) FROM jobs
                WHERE status IN ($1, $2)
            """
            values = [JobStatus.PENDING, JobStatus.RUNNING]
        
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval(query, *values)
            return result or 0
    
    def _row_to_job(self, row: asyncpg.Record) -> CrawlJob:
        """Convert database row to CrawlJob model."""
        
        data = dict(row)
        
        # Parse JSON fields
        if data.get('result') and isinstance(data['result'], str):
            data['result'] = json.loads(data['result'])
        
        return CrawlJob(**data)