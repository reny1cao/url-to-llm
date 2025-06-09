"""CLI interface for the crawler."""

import asyncio
import click
import structlog
from dotenv import load_dotenv

from .crawler import Crawler, CrawlerSettings

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@click.group()
def cli():
    """URL to LLM Crawler CLI."""
    pass


@cli.command()
@click.argument('host')
@click.option('--max-pages', default=10000, help='Maximum pages to crawl')
@click.option('--rate-limit', default=4, help='Requests per minute')
def crawl(host: str, max_pages: int, rate_limit: int):
    """Crawl a single host."""
    async def run():
        # Load settings
        settings = CrawlerSettings()
        settings.max_pages_per_host = max_pages
        settings.crawl_rate_limit = rate_limit
        
        # Create and initialize crawler
        crawler = Crawler(settings)
        await crawler.initialize()
        
        try:
            # Run crawl
            result = await crawler.crawl_host(host)
            logger.info("Crawl completed", **result)
        finally:
            await crawler.close()
            
    asyncio.run(run())


@cli.command()
@click.argument('hosts', nargs=-1, required=True)
@click.option('--concurrent', default=3, help='Number of concurrent crawls')
def batch(hosts: tuple, concurrent: int):
    """Crawl multiple hosts."""
    async def run():
        settings = CrawlerSettings()
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrent)
        
        async def crawl_with_limit(host: str):
            async with semaphore:
                crawler = Crawler(settings)
                await crawler.initialize()
                try:
                    result = await crawler.crawl_host(host)
                    return result
                finally:
                    await crawler.close()
                    
        # Run all crawls
        tasks = [crawl_with_limit(host) for host in hosts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Report results
        for host, result in zip(hosts, results):
            if isinstance(result, Exception):
                logger.error("Crawl failed", host=host, error=str(result))
            else:
                logger.info("Crawl completed", host=host, **result)
                
    asyncio.run(run())


@cli.command()
@click.argument('host')
def regenerate(host: str):
    """Regenerate manifest for a host without crawling."""
    async def run():
        settings = CrawlerSettings()
        
        # Create storage and manifest generator
        from .storage import StorageAdapter
        from .manifest import LLMManifest
        
        storage = StorageAdapter(
            db_url=settings.database_url,
            s3_endpoint=settings.s3_endpoint,
            s3_access_key=settings.s3_access_key,
            s3_secret_key=settings.s3_secret_key,
            s3_bucket=settings.s3_bucket,
        )
        await storage.initialize()
        
        try:
            manifest_gen = LLMManifest(storage)
            manifest = await manifest_gen.generate_manifest(host)
            logger.info("Manifest regenerated", host=host)
            print(manifest)
        finally:
            await storage.close()
            
    asyncio.run(run())


if __name__ == '__main__':
    cli()