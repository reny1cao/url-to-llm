"""Rate limiting service."""

import time
from typing import Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

from fastapi import HTTPException
import structlog

logger = structlog.get_logger()


class RateLimitService:
    """Service for managing API rate limits."""
    
    def __init__(
        self,
        default_limit: int = 60,
        window_seconds: int = 60,
        burst_multiplier: float = 1.5
    ):
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.burst_multiplier = burst_multiplier
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(
        self,
        user_id: str,
        limit: Optional[int] = None,
        resource: str = "default"
    ) -> bool:
        """Check if user has exceeded rate limit."""
        
        limit = limit or self.default_limit
        burst_limit = int(limit * self.burst_multiplier)
        key = f"{user_id}:{resource}"
        
        async with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            
            # Clean old requests
            self._requests[key] = [
                req_time for req_time in self._requests[key]
                if req_time > window_start
            ]
            
            # Check limits
            request_count = len(self._requests[key])
            
            if request_count >= burst_limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Max {limit} requests per {self.window_seconds} seconds."
                )
            
            # Log request
            self._requests[key].append(now)
            
            # Warn if approaching limit
            if request_count >= limit * 0.8:
                logger.warning(
                    "User approaching rate limit",
                    user_id=user_id,
                    resource=resource,
                    requests=request_count,
                    limit=limit
                )
            
            return True
    
    async def get_remaining_requests(
        self,
        user_id: str,
        limit: Optional[int] = None,
        resource: str = "default"
    ) -> int:
        """Get remaining requests for user."""
        
        limit = limit or self.default_limit
        key = f"{user_id}:{resource}"
        
        async with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            
            # Count recent requests
            self._requests[key] = [
                req_time for req_time in self._requests[key]
                if req_time > window_start
            ]
            
            request_count = len(self._requests[key])
            return max(0, limit - request_count)
    
    async def reset_user_limit(self, user_id: str, resource: str = "default"):
        """Reset rate limit for a specific user."""
        
        key = f"{user_id}:{resource}"
        async with self._lock:
            self._requests[key] = []
    
    def get_reset_time(self) -> datetime:
        """Get time when rate limits reset."""
        return datetime.utcnow() + timedelta(seconds=self.window_seconds)