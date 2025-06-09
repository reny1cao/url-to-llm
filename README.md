# URL → llm.txt Pipeline

End-to-end system that crawls any given domain, builds/updates an `llm.txt` manifest, hosts it statically, and exposes both manifests & raw pages to agents via Model Context Protocol (MCP).

## Quick Start

```bash
# Start the full stack locally
docker-compose up -d

# Run tests
make test

# Deploy to production
make deploy
```

## Architecture

- **Crawler**: Playwright-powered incremental crawler with politeness controls
- **Backend**: FastAPI + MCP server with OAuth 2.1 PKCE authentication
- **Frontend**: Next.js 15 dashboard with real-time crawl monitoring
- **Storage**: PostgreSQL for metadata, S3/MinIO for content

## Development

See individual module READMEs:
- [Crawler Documentation](./crawler/README.md)
- [Backend Documentation](./backend/README.md)
- [Frontend Documentation](./frontend/README.md)

## License

MIT