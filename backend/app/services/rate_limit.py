"""Rate limiting service using Redis."""

from datetime import datetime, timedelta, timezone
from typing import Tuple

import redis.asyncio as redis
import structlog

from ..models.auth import RateLimitInfo

logger = structlog.get_logger()


class RateLimitService:
    """Handle rate limiting with sliding window algorithm."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60
    ) -> Tuple[bool, RateLimitInfo]:
        """
        Check if request is within rate limit.

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=window_seconds)

        # Use Redis sorted set for sliding window
        pipe = self.redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(
            f"rate_limit:{key}",
            "-inf",
            window_start.timestamp()
        )

        # Count requests in window
        pipe.zcard(f"rate_limit:{key}")

        # Execute pipeline
        results = await pipe.execute()
        current_count = results[1]

        # Check if under limit
        if current_count < limit:
            # Add current request
            await self.redis.zadd(
                f"rate_limit:{key}",
                {str(now.timestamp()): now.timestamp()}
            )

            # Set expiry
            await self.redis.expire(f"rate_limit:{key}", window_seconds + 1)

            rate_limit_info = RateLimitInfo(
                limit=limit,
                remaining=limit - current_count - 1,
                reset=now + timedelta(seconds=window_seconds)
            )

            return True, rate_limit_info
        else:
            # Get oldest request time to calculate retry_after
            oldest_timestamp = await self.redis.zrange(
                f"rate_limit:{key}",
                0,
                0,
                withscores=True
            )

            if oldest_timestamp:
                oldest_time = datetime.fromtimestamp(
                    oldest_timestamp[0][1],
                    tz=timezone.utc
                )
                retry_after = int(
                    (oldest_time + timedelta(seconds=window_seconds) - now).total_seconds()
                )
            else:
                retry_after = window_seconds

            rate_limit_info = RateLimitInfo(
                limit=limit,
                remaining=0,
                reset=now + timedelta(seconds=retry_after),
                retry_after=retry_after
            )

            return False, rate_limit_info

    async def get_token_key(self, token: str) -> str:
        """Get rate limit key for a token."""
        # In production, would decode token to get user ID
        # For now, use token prefix
        return f"token:{token[:16]}"
