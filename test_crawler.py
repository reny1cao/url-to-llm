#!/usr/bin/env python3
"""Test script to verify crawler functionality."""

import asyncio
import os
import sys

# Add crawler module to path
sys.path.append(os.path.join(os.path.dirname(__file__), "crawler"))

from crawler.src.crawler import Crawler, CrawlerSettings
from crawler.src.storage import StorageAdapter
from crawler.src.manifest import LLMManifest


async def test_minimal_crawl():
    """Test minimal crawl functionality."""
    # Create test settings
    settings = CrawlerSettings(
        database_url="postgresql://postgres:postgres@localhost:5432/urlllm",
        s3_endpoint="http://localhost:9000",
        s3_access_key="minioadmin",
        s3_secret_key="minioadmin",
        s3_bucket="urlllm",
        max_pages_per_host=5,  # Small number for testing
        crawl_rate_limit=10,  # Faster for testing
    )
    
    # Test with a simple website
    test_host = "example.com"
    
    print(f"Testing crawler with {test_host}...")
    
    # Create and initialize crawler
    crawler = Crawler(settings)
    
    try:
        await crawler.initialize()
        print("✓ Crawler initialized")
        
        # Run crawl
        result = await crawler.crawl_host(test_host)
        print(f"✓ Crawl completed: {result}")
        
        # Get generated manifest
        manifest_content = await crawler.storage.get_from_s3(f"llm/{test_host}/llm.txt")
        
        if manifest_content:
            print("\n--- Generated Manifest ---")
            print(manifest_content.decode('utf-8'))
            print("--- End Manifest ---\n")
            print("✓ Manifest generated successfully!")
        else:
            print("✗ Failed to retrieve manifest")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await crawler.close()
        print("✓ Cleanup completed")


if __name__ == "__main__":
    asyncio.run(test_minimal_crawl())