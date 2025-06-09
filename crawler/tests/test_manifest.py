"""Test manifest generation."""

import pytest
from datetime import datetime

from src.manifest import ManifestGenerator


@pytest.mark.asyncio
async def test_generate_basic_manifest():
    """Test basic manifest generation."""
    generator = ManifestGenerator(None)  # Storage not needed for this test
    
    # Mock page data
    pages = [
        {
            "url": "https://example.com/",
            "title": "Example Site",
            "status_code": 200,
            "is_blocked": False,
        },
        {
            "url": "https://example.com/about",
            "title": "About Us",
            "status_code": 200,
            "is_blocked": False,
        },
        {
            "url": "https://example.com/blocked",
            "title": None,
            "status_code": 403,
            "is_blocked": True,
        },
    ]
    
    # Generate manifest
    manifest = await generator._format_manifest(
        host="example.com",
        pages=pages,
        total_pages=3,
        accessible_pages=2,
        blocked_pages=1,
        avg_response_time=150.5,
        license_info=None,
        site_description="Example website",
    )
    
    # Verify manifest content
    assert "# example.com llm.txt" in manifest
    assert "Version: 1.0.0" in manifest
    assert "Example website" in manifest
    assert "Total pages: 3" in manifest
    assert "Accessible pages: 2" in manifest
    assert "Blocked pages: 1" in manifest
    assert "Average response time: 150.50ms" in manifest


@pytest.mark.asyncio
async def test_manifest_with_license():
    """Test manifest generation with license detection."""
    generator = ManifestGenerator(None)
    
    manifest = await generator._format_manifest(
        host="example.com",
        pages=[],
        total_pages=10,
        accessible_pages=10,
        blocked_pages=0,
        avg_response_time=100,
        license_info="MIT License",
        site_description="Open source project",
    )
    
    assert "## License" in manifest
    assert "MIT License" in manifest