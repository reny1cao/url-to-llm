"""Test health endpoints."""

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the health check endpoint."""
    response = await client.get("/health")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["status"] == "healthy"
    assert "checks" in data
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["redis"] == "ok"
    assert data["checks"]["s3"] == "ok"


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test the root endpoint."""
    response = await client.get("/")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["name"] == "URL to LLM API"
    assert data["version"] == "0.1.0"
    assert "mcp_enabled" in data
    assert data["docs"] == "/docs"