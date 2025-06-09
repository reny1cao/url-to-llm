"""Dependency injection for FastAPI."""

from typing import Any, AsyncGenerator, Optional

import aioboto3
import asyncpg
import redis.asyncio as redis
import structlog
from fastapi import Depends

from .config import settings
from .services.auth import AuthService
from .services.rate_limit import RateLimitService

logger = structlog.get_logger()

# Global instances
_redis_pool: Optional[redis.ConnectionPool] = None
_pg_pool: Optional[asyncpg.Pool] = None
_s3_session: Optional[aioboto3.Session] = None


async def init_dependencies():
    """Initialize global dependencies."""
    global _redis_pool, _pg_pool, _s3_session

    # Redis connection pool
    _redis_pool = redis.ConnectionPool.from_url(
        settings.redis_url,
        max_connections=50,
        decode_responses=True
    )

    # PostgreSQL connection pool
    _pg_pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=10,
        max_size=20
    )

    # S3 session
    _s3_session = aioboto3.Session(
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )

    logger.info("Dependencies initialized")


async def close_dependencies():
    """Close all dependencies."""
    global _redis_pool, _pg_pool

    if _redis_pool:
        await _redis_pool.disconnect()

    if _pg_pool:
        await _pg_pool.close()

    logger.info("Dependencies closed")


# Dependency functions

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """Get Redis client."""
    async with redis.Redis(connection_pool=_redis_pool) as client:
        yield client


async def get_db() -> AsyncGenerator[asyncpg.Pool, None]:
    """Get database connection pool."""
    yield _pg_pool


async def get_s3_client() -> AsyncGenerator[Any, None]:
    """Get S3 client."""
    async with _s3_session.client(
        's3',
        endpoint_url=settings.s3_endpoint
    ) as client:
        yield client


async def get_storage() -> AsyncGenerator[Any, None]:
    """Get storage adapter instance."""
    # Import here to avoid circular imports
    from crawler.src.storage import StorageAdapter

    storage = StorageAdapter(
        db_url=settings.database_url,
        s3_endpoint=settings.s3_endpoint,
        s3_access_key=settings.s3_access_key,
        s3_secret_key=settings.s3_secret_key,
        s3_bucket=settings.s3_bucket,
    )
    # Use existing pool
    storage._pool = _pg_pool
    storage._s3_session = _s3_session

    yield storage


async def get_auth_service(
    redis_client: redis.Redis = Depends(get_redis)
) -> AuthService:
    """Get auth service instance."""
    return AuthService(redis_client)


async def get_rate_limit_service(
    redis_client: redis.Redis = Depends(get_redis)
) -> RateLimitService:
    """Get rate limit service instance."""
    return RateLimitService(redis_client)
