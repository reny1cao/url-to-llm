"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.dependencies import close_dependencies, init_dependencies
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_dependencies():
    """Initialize dependencies for tests."""
    await init_dependencies()
    yield
    await close_dependencies()


@pytest.fixture
async def client(setup_dependencies) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sync_client() -> TestClient:
    """Create a sync test client for simple tests."""
    return TestClient(app)
