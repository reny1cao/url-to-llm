"""Application dependencies."""

from typing import Optional
import asyncpg
from fastapi import Depends

from .db.session import get_db_pool
from .repositories.jobs import JobRepository
from .services.rate_limit import RateLimitService
from .services.auth import AuthService
from .services.storage import StorageService

# Global instances
_pg_pool: Optional[asyncpg.Pool] = None
_rate_limit_service: Optional[RateLimitService] = None


async def init_dependencies():
    """Initialize dependencies on startup."""
    global _pg_pool, _rate_limit_service
    
    # Initialize database pool
    _pg_pool = await get_db_pool()
    
    # Initialize rate limit service
    _rate_limit_service = RateLimitService()


async def cleanup_dependencies():
    """Cleanup dependencies on shutdown."""
    global _pg_pool
    
    if _pg_pool:
        await _pg_pool.close()
        _pg_pool = None


async def get_db() -> asyncpg.Pool:
    """Get database connection pool."""
    if _pg_pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pg_pool


async def get_job_repository(
    db_pool: asyncpg.Pool = Depends(get_db)
) -> JobRepository:
    """Get job repository instance."""
    return JobRepository(db_pool)


async def get_rate_limit_service() -> RateLimitService:
    """Get rate limit service instance."""
    if _rate_limit_service is None:
        raise RuntimeError("Rate limit service not initialized")
    return _rate_limit_service


async def get_auth_service(
    db_pool: asyncpg.Pool = Depends(get_db)
) -> AuthService:
    """Get auth service instance."""
    return AuthService(db_pool)


async def get_storage() -> StorageService:
    """Get storage service instance."""
    return StorageService()