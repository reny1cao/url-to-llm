# URL to LLM Backend

FastAPI backend with Model Context Protocol (MCP) server for URL to LLM.

## Features

- OAuth 2.1 PKCE authentication
- MCP tool endpoints for AI agents
- Rate limiting and monitoring
- Async PostgreSQL and Redis integration

## Development

```bash
poetry install
poetry run uvicorn app.main:app --reload
```

## Testing

```bash
poetry run pytest
```