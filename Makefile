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

# Worker management
worker:
	docker-compose up -d celery-worker

worker-logs:
	docker-compose logs -f celery-worker

worker-restart:
	docker-compose restart celery-worker

worker-scale:
	@if [ -z "$(N)" ]; then \
		echo "Usage: N=4 make worker-scale"; \
		exit 1; \
	fi
	docker-compose up -d --scale celery-worker=$(N) celery-worker
	@echo "Scaled to $(N) workers"

# Monitoring
flower:
	docker-compose up -d flower
	@echo "Flower UI available at http://localhost:5555 (admin:admin)"

# Database
migrate:
	docker-compose exec backend python run_migrations.py

# Production
prod-build:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

prod-up:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Full stack management
stack-up: up worker flower migrate
	@echo "Full stack started!"
	@echo "  - Backend API: http://localhost:8000"
	@echo "  - Frontend: http://localhost:3000"
	@echo "  - MinIO: http://localhost:9001"
	@echo "  - Flower: http://localhost:5555"

stack-down:
	docker-compose down