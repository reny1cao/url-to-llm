"""Development endpoints (disabled in production)."""

from typing import List

import structlog
from fastapi import APIRouter, HTTPException

from ..config import settings
from ..models.mcp import HostInfo, ManifestResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/dev", tags=["Development"])


@router.get("/hosts", response_model=List[HostInfo])
async def list_hosts_dev(storage=None):
    """List all hosts (dev mode - no auth)."""
    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="Not found")

    # Mock data for now
    from datetime import datetime

    return [
        HostInfo(
            host="example.com",
            total_pages=100,
            accessible_pages=85,
            blocked_pages=15,
            last_crawled=datetime.fromisoformat("2024-01-01T00:00:00"),
            manifest_hash="abc123def456",
            change_frequency="daily"
        ),
        HostInfo(
            host="test.org",
            total_pages=50,
            accessible_pages=48,
            blocked_pages=2,
            last_crawled=datetime.fromisoformat("2024-01-02T00:00:00"),
            manifest_hash="789xyz012",
            change_frequency="weekly"
        )
    ]


@router.get("/manifest/{host}", response_model=ManifestResponse)
async def get_manifest_dev(host: str):
    """Get llm.txt manifest for a host (dev mode - no auth)."""
    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="Not found")

    # Mock manifest - return raw manifest content as text
    manifest_content = f"""# {host} llm.txt

This is a development manifest for {host}.

## Overview
This site contains example content for testing.

## Access
- Rate limit: 60 requests per minute
- Authentication: None required

## Content
- Total pages: 100
- Accessible pages: 85
- Last crawled: 2024-01-01

## License
Content is provided for testing purposes only.
"""

    from datetime import datetime

    return ManifestResponse(
        host=host,
        manifest_url=f"{settings.cdn_url}/{host}/llm.txt",
        cdn_url=settings.cdn_url,
        last_updated=datetime.now(),
        pages_count=100,
        content_hash="mock_hash_12345"
    )
