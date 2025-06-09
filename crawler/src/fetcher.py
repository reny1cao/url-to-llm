"""Web page fetcher using Playwright with stealth and anti-blocking measures."""

import asyncio
import random
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from playwright.async_api import async_playwright, Page, Response
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

logger = structlog.get_logger()


class StealthConfig:
    """Configuration for stealth browser settings."""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    VIEWPORT_SIZES = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
    ]


class PageFetcher:
    """Fetches web pages using Playwright with anti-detection measures."""
    
    def __init__(
        self,
        proxy_url: Optional[str] = None,
        capsolver_key: Optional[str] = None,
        headless: bool = True,
    ):
        self.proxy_url = proxy_url
        self.capsolver_key = capsolver_key
        self.headless = headless
        self._playwright = None
        self._browser = None
        
    async def initialize(self):
        """Initialize Playwright and browser."""
        self._playwright = await async_playwright().start()
        
        launch_args = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ]
        }
        
        if self.proxy_url:
            launch_args["proxy"] = {"server": self.proxy_url}
            
        self._browser = await self._playwright.chromium.launch(**launch_args)
        
    async def close(self):
        """Close browser and Playwright."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
            
    async def create_stealth_context(self):
        """Create a new browser context with stealth settings."""
        user_agent = random.choice(StealthConfig.USER_AGENTS)
        viewport = random.choice(StealthConfig.VIEWPORT_SIZES)
        
        context = await self._browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
            locale="en-US",
            timezone_id="America/New_York",
            permissions=["geolocation"],
            geolocation={"latitude": 40.7128, "longitude": -74.0060},
        )
        
        # Add stealth scripts
        await context.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override chrome detection
            window.chrome = {
                runtime: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)
        
        return context
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch(self, url: str) -> Tuple[int, Dict[str, str], str, Optional[str]]:
        """
        Fetch a page with retry logic.
        
        Returns:
            Tuple of (status_code, headers, content, error_message)
        """
        context = await self.create_stealth_context()
        page = await context.new_page()
        
        try:
            # Set up response interception
            response_data = {"status": 0, "headers": {}, "content": "", "error": None}
            
            async def handle_response(response: Response):
                if response.url == url or response.url.rstrip('/') == url.rstrip('/'):
                    response_data["status"] = response.status
                    response_data["headers"] = await response.all_headers()
                    
            page.on("response", handle_response)
            
            # Navigate with timeout
            try:
                response = await page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=30000
                )
                
                # Wait for dynamic content
                await page.wait_for_timeout(random.randint(1000, 3000))
                
                # Check for CAPTCHA
                if await self._detect_captcha(page):
                    logger.warning("CAPTCHA detected", url=url)
                    if self.capsolver_key:
                        await self._solve_captcha(page)
                    else:
                        response_data["error"] = "CAPTCHA detected"
                        response_data["status"] = 403
                        
                # Get page content
                content = await page.content()
                response_data["content"] = content
                
                # Handle specific error pages
                if response_data["status"] in [403, 503]:
                    if self.proxy_url:
                        # Retry with different proxy
                        raise Exception("Blocked, retrying with different proxy")
                        
            except Exception as e:
                logger.error("Page fetch error", url=url, error=str(e))
                response_data["error"] = str(e)
                if response_data["status"] == 0:
                    response_data["status"] = 500
                    
            return (
                response_data["status"],
                response_data["headers"],
                response_data["content"],
                response_data["error"]
            )
            
        finally:
            await page.close()
            await context.close()
            
    async def _detect_captcha(self, page: Page) -> bool:
        """Detect common CAPTCHA patterns."""
        captcha_selectors = [
            'iframe[src*="recaptcha"]',
            'iframe[src*="captcha"]',
            'div[class*="captcha"]',
            '#captcha',
            '.g-recaptcha',
            'div[id*="captcha"]',
        ]
        
        for selector in captcha_selectors:
            if await page.query_selector(selector):
                return True
                
        # Check page content for CAPTCHA keywords
        content = await page.content()
        captcha_keywords = ['captcha', 'recaptcha', 'challenge', 'verify you are human']
        content_lower = content.lower()
        
        return any(keyword in content_lower for keyword in captcha_keywords)
        
    async def _solve_captcha(self, page: Page):
        """Solve CAPTCHA using CapSolver API."""
        # This is a placeholder - actual implementation would use CapSolver API
        logger.info("CAPTCHA solving not implemented yet")
        await page.wait_for_timeout(5000)
        
    async def fetch_robots_txt(self, host: str) -> Optional[str]:
        """Fetch robots.txt for a host."""
        robots_url = f"https://{host}/robots.txt"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(robots_url, timeout=10)
                if response.status_code == 200:
                    return response.text
        except Exception as e:
            logger.warning("Failed to fetch robots.txt", host=host, error=str(e))
            
        return None
        
    async def fetch_sitemap(self, host: str) -> Optional[str]:
        """Fetch sitemap.xml for a host."""
        sitemap_urls = [
            f"https://{host}/sitemap.xml",
            f"https://{host}/sitemap_index.xml",
            f"https://{host}/sitemap-index.xml",
        ]
        
        async with httpx.AsyncClient() as client:
            for url in sitemap_urls:
                try:
                    response = await client.get(url, timeout=10)
                    if response.status_code == 200:
                        return response.text
                except Exception:
                    continue
                    
        return None