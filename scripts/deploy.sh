#!/bin/bash

# URL-to-LLM Deployment Script
# This script handles the deployment process for production

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOMAIN=${DOMAIN:-"yourdomain.com"}
ENVIRONMENT=${ENVIRONMENT:-"production"}
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"

echo -e "${GREEN}URL-to-LLM Deployment Script${NC}"
echo "=============================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

if ! command_exists docker; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command_exists docker-compose; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites met${NC}"

# Check environment file
if [ ! -f ".env.production" ]; then
    echo -e "${RED}Error: .env.production file not found${NC}"
    echo "Please copy .env.production.example and configure it"
    exit 1
fi

# Validate environment variables
echo -e "\n${YELLOW}Validating configuration...${NC}"

# Source the environment file to check values
set -a
source .env.production
set +a

# Check for placeholder values
if [[ "$SECRET_KEY" == *"CHANGE_ME"* ]]; then
    echo -e "${RED}Error: SECRET_KEY contains placeholder value${NC}"
    echo "Please generate a secure secret key"
    exit 1
fi

if [[ "$POSTGRES_PASSWORD" == *"CHANGE_ME"* ]]; then
    echo -e "${RED}Error: POSTGRES_PASSWORD contains placeholder value${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Configuration validated${NC}"

# Generate SSL certificates if they don't exist
if [ ! -f "nginx/ssl/cert.pem" ] || [ ! -f "nginx/ssl/key.pem" ]; then
    echo -e "\n${YELLOW}Generating self-signed SSL certificates...${NC}"
    mkdir -p nginx/ssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/key.pem \
        -out nginx/ssl/cert.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN"
    echo -e "${GREEN}✓ SSL certificates generated${NC}"
    echo -e "${YELLOW}Note: For production, replace with real certificates from Let's Encrypt${NC}"
fi

# Build images
echo -e "\n${YELLOW}Building Docker images...${NC}"
docker-compose -f $DOCKER_COMPOSE_FILE build

# Run database migrations
echo -e "\n${YELLOW}Running database migrations...${NC}"
docker-compose -f $DOCKER_COMPOSE_FILE run --rm backend alembic upgrade head

# Start services
echo -e "\n${YELLOW}Starting services...${NC}"
docker-compose -f $DOCKER_COMPOSE_FILE up -d

# Wait for services to be healthy
echo -e "\n${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Check health status
echo -e "\n${YELLOW}Checking service health...${NC}"
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/health || echo "000")

if [ "$HEALTH_CHECK" = "200" ]; then
    echo -e "${GREEN}✓ All services are healthy${NC}"
else
    echo -e "${RED}✗ Health check failed (HTTP $HEALTH_CHECK)${NC}"
    echo -e "${YELLOW}Checking logs...${NC}"
    docker-compose -f $DOCKER_COMPOSE_FILE logs --tail=50
    exit 1
fi

# Create initial admin user (optional)
echo -e "\n${YELLOW}Do you want to create an admin user? (y/n)${NC}"
read -r CREATE_ADMIN

if [ "$CREATE_ADMIN" = "y" ]; then
    echo "Enter admin email:"
    read -r ADMIN_EMAIL
    echo "Enter admin password:"
    read -rs ADMIN_PASSWORD
    
    # You would implement this in your backend
    # docker-compose -f $DOCKER_COMPOSE_FILE exec backend python -m app.scripts.create_admin "$ADMIN_EMAIL" "$ADMIN_PASSWORD"
    echo -e "${GREEN}✓ Admin user created${NC}"
fi

# Display summary
echo -e "\n${GREEN}Deployment completed successfully!${NC}"
echo "=============================="
echo -e "Frontend URL: https://$DOMAIN"
echo -e "API URL: https://$DOMAIN/api"
echo -e "API Docs: https://$DOMAIN/api/docs"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Update DNS records to point to this server"
echo "2. Configure real SSL certificates (Let's Encrypt recommended)"
echo "3. Set up monitoring and alerts"
echo "4. Configure backup strategy"
echo "5. Test the application thoroughly"

# Show running containers
echo -e "\n${YELLOW}Running containers:${NC}"
docker-compose -f $DOCKER_COMPOSE_FILE ps