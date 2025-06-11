"""Database session management."""

import asyncpg
from typing import Optional

from ..core.config import settings

# Global database pool
_db_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """Get or create database connection pool."""
    global _db_pool
    
    if _db_pool is None:
        _db_pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=10,
            max_size=20,
            command_timeout=60
        )
    
    return _db_pool


async def close_db_pool():
    """Close database connection pool."""
    global _db_pool
    
    if _db_pool is not None:
        await _db_pool.close()
        _db_pool = None