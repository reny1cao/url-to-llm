"""Model Context Protocol (MCP) API endpoints."""

from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer

from ..core.config import settings
from ..dependencies import (
    get_auth_service,
    get_rate_limit_service,
    get_storage,
)
from ..models.auth import RateLimitInfo, TokenData
from ..models.mcp import (
    HostInfo,
    MCPRequest,
    MCPResponse,
    MCPTool,
    PageResponse,
)
from ..services.auth import AuthService
from ..services.rate_limit import RateLimitService

logger = structlog.get_logger()

router = APIRouter(prefix="/tools", tags=["MCP"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def verify_token_and_scope(
    token: Annotated[str, Depends(oauth2_scheme)],
    required_scope: str,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> TokenData:
    """Verify token and check required scope."""
    token_data = await auth_service.verify_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    if required_scope not in token_data.scopes:
        raise HTTPException(
            status_code=403,
            detail=f"Missing required scope: {required_scope}"
        )

    return token_data


async def check_rate_limit(
    token: Annotated[str, Depends(oauth2_scheme)],
    response: Response,
    rate_limit_service: Annotated[RateLimitService, Depends(get_rate_limit_service)]
) -> RateLimitInfo:
    """Check rate limit for token."""
    key = await rate_limit_service.get_token_key(token)
    is_allowed, rate_info = await rate_limit_service.check_rate_limit(
        key,
        settings.rate_limit_per_minute,
        60
    )

    # Set rate limit headers
    response.headers["X-RateLimit-Limit"] = str(rate_info.limit)
    response.headers["X-RateLimit-Remaining"] = str(rate_info.remaining)
    response.headers["X-RateLimit-Reset"] = str(int(rate_info.reset.timestamp()))

    if not is_allowed:
        response.headers["Retry-After"] = str(rate_info.retry_after)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(rate_info.retry_after)
            }
        )

    return rate_info


@router.get("/", response_model=list[MCPTool])
async def list_tools():
    """List available MCP tools."""
    tools = [
        MCPTool(
            name="llm.fetch_manifest",
            description="Fetch the llm.txt manifest for a host",
            input_schema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "The host to fetch manifest for"
                    }
                },
                "required": ["host"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "manifest_url": {"type": "string"},
                    "cdn_url": {"type": "string"},
                    "last_updated": {"type": "string", "format": "date-time"},
                    "pages_count": {"type": "integer"},
                    "content_hash": {"type": "string"}
                }
            }
        ),
        MCPTool(
            name="llm.fetch_page",
            description="Fetch a specific page content",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The page URL to fetch"
                    }
                },
                "required": ["url"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "content_url": {"type": "string"},
                    "content_type": {"type": "string"},
                    "last_crawled": {"type": "string", "format": "date-time"},
                    "content_hash": {"type": "string"},
                    "status": {"type": "string"}
                }
            }
        ),
        MCPTool(
            name="llm.list_hosts",
            description="List all crawled hosts",
            input_schema={
                "type": "object",
                "properties": {}
            },
            output_schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "total_pages": {"type": "integer"},
                        "last_crawled": {"type": "string", "format": "date-time"}
                    }
                }
            }
        )
    ]
    return tools


@router.get("/llm.fetch_manifest")
async def fetch_manifest(
    host: str,
    token_data: Annotated[TokenData, Depends(lambda t: verify_token_and_scope(t, "read:llm", get_auth_service()))],
    rate_info: Annotated[RateLimitInfo, Depends(check_rate_limit)],
    storage: Annotated[Any, Depends(get_storage)]
) -> RedirectResponse:
    """Fetch llm.txt manifest for a host."""
    # Check if host exists
    hosts = await storage.get_hosts()
    host_exists = any(h['host'] == host for h in hosts)

    if not host_exists:
        raise HTTPException(status_code=404, detail=f"Host {host} not found")

    # Redirect to CDN URL
    manifest_url = f"{settings.cdn_url}/llm/{host}/llm.txt"

    logger.info(
        "Manifest fetch",
        user=token_data.sub,
        host=host,
        url=manifest_url
    )

    return RedirectResponse(url=manifest_url, status_code=302)


@router.get("/llm.fetch_page")
async def fetch_page(
    url: str,
    token_data: Annotated[TokenData, Depends(lambda t: verify_token_and_scope(t, "read:html", get_auth_service()))],
    rate_info: Annotated[RateLimitInfo, Depends(check_rate_limit)],
    storage: Annotated[Any, Depends(get_storage)]
) -> PageResponse:
    """Fetch a specific page content."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.netloc

    # Get page info from database
    page_info = await storage.get_page_info(url)

    if not page_info:
        raise HTTPException(status_code=404, detail="Page not found")

    # Build S3 key
    path = parsed.path.lstrip('/')
    if not path:
        path = "index.html"
    elif not path.endswith('.html'):
        path += '/index.html'

    content_url = f"{settings.cdn_url}/pages/{host}/{path}"

    return PageResponse(
        url=url,
        content_url=content_url,
        content_type="text/html",
        last_crawled=page_info['crawled_at'],
        content_hash=page_info['content_hash'],
        status="accessible" if not page_info.get('is_blocked') else "blocked"
    )


@router.get("/llm.list_hosts", response_model=list[HostInfo])
async def list_hosts(
    token_data: Annotated[TokenData, Depends(lambda t: verify_token_and_scope(t, "read:llm", get_auth_service()))],
    rate_info: Annotated[RateLimitInfo, Depends(check_rate_limit)],
    storage: Annotated[Any, Depends(get_storage)]
) -> list[HostInfo]:
    """List all crawled hosts."""
    hosts = await storage.get_hosts()

    result = []
    for host_data in hosts:
        # Get manifest info
        manifest_content = await storage.get_from_s3(f"llm/{host_data['host']}/llm.txt")
        if manifest_content:
            import hashlib
            manifest_hash = hashlib.sha256(manifest_content).hexdigest()
        else:
            manifest_hash = ""

        result.append(HostInfo(
            host=host_data['host'],
            total_pages=host_data['total_pages'],
            accessible_pages=host_data['total_pages'] - host_data.get('blocked_pages', 0),
            blocked_pages=host_data.get('blocked_pages', 0),
            last_crawled=host_data['last_crawled'],
            manifest_hash=manifest_hash[:16],
            change_frequency="daily"  # Placeholder
        ))

    return result


@router.post("/invoke", response_model=MCPResponse)
async def invoke_tool(
    request: MCPRequest,
    token_data: Annotated[TokenData, Depends(lambda t: verify_token_and_scope(t, "read:llm", get_auth_service()))],
    rate_info: Annotated[RateLimitInfo, Depends(check_rate_limit)]
) -> MCPResponse:
    """Generic MCP tool invocation endpoint."""
    # Route to appropriate handler based on tool name
    if request.tool == "llm.fetch_manifest":
        result = await fetch_manifest(
            request.parameters.get("host"),
            token_data,
            rate_info,
            get_storage()
        )
        return MCPResponse(
            request_id=request.request_id,
            result={"redirect_url": result.headers.get("location")}
        )
    elif request.tool == "llm.fetch_page":
        result = await fetch_page(
            request.parameters.get("url"),
            token_data,
            rate_info,
            get_storage()
        )
        return MCPResponse(
            request_id=request.request_id,
            result=result.dict()
        )
    else:
        return MCPResponse(
            request_id=request.request_id,
            result=None,
            error=f"Unknown tool: {request.tool}"
        )
