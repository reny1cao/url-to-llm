# 🔧 Fixing Cloud Run GitHub Integration

## The Issue
Cloud Run's automatic build from GitHub is looking for a Dockerfile in the root directory, but our project has separate Dockerfiles for backend and frontend.

## Solution Options

### Option 1: Deploy Backend Only (Recommended for Quick Start)

1. **Use the root Dockerfile I created** - This builds just the backend
2. **Deploy frontend separately** using Vercel or Netlify
3. **Update frontend API URL** to point to Cloud Run backend

### Option 2: Manual Deployment with Cloud Build

Instead of using Cloud Run's GitHub integration, use Cloud Build:

```bash
# 1. Disconnect GitHub integration in Cloud Run console

# 2. Build and deploy manually
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_PROJECT_ID=$PROJECT_ID,_REGION=us-central1

# 3. Or build just the backend
gcloud builds submit --tag gcr.io/$PROJECT_ID/url-to-llm-backend backend/

# 4. Deploy to Cloud Run
gcloud run deploy url-to-llm \
  --image gcr.io/$PROJECT_ID/url-to-llm-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="STORAGE_BACKEND=gcs" \
  --port 8080
```

### Option 3: Fix for Automatic Builds

1. **Commit and push these files**:
   - `Dockerfile` (root) - ✅ Created
   - `Procfile` - ✅ Created  
   - `.gcloudignore` - ✅ Created
   - `app.json` - ✅ Created

2. **Configure in Cloud Run Console**:
   - Go to Cloud Run > Edit & Deploy New Revision
   - Environment Variables:
     ```
     DATABASE_URL=<from-secret-manager>
     REDIS_URL=<from-secret-manager>
     SECRET_KEY=<from-secret-manager>
     GCS_BUCKET=<your-bucket>
     STORAGE_BACKEND=gcs
     ```
   - Container port: 8080
   - Memory: 2GiB
   - CPU: 2

3. **Set up Cloud SQL connection**:
   - In Cloud Run settings, add Cloud SQL connection
   - Use your Cloud SQL instance name

## Quick Deploy Commands

```bash
# Set your project ID
export PROJECT_ID=your-project-id
export REGION=us-central1

# Option A: Deploy with existing Dockerfile
gcloud run deploy url-to-llm \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="STORAGE_BACKEND=gcs" \
  --port 8080

# Option B: Build and deploy backend only
cd backend
gcloud run deploy url-to-llm-backend \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="STORAGE_BACKEND=gcs" \
  --port 8080
```

## Environment Variables Needed

Create these in Secret Manager first:

```bash
# Create secrets
echo -n "postgresql://user:pass@/dbname?host=/cloudsql/INSTANCE" | \
  gcloud secrets create database-url --data-file=-

echo -n "redis://redis-host:6379" | \
  gcloud secrets create redis-url --data-file=-

echo -n "your-secret-key" | \
  gcloud secrets create jwt-secret --data-file=-

echo -n "your-bucket-name" | \
  gcloud secrets create gcs-bucket --data-file=-
```

Then reference in Cloud Run:
```bash
gcloud run deploy url-to-llm \
  --update-secrets=DATABASE_URL=database-url:latest,\
REDIS_URL=redis-url:latest,\
SECRET_KEY=jwt-secret:latest,\
GCS_BUCKET=gcs-bucket:latest
```

## Testing the Deployment

Once deployed, test with:

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe url-to-llm \
  --platform managed \
  --region $REGION \
  --format 'value(status.url)')

# Test health endpoint
curl $SERVICE_URL/health

# Should return: {"status":"ok","services":{...}}
```

## Next Steps

1. **Frontend Deployment**:
   - Deploy to Vercel: `vercel --prod`
   - Update `NEXT_PUBLIC_API_URL` to Cloud Run URL

2. **Custom Domain**:
   ```bash
   gcloud beta run domain-mappings create \
     --service url-to-llm \
     --domain api.yourdomain.com \
     --region $REGION
   ```

3. **Enable Cloud CDN** for better performance

The root Dockerfile I created will work with Cloud Run's automatic builds. Just push to GitHub and it should build successfully!