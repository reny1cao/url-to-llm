.PHONY: help build up down logs test clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make build    - Build all Docker images"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make logs     - Show logs from all services"
	@echo "  make test     - Run all tests"
	@echo "  make clean    - Clean up volumes and images"
	@echo "  make crawl    - Run crawler for a host (HOST=example.com make crawl)"
	@echo "  make shell-*  - Open shell in service (e.g., make shell-backend)"

# Build all images
build:
	docker-compose build

# Start services
up:
	docker-compose up -d
	@echo "Services started!"
	@echo "Backend API: http://localhost:8000"
	@echo "MinIO Console: http://localhost:9001"
	@echo "Frontend: http://localhost:3000 (when implemented)"

# Stop services
down:
	docker-compose down

# Show logs
logs:
	docker-compose logs -f

# Run tests
test:
	docker-compose run --rm crawler pytest
	docker-compose run --rm backend pytest

# Clean everything
clean:
	docker-compose down -v
	docker image prune -f

# Crawl a specific host
crawl:
	@if [ -z "$(HOST)" ]; then \
		echo "Usage: HOST=example.com make crawl"; \
		exit 1; \
	fi
	docker-compose run --rm crawler python -m src.cli crawl $(HOST)

# Shell access
shell-crawler:
	docker-compose run --rm crawler /bin/bash

shell-backend:
	docker-compose run --rm backend /bin/bash

shell-db:
	docker-compose exec db psql -U postgres -d url_to_llm

# Development shortcuts
dev-backend:
	cd backend && uvicorn app.main:app --reload

dev-crawler:
	cd crawler && python -m src.cli --help

# Initialize development environment
init:
	cp .env.example .env
	@echo "Environment file created. Please edit .env with your settings."
	@echo "Run 'make build' to build images, then 'make up' to start services."