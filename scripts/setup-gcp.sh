#!/bin/bash

# Google Cloud Platform Setup Script for URL-to-LLM
# This script sets up all required GCP resources

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-""}
REGION=${REGION:-"us-central1"}
SERVICE_NAME=${SERVICE_NAME:-"url-to-llm"}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}URL-to-LLM Google Cloud Setup${NC}"
echo "=============================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${YELLOW}Please log in to Google Cloud${NC}"
    gcloud auth login
fi

# Get or set project ID
if [ -z "$PROJECT_ID" ]; then
    echo "Enter your Google Cloud Project ID:"
    read PROJECT_ID
fi

echo -e "\n${YELLOW}Setting up project: $PROJECT_ID${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "\n${YELLOW}Enabling required APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    redis.googleapis.com \
    storage.googleapis.com \
    compute.googleapis.com

# Create service account
echo -e "\n${YELLOW}Creating service account...${NC}"
SERVICE_ACCOUNT="${SERVICE_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create $SERVICE_NAME \
    --display-name="URL-to-LLM Service Account" \
    --description="Service account for URL-to-LLM Cloud Run services" \
    || echo "Service account already exists"

# Grant necessary permissions
echo -e "\n${YELLOW}Granting permissions...${NC}"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

# Create Cloud SQL instance
echo -e "\n${YELLOW}Creating Cloud SQL instance...${NC}"
DB_INSTANCE="${SERVICE_NAME}-db"

gcloud sql instances create $DB_INSTANCE \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --network=default \
    --no-assign-ip \
    || echo "Cloud SQL instance already exists"

# Create database
echo -e "\n${YELLOW}Creating database...${NC}"
gcloud sql databases create url_to_llm \
    --instance=$DB_INSTANCE \
    || echo "Database already exists"

# Generate secure password
DB_PASSWORD=$(openssl rand -base64 32)

# Set postgres user password
echo -e "\n${YELLOW}Setting database password...${NC}"
gcloud sql users set-password postgres \
    --instance=$DB_INSTANCE \
    --password="$DB_PASSWORD"

# Create Redis instance (Memorystore)
echo -e "\n${YELLOW}Creating Redis instance...${NC}"
REDIS_INSTANCE="${SERVICE_NAME}-redis"

gcloud redis instances create $REDIS_INSTANCE \
    --size=1 \
    --region=$REGION \
    --redis-version=redis_6_x \
    --tier=basic \
    || echo "Redis instance already exists"

# Get Redis host
REDIS_HOST=$(gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format="value(host)")
REDIS_PORT=$(gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format="value(port)")

# Create GCS bucket
echo -e "\n${YELLOW}Creating Cloud Storage bucket...${NC}"
BUCKET_NAME="${PROJECT_ID}-${SERVICE_NAME}-storage"

gsutil mb -p $PROJECT_ID -c standard -l $REGION gs://${BUCKET_NAME}/ \
    || echo "Bucket already exists"

# Create secrets in Secret Manager
echo -e "\n${YELLOW}Creating secrets...${NC}"

# Database URL
DB_CONNECTION_NAME="${PROJECT_ID}:${REGION}:${DB_INSTANCE}"
DATABASE_URL="postgresql://postgres:${DB_PASSWORD}@/${SERVICE_NAME}?host=/cloudsql/${DB_CONNECTION_NAME}"

echo -n "$DATABASE_URL" | gcloud secrets create database-url --data-file=- \
    || echo -n "$DATABASE_URL" | gcloud secrets versions add database-url --data-file=-

# Redis URL
REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}/0"
echo -n "$REDIS_URL" | gcloud secrets create redis-url --data-file=- \
    || echo -n "$REDIS_URL" | gcloud secrets versions add redis-url --data-file=-

# Secret key
SECRET_KEY=$(openssl rand -hex 32)
echo -n "$SECRET_KEY" | gcloud secrets create secret-key --data-file=- \
    || echo "Secret key already exists"

# GCS bucket
echo -n "$BUCKET_NAME" | gcloud secrets create gcs-bucket --data-file=- \
    || echo -n "$BUCKET_NAME" | gcloud secrets versions add gcs-bucket --data-file=-

# Create Cloud Build trigger
echo -e "\n${YELLOW}Creating Cloud Build trigger...${NC}"
gcloud builds triggers create github \
    --repo-name=url-to-llm \
    --repo-owner=YOUR_GITHUB_USERNAME \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml \
    --substitutions="_SERVICE_NAME=${SERVICE_NAME},_REGION=${REGION}" \
    || echo "Build trigger already exists"

# Create .env.gcp file
echo -e "\n${YELLOW}Creating .env.gcp file...${NC}"
cat > .env.gcp << EOF
# Google Cloud Configuration
PROJECT_ID=${PROJECT_ID}
REGION=${REGION}
SERVICE_NAME=${SERVICE_NAME}
SERVICE_ACCOUNT=${SERVICE_ACCOUNT}

# Database
DB_INSTANCE=${DB_INSTANCE}
DB_CONNECTION_NAME=${DB_CONNECTION_NAME}

# Redis
REDIS_INSTANCE=${REDIS_INSTANCE}
REDIS_HOST=${REDIS_HOST}
REDIS_PORT=${REDIS_PORT}

# Storage
GCS_BUCKET=${BUCKET_NAME}

# URLs (after deployment)
API_URL=https://api-${SERVICE_NAME}-${REGION}-${PROJECT_ID}.a.run.app
WEB_URL=https://web-${SERVICE_NAME}-${REGION}-${PROJECT_ID}.a.run.app
EOF

echo -e "\n${GREEN}Setup completed successfully!${NC}"
echo "=============================="
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Update YOUR_GITHUB_USERNAME in the build trigger"
echo "2. Connect your GitHub repository to Cloud Build"
echo "3. Run the initial deployment:"
echo "   gcloud builds submit --config=cloudbuild.yaml"
echo "4. Map custom domains (optional)"
echo ""
echo -e "${GREEN}Your configuration has been saved to .env.gcp${NC}"