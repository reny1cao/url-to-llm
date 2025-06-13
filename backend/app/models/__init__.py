"""Data models for the API."""

# Import Pydantic models for API serialization
from .documentation_dto import (
    SiteResponse,
    PageResponse,
    NavigationResponse,
    PageListResponse,
    SearchResponse,
    SiteCreateRequest,
    CrawlRequest
)

__all__ = [
    "SiteResponse",
    "PageResponse", 
    "NavigationResponse",
    "PageListResponse",
    "SearchResponse",
    "SiteCreateRequest",
    "CrawlRequest"
]
