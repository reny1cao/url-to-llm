# 🚀 Cloud Run Setup Instructions

Your Cloud Run service is deployed but needs configuration to work properly.

## Service URL
- **Live URL**: https://url-to-llm-ip37os3n7a-as.a.run.app
- **Region**: asia-southeast1
- **Project**: gen-lang-client-0975810124

## Required Setup Steps

### 1. Set Environment Variables in Cloud Run Console

Go to: https://console.cloud.google.com/run/detail/asia-southeast1/url-to-llm/revisions?project=gen-lang-client-0975810124

Click "Edit & Deploy New Revision" and add these environment variables:

```
DATABASE_URL=postgresql://postgres:password@/url-to-llm?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME
REDIS_URL=redis://10.x.x.x:6379
SECRET_KEY=your-secret-key-here
GCS_BUCKET=url-to-llm-storage
STORAGE_BACKEND=gcs
```

### 2. Create Cloud SQL Instance (if not exists)

```bash
# Set your project
gcloud config set project gen-lang-client-0975810124

# Create Cloud SQL instance
gcloud sql instances create url-to-llm-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=asia-southeast1

# Create database
gcloud sql databases create url-to-llm \
  --instance=url-to-llm-db

# Create user
gcloud sql users create appuser \
  --instance=url-to-llm-db \
  --password=secure-password-here
```

### 3. Connect Cloud SQL to Cloud Run

In Cloud Run console, under "Connections" tab, add Cloud SQL connection:
- Instance: `gen-lang-client-0975810124:asia-southeast1:url-to-llm-db`

### 4. Create Redis Instance (Memorystore)

```bash
gcloud redis instances create url-to-llm-redis \
  --size=1 \
  --region=asia-southeast1 \
  --redis-version=redis_6_x
```

### 5. Create GCS Bucket

```bash
gcloud storage buckets create gs://url-to-llm-storage-gen-lang \
  --location=asia-southeast1 \
  --uniform-bucket-level-access
```

### 6. Update Service Account Permissions

```bash
# Get the Cloud Run service account
SERVICE_ACCOUNT=$(gcloud run services describe url-to-llm \
  --region=asia-southeast1 \
  --format='value(spec.template.spec.serviceAccountName)')

# Grant necessary permissions
gcloud projects add-iam-policy-binding gen-lang-client-0975810124 \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding gen-lang-client-0975810124 \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/storage.objectAdmin"
```

### 7. Quick Setup with Secrets Manager (Recommended)

```bash
# Create secrets
echo -n "postgresql://appuser:secure-password-here@/url-to-llm?host=/cloudsql/gen-lang-client-0975810124:asia-southeast1:url-to-llm-db" | \
  gcloud secrets create database-url --data-file=-

echo -n "redis://REDIS_IP:6379" | \
  gcloud secrets create redis-url --data-file=-

echo -n "your-secret-key-$(openssl rand -hex 32)" | \
  gcloud secrets create jwt-secret --data-file=-

echo -n "url-to-llm-storage-gen-lang" | \
  gcloud secrets create gcs-bucket --data-file=-

# Update Cloud Run with secrets
gcloud run services update url-to-llm \
  --region=asia-southeast1 \
  --update-secrets=DATABASE_URL=database-url:latest,REDIS_URL=redis-url:latest,SECRET_KEY=jwt-secret:latest,GCS_BUCKET=gcs-bucket:latest
```

### 8. Run Database Migrations

Once database is connected:

```bash
# SSH into Cloud Shell or use local gcloud
gcloud run jobs create migrate-db \
  --image=gcr.io/gen-lang-client-0975810124/url-to-llm \
  --region=asia-southeast1 \
  --set-env-vars="DATABASE_URL=SECRET:database-url" \
  --set-cloudsql-instances=gen-lang-client-0975810124:asia-southeast1:url-to-llm-db \
  --command="alembic,upgrade,head"

# Execute the job
gcloud run jobs execute migrate-db --region=asia-southeast1
```

## Testing After Setup

```bash
# Test health endpoint
curl https://url-to-llm-ip37os3n7a-as.a.run.app/health

# Expected response:
# {"status":"ok","services":{"database":"connected","redis":"connected","storage":"connected"}}
```

## Frontend Deployment

For the frontend, deploy to Vercel:

```bash
cd frontend
vercel --prod
```

Update the environment variable in Vercel:
```
NEXT_PUBLIC_API_URL=https://url-to-llm-ip37os3n7a-as.a.run.app
```

## Monitoring

View logs:
```bash
gcloud run services logs read url-to-llm --region=asia-southeast1
```

## Custom Domain (Optional)

```bash
gcloud beta run domain-mappings create \
  --service=url-to-llm \
  --domain=api.yourdomain.com \
  --region=asia-southeast1
```