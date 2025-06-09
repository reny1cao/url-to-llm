# URL to LLM Crawler

Playwright-powered incremental web crawler with politeness controls.

## Features

- Stealth browser automation
- BFS crawling with frontier management
- Change detection (ETag/SHA-256)
- Robots.txt compliance
- Rate limiting (4 requests/minute)

## Development

```bash
poetry install
poetry run playwright install chromium
poetry run python -m src.cli --help
```

## Testing

```bash
poetry run pytest
```