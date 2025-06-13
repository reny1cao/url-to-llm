"""Data Transfer Objects for documentation API.

This module defines Pydantic models for API requests and responses
related to documentation hosting functionality.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class SiteBase(BaseModel):
    """Base model for documentation sites."""
    host: str = Field(..., description="The hostname of the documentation site")
    title: Optional[str] = Field(None, description="Site title")
    description: Optional[str] = Field(None, description="Site description")
    favicon_url: Optional[str] = Field(None, description="URL to site favicon")
    language: str = Field("en", description="Primary language (ISO 639-1)")


class SiteCreateRequest(SiteBase):
    """Request model for creating a new site."""
    crawl_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Crawl configuration settings"
    )


class SiteResponse(SiteBase):
    """Response model for site information."""
    id: UUID
    is_active: bool = Field(True, description="Whether the site is active")
    created_at: datetime
    updated_at: datetime
    last_crawled_at: Optional[datetime] = None
    total_pages: int = Field(0, description="Total number of pages")
    total_size_bytes: int = Field(0, description="Total size in bytes")
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True


class PageBase(BaseModel):
    """Base model for documentation pages."""
    url: str = Field(..., description="Full URL of the page")
    path: str = Field(..., description="Path relative to site root")
    title: Optional[str] = Field(None, description="Page title")
    description: Optional[str] = Field(None, description="Page description")


class PageResponse(PageBase):
    """Response model for page information."""
    id: UUID
    html_size_bytes: Optional[int] = None
    markdown_size_bytes: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    crawled_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class PageListResponse(BaseModel):
    """Response model for paginated page list."""
    pages: List[PageResponse]
    total: int
    limit: int
    offset: int


class NavigationResponse(BaseModel):
    """Response model for navigation structure."""
    id: UUID
    page_id: UUID
    parent_id: Optional[UUID] = None
    title: str
    path: str
    url: str
    description: Optional[str] = None
    order_index: int = 0
    level: int = 0
    is_expanded: bool = True
    metadata: Optional[Dict[str, Any]] = None
    children: List['NavigationResponse'] = []
    
    class Config:
        orm_mode = True


# Update forward references
NavigationResponse.model_rebuild()


class SearchResult(BaseModel):
    """Search result item."""
    id: UUID
    url: str
    path: str
    title: Optional[str]
    description: Optional[str]
    snippet: str = Field(..., description="Highlighted text snippet")
    score: float = Field(..., description="Relevance score")


class SearchResponse(BaseModel):
    """Response model for search results."""
    query: str
    results: List[SearchResult]
    total: int
    limit: int
    offset: int


class AssetResponse(BaseModel):
    """Response model for asset information."""
    id: UUID
    url: str
    path: str
    content_type: str
    size_bytes: int
    created_at: datetime
    
    class Config:
        orm_mode = True


class CrawlRequest(BaseModel):
    """Request model for starting a documentation crawl."""
    url: HttpUrl = Field(..., description="URL to start crawling from")
    max_pages: int = Field(1000, ge=1, le=10000, description="Maximum pages to crawl")
    follow_links: bool = Field(True, description="Whether to follow internal links")
    download_assets: bool = Field(True, description="Whether to download images and assets")
    incremental: bool = Field(False, description="Only update changed pages")
    rate_limit: float = Field(0.5, ge=0.1, le=10.0, description="Seconds between requests")


class CrawlStatusResponse(BaseModel):
    """Response model for crawl job status."""
    job_id: UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    pages_crawled: int = 0
    pages_added: int = 0
    pages_updated: int = 0
    assets_downloaded: int = 0
    errors: List[Dict[str, Any]] = []
    progress_percentage: float = 0.0