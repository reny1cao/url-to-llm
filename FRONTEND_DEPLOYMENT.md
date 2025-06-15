# 🚀 Frontend Deployment Guide

## Backend API URL
✅ **Live Backend**: https://url-to-llm-857813849242.asia-southeast1.run.app

## Option 1: Deploy to Vercel (Recommended - Free)

1. **Install Vercel CLI** (if not installed):
```bash
pnpm install -g vercel
```

2. **Deploy from frontend directory**:
```bash
cd frontend
vercel
```

3. **During setup, set environment variable**:
```
NEXT_PUBLIC_API_URL=https://url-to-llm-857813849242.asia-southeast1.run.app
```

4. **For production deployment**:
```bash
vercel --prod
```

## Option 2: Deploy to Netlify (Free)

1. **Create netlify.toml**:
```toml
[build]
  command = "pnpm run build"
  publish = ".next"

[build.environment]
  NEXT_PUBLIC_API_URL = "https://url-to-llm-857813849242.asia-southeast1.run.app"
```

2. **Deploy**:
```bash
cd frontend
netlify deploy
netlify deploy --prod
```

## Option 3: Deploy to Google Cloud Run (Same as backend)

1. **Use existing Dockerfile.cloudrun**:
```bash
cd frontend
gcloud run deploy url-to-llm-frontend \
  --source . \
  --dockerfile Dockerfile.cloudrun \
  --platform managed \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars="NEXT_PUBLIC_API_URL=https://url-to-llm-857813849242.asia-southeast1.run.app"
```

## Option 4: Static Export (GitHub Pages/Any Static Host)

1. **Update next.config.js for static export**:
```javascript
module.exports = {
  output: 'export',
  // ... other config
}
```

2. **Build and export**:
```bash
cd frontend
NEXT_PUBLIC_API_URL=https://url-to-llm-857813849242.asia-southeast1.run.app pnpm run build
```

3. **Deploy the `out` directory to any static host**

## Quick Vercel Deploy (Simplest)

```bash
# From project root
cd frontend

# Create .env.production.local
echo "NEXT_PUBLIC_API_URL=https://url-to-llm-857813849242.asia-southeast1.run.app" > .env.production.local

# Deploy to Vercel
pnpm install -g vercel  # if not installed
vercel

# Follow prompts:
# - Set up and deploy: Y
# - Which scope: (your account)
# - Link to existing project: N
# - Project name: url-to-llm
# - Directory: ./
# - Override settings: N

# For production:
vercel --prod
```

## CORS Configuration

The backend is already configured to accept requests from localhost:3000. After deployment, you may need to update the backend's CORS settings to include your frontend URL.

Update in Cloud Run environment variables:
```
ALLOWED_ORIGINS=https://your-frontend-url.vercel.app,http://localhost:3000
```

## Test Frontend Locally First

```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=https://url-to-llm-857813849242.asia-southeast1.run.app" > .env.local
pnpm install
pnpm run dev
# Open http://localhost:3000
```

This will verify the frontend can connect to the backend before deploying.