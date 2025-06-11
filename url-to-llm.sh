#!/bin/bash

# URL-to-LLM Master Management Script
# Consolidates all management functionality into a single script

set -e

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_step() { echo -e "${CYAN}▶️  $1${NC}"; }

# Function to show header
show_header() {
    echo -e "${MAGENTA}"
    echo "╔═══════════════════════════════════════╗"
    echo "║       URL-to-LLM Management Tool      ║"
    echo "╚═══════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check prerequisites
check_prerequisites() {
    local missing=0
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install Docker first."
        missing=1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose not found. Please install Docker Compose first."
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        exit 1
    fi
}

# Check if services are running
check_services() {
    local running=$(docker ps --format "{{.Names}}" | grep -c "url-to-llm" || echo "0")
    if [ "$running" -gt 0 ]; then
        return 0
    else
        return 1
    fi
}

# Initialize environment
init_env() {
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            print_info "Creating .env file from example..."
            cp .env.example .env
            print_warning "Please edit .env with your configuration and run again."
            exit 1
        else
            print_error "No .env or .env.example file found!"
            exit 1
        fi
    fi
    source .env
}

# Start services
start_services() {
    if check_services; then
        print_warning "Services are already running. Use 'restart' to restart them."
        show_status
        return
    fi
    
    print_step "Building Docker images..."
    docker-compose build
    
    print_step "Starting core services (Database, Redis, MinIO)..."
    docker-compose up -d db redis minio
    
    print_step "Waiting for core services to be healthy..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose ps | grep -E "(db|redis|minio)" | grep -q "healthy"; then
            print_success "Core services are healthy"
            break
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    echo
    
    print_step "Initializing MinIO bucket..."
    docker-compose run --rm minio sh -c "
        mc alias set local http://minio:9000 minioadmin minioadmin && \
        mc mb local/llm-manifests --ignore-existing && \
        mc anonymous set public local/llm-manifests
    " 2>/dev/null || true
    
    print_step "Starting backend and running migrations..."
    docker-compose up -d backend
    sleep 5
    docker-compose exec -T backend python run_migrations.py || true
    
    print_step "Starting all services..."
    docker-compose up -d
    
    if [ "${START_WORKERS:-true}" == "true" ]; then
        print_step "Starting Celery workers..."
        docker-compose up -d celery-worker celery-beat
    fi
    
    if [ "${ENABLE_MONITORING:-false}" == "true" ]; then
        print_step "Starting monitoring services..."
        docker-compose up -d flower
    fi
    
    sleep 3
    show_urls
}

# Stop services
stop_services() {
    print_step "Stopping all services..."
    docker-compose down
    print_success "All services stopped"
}

# Restart services
restart_services() {
    print_step "Restarting services..."
    docker-compose down
    sleep 2
    start_services
}

# Clean everything
clean_all() {
    print_warning "This will remove all containers, volumes, and images!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v --rmi all
        print_success "Cleanup complete"
    else
        print_info "Cleanup cancelled"
    fi
}

# Fix and rebuild (for issues)
fix_rebuild() {
    print_step "Fixing and rebuilding services..."
    docker-compose down
    print_step "Cleaning build cache..."
    docker-compose build --no-cache backend
    start_services
}

# Show logs
show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$service"
    fi
}

# Scale workers
scale_workers() {
    local count=$1
    if [ -z "$count" ]; then
        print_error "Please specify worker count"
        exit 1
    fi
    print_step "Scaling Celery workers to $count..."
    docker-compose up -d --scale celery-worker="$count"
    print_success "Workers scaled to $count"
}

# Show status
show_status() {
    echo "📊 Service Status:"
    docker-compose ps
}

# Show URLs
show_urls() {
    echo
    print_success "URL-to-LLM is running!"
    echo
    echo "🌐 Access URLs:"
    echo "  - Frontend: http://localhost:3000"
    echo "  - Backend API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    echo "  - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
    
    if [ "${ENABLE_MONITORING:-false}" == "true" ]; then
        echo "  - Flower: http://localhost:5555"
    fi
    
    echo
    echo "🕷️ Test the crawler at http://localhost:3000/test-crawler"
}

# Quick test
test_system() {
    print_step "Testing system health..."
    
    # Test backend
    if curl -s http://localhost:8000/health > /dev/null; then
        print_success "Backend is healthy"
    else
        print_error "Backend is not responding"
    fi
    
    # Test frontend
    if curl -s http://localhost:3000 > /dev/null; then
        print_success "Frontend is accessible"
    else
        print_error "Frontend is not responding"
    fi
    
    # Test database
    if docker-compose exec -T db pg_isready > /dev/null; then
        print_success "Database is ready"
    else
        print_error "Database is not ready"
    fi
    
    # Test Redis
    if docker-compose exec -T redis redis-cli ping > /dev/null; then
        print_success "Redis is ready"
    else
        print_error "Redis is not ready"
    fi
}

# Main menu
show_menu() {
    echo
    echo "Available commands:"
    echo "  start    - Start all services"
    echo "  stop     - Stop all services"
    echo "  restart  - Restart all services"
    echo "  status   - Show service status"
    echo "  logs     - Show logs (optional: service name)"
    echo "  test     - Test system health"
    echo "  scale    - Scale Celery workers"
    echo "  fix      - Fix and rebuild (for issues)"
    echo "  clean    - Remove all containers and data"
    echo "  help     - Show this help"
    echo
    echo "Examples:"
    echo "  $0 start              # Start everything"
    echo "  $0 logs backend       # Show backend logs"
    echo "  $0 scale 4            # Scale to 4 workers"
}

# Main command handling
main() {
    show_header
    check_prerequisites
    
    case "${1:-help}" in
        start)
            init_env
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            init_env
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$2"
            ;;
        test)
            test_system
            ;;
        scale)
            scale_workers "$2"
            ;;
        fix)
            init_env
            fix_rebuild
            ;;
        clean)
            clean_all
            ;;
        help|--help|-h)
            show_menu
            ;;
        *)
            print_error "Unknown command: $1"
            show_menu
            exit 1
            ;;
    esac
}

# Run main function
main "$@"