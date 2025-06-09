"""Model Context Protocol (MCP) models."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MCPTool(BaseModel):
    """MCP tool definition."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]


class MCPRequest(BaseModel):
    """MCP tool invocation request."""

    tool: str
    parameters: Dict[str, Any]
    request_id: Optional[str] = None


class MCPResponse(BaseModel):
    """MCP tool response."""

    request_id: Optional[str] = None
    result: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ManifestResponse(BaseModel):
    """Response for llm.fetch_manifest tool."""

    host: str
    manifest_url: str
    cdn_url: str
    last_updated: datetime
    pages_count: int
    content_hash: str


class PageResponse(BaseModel):
    """Response for llm.fetch_page tool."""

    url: str
    content_url: str
    content_type: str
    last_crawled: datetime
    content_hash: str
    status: str  # accessible, blocked, error


class HostInfo(BaseModel):
    """Information about a crawled host."""

    host: str
    total_pages: int
    accessible_pages: int
    blocked_pages: int
    last_crawled: datetime
    manifest_hash: str
    change_frequency: str  # daily, weekly, monthly


class CrawlStatus(BaseModel):
    """Real-time crawl status."""

    session_id: int
    host: str
    status: str  # running, completed, failed
    progress: float  # 0-100
    pages_crawled: int
    pages_changed: int
    started_at: datetime
    eta: Optional[datetime] = None
