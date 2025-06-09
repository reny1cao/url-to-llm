"""Storage layer for crawler - PostgreSQL + S3."""

import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncpg
import aioboto3
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()


class PageRecord(BaseModel):
    """Represents a crawled page record."""
    
    url: str
    host: str
    content_hash: str
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    status_code: int
    headers: Dict[str, str]
    crawled_at: datetime
    content_type: str = "text/html"
    is_blocked: bool = False
    error_message: Optional[str] = None


class CrawlSession(BaseModel):
    """Represents a crawl session."""
    
    id: int
    host: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    pages_crawled: int = 0
    pages_changed: int = 0
    status: str = "running"  # running, completed, failed


class StorageAdapter:
    """Handles all storage operations for the crawler."""
    
    def __init__(
        self,
        db_url: str,
        s3_endpoint: str,
        s3_access_key: str,
        s3_secret_key: str,
        s3_bucket: str,
    ):
        self.db_url = db_url
        self.s3_endpoint = s3_endpoint
        self.s3_access_key = s3_access_key
        self.s3_secret_key = s3_secret_key
        self.s3_bucket = s3_bucket
        self._pool: Optional[asyncpg.Pool] = None
        self._s3_session = None
        
    async def initialize(self):
        """Initialize database connection pool and S3 session."""
        self._pool = await asyncpg.create_pool(self.db_url)
        self._s3_session = aioboto3.Session(
            aws_access_key_id=self.s3_access_key,
            aws_secret_access_key=self.s3_secret_key,
        )
        await self._create_tables()
        
    async def close(self):
        """Close all connections."""
        if self._pool:
            await self._pool.close()
            
    async def _create_tables(self):
        """Create necessary database tables."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS crawl_sessions (
                    id SERIAL PRIMARY KEY,
                    host VARCHAR(255) NOT NULL,
                    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    pages_crawled INTEGER DEFAULT 0,
                    pages_changed INTEGER DEFAULT 0,
                    status VARCHAR(50) DEFAULT 'running'
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id SERIAL PRIMARY KEY,
                    url TEXT NOT NULL UNIQUE,
                    host VARCHAR(255) NOT NULL,
                    content_hash VARCHAR(64) NOT NULL,
                    etag VARCHAR(255),
                    last_modified VARCHAR(255),
                    status_code INTEGER NOT NULL,
                    headers JSONB NOT NULL,
                    crawled_at TIMESTAMP NOT NULL,
                    content_type VARCHAR(100) DEFAULT 'text/html',
                    is_blocked BOOLEAN DEFAULT FALSE,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pages_host ON pages(host);
                CREATE INDEX IF NOT EXISTS idx_pages_crawled_at ON pages(crawled_at);
            """)
            
    async def start_crawl_session(self, host: str) -> int:
        """Start a new crawl session."""
        async with self._pool.acquire() as conn:
            session_id = await conn.fetchval(
                """
                INSERT INTO crawl_sessions (host, started_at)
                VALUES ($1, $2)
                RETURNING id
                """,
                host,
                datetime.utcnow()
            )
            logger.info("Started crawl session", session_id=session_id, host=host)
            return session_id
            
    async def complete_crawl_session(
        self,
        session_id: int,
        pages_crawled: int,
        pages_changed: int,
        status: str = "completed"
    ):
        """Complete a crawl session."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE crawl_sessions
                SET completed_at = $1, pages_crawled = $2, 
                    pages_changed = $3, status = $4
                WHERE id = $5
                """,
                datetime.utcnow(),
                pages_crawled,
                pages_changed,
                status,
                session_id
            )
            
    async def get_page_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get existing page information."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT content_hash, etag, last_modified, crawled_at
                FROM pages
                WHERE url = $1
                """,
                url
            )
            if row:
                return dict(row)
            return None
            
    async def save_page(self, page: PageRecord) -> bool:
        """Save or update a page record. Returns True if page was updated."""
        async with self._pool.acquire() as conn:
            # Check if page exists
            existing = await conn.fetchrow(
                "SELECT id, content_hash FROM pages WHERE url = $1",
                page.url
            )
            
            if existing:
                # Update existing page
                changed = existing['content_hash'] != page.content_hash
                await conn.execute(
                    """
                    UPDATE pages
                    SET content_hash = $1, etag = $2, last_modified = $3,
                        status_code = $4, headers = $5, crawled_at = $6,
                        content_type = $7, is_blocked = $8, error_message = $9,
                        updated_at = NOW()
                    WHERE url = $10
                    """,
                    page.content_hash,
                    page.etag,
                    page.last_modified,
                    page.status_code,
                    page.headers,
                    page.crawled_at,
                    page.content_type,
                    page.is_blocked,
                    page.error_message,
                    page.url
                )
                return changed
            else:
                # Insert new page
                await conn.execute(
                    """
                    INSERT INTO pages (
                        url, host, content_hash, etag, last_modified,
                        status_code, headers, crawled_at, content_type,
                        is_blocked, error_message
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                    page.url,
                    page.host,
                    page.content_hash,
                    page.etag,
                    page.last_modified,
                    page.status_code,
                    page.headers,
                    page.crawled_at,
                    page.content_type,
                    page.is_blocked,
                    page.error_message
                )
                return True
                
    async def save_to_s3(self, key: str, content: bytes, content_type: str = "text/html"):
        """Save content to S3."""
        async with self._s3_session.client(
            's3',
            endpoint_url=self.s3_endpoint
        ) as s3_client:
            await s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=content,
                ContentType=content_type
            )
            
    async def get_from_s3(self, key: str) -> Optional[bytes]:
        """Get content from S3."""
        async with self._s3_session.client(
            's3',
            endpoint_url=self.s3_endpoint
        ) as s3_client:
            try:
                response = await s3_client.get_object(
                    Bucket=self.s3_bucket,
                    Key=key
                )
                return await response['Body'].read()
            except Exception:
                return None
                
    async def get_host_pages(self, host: str) -> List[Dict[str, Any]]:
        """Get all pages for a host."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT url, content_hash, status_code, crawled_at,
                       is_blocked, error_message
                FROM pages
                WHERE host = $1
                ORDER BY crawled_at DESC
                """,
                host
            )
            return [dict(row) for row in rows]
            
    async def get_hosts(self) -> List[Dict[str, Any]]:
        """Get all crawled hosts with stats."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    host,
                    COUNT(*) as total_pages,
                    COUNT(CASE WHEN is_blocked THEN 1 END) as blocked_pages,
                    MAX(crawled_at) as last_crawled,
                    COUNT(CASE WHEN crawled_at > NOW() - INTERVAL '1 day' THEN 1 END) as recent_changes
                FROM pages
                GROUP BY host
                ORDER BY last_crawled DESC
                """
            )
            return [dict(row) for row in rows]
            
    @staticmethod
    def compute_content_hash(content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()