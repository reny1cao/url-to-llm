# 🚀 Deploying URL-to-LLM on Google Cloud Run

This guide walks you through deploying URL-to-LLM on Google Cloud Run, a fully managed serverless platform.

## 📋 Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed ([Install Guide](https://cloud.google.com/sdk/docs/install))
- Docker installed locally
- GitHub account (for CI/CD)

## 🏗️ Architecture on Cloud Run

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   Frontend  │────▶│   Backend   │────▶│  Cloud SQL   │
│ (Cloud Run) │     │ (Cloud Run) │     │ (PostgreSQL) │
└─────────────┘     └─────────────┘     └──────────────┘
                            │                     
                            ├──────▶ Memorystore (Redis)
                            │                     
                            └──────▶ Cloud Storage (GCS)
```

## 🚦 Quick Start (15 minutes)

### 1. Set up Google Cloud Project

```bash
# Clone the repository
git clone https://github.com/yourusername/url-to-llm.git
cd url-to-llm

# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Run the setup script
./scripts/setup-gcp.sh
```

This script will:
- Enable required APIs
- Create Cloud SQL instance
- Set up Memorystore Redis
- Create Cloud Storage bucket
- Configure Secret Manager
- Set up service accounts

### 2. Deploy Manually (First Time)

```bash
# Authenticate with Google Cloud
gcloud auth login
gcloud config set project $PROJECT_ID

# Build and deploy using Cloud Build
gcloud builds submit --config=cloudbuild.yaml
```

### 3. Set up GitHub Actions (For CI/CD)

1. Create a service account key:
```bash
gcloud iam service-accounts keys create key.json \
  --iam-account=url-to-llm@${PROJECT_ID}.iam.gserviceaccount.com
```

2. Add GitHub secrets:
   - `GCP_PROJECT_ID`: Your project ID
   - `GCP_SA_KEY`: Contents of `key.json`
   - `DB_CONNECTION_NAME`: From `.env.gcp`
   - `DATABASE_SECRET`: "database-url"
   - `SECRET_KEY_SECRET`: "secret-key"
   - `REDIS_URL_SECRET`: "redis-url"
   - `GCS_BUCKET_SECRET`: "gcs-bucket"
   - `SERVICE_ACCOUNT`: From `.env.gcp`

3. Push to main branch to trigger deployment!

## 💰 Cost Estimation

| Service | Free Tier | Estimated Monthly Cost |
|---------|-----------|----------------------|
| Cloud Run | 2M requests/month | $0-10 |
| Cloud SQL | None | $10-15 (db-f1-micro) |
| Memorystore | None | $35 (1GB basic) |
| Cloud Storage | 5GB | $0.20 |
| **Total** | - | **~$45-60/month** |

### 💡 Cost Optimization Tips

1. **Development**: Use Cloud SQL proxy for local dev
2. **Staging**: Schedule instances to stop at night
3. **Production**: Use Cloud Run min instances = 0 for low traffic

## 🔧 Configuration

### Environment Variables

Cloud Run automatically injects:
- `PORT`: The port your app should listen on
- `K_SERVICE`: The service name (used to detect Cloud Run environment)

### Secrets

All sensitive data is stored in Secret Manager:
- `database-url`: PostgreSQL connection string
- `redis-url`: Redis connection string
- `secret-key`: JWT signing key
- `gcs-bucket`: Storage bucket name

### Custom Domain

1. Map your domain:
```bash
gcloud run domain-mappings create \
  --service=web-url-to-llm \
  --domain=yourdomain.com \
  --region=$REGION
```

2. Update DNS records as shown in the output

## 🛠️ Operations

### View Logs

```bash
# Backend logs
gcloud run services logs read api-url-to-llm --region=$REGION

# Frontend logs
gcloud run services logs read web-url-to-llm --region=$REGION
```

### Scale Settings

```bash
# Adjust backend scaling
gcloud run services update api-url-to-llm \
  --min-instances=0 \
  --max-instances=100 \
  --region=$REGION
```

### Database Operations

```bash
# Connect to database
gcloud sql connect url-to-llm-db --user=postgres

# Backup database
gcloud sql backups create --instance=url-to-llm-db
```

## 🚨 Troubleshooting

### Common Issues

1. **"Service Unavailable" error**
   - Check Cloud SQL instance is running
   - Verify VPC connector if using private IP

2. **"Permission denied" errors**
   - Ensure service account has correct roles
   - Check Secret Manager permissions

3. **High latency**
   - Enable Cloud Run CPU boost
   - Increase min instances for warm starts

### Debug Commands

```bash
# Check service status
gcloud run services describe api-url-to-llm --region=$REGION

# Test connectivity
gcloud run services proxy api-url-to-llm --region=$REGION
# Then visit http://localhost:8080/api/health
```

## 🔒 Security Best Practices

1. **Enable VPC connector** for private Cloud SQL access
2. **Use Secret Manager** for all sensitive data
3. **Enable Cloud Armor** for DDoS protection
4. **Set up Identity Platform** for user authentication
5. **Enable audit logs** for compliance

## 📊 Monitoring

1. Go to [Cloud Console](https://console.cloud.google.com)
2. Navigate to Cloud Run
3. View metrics:
   - Request count
   - Latency
   - Error rate
   - Instance count

Set up alerts for:
- Error rate > 1%
- Latency > 2s
- Cloud SQL CPU > 80%

## 🎯 Next Steps

1. **Set up staging environment**: Duplicate resources with `-staging` suffix
2. **Enable Cloud CDN**: For static assets
3. **Add Cloud Scheduler**: For periodic crawls
4. **Implement Cloud Tasks**: For better queue management

## 🆘 Support

- Check logs: `gcloud run services logs read`
- View metrics in Cloud Console
- Create an issue on GitHub

---

**Remember**: Cloud Run automatically scales to zero when not in use, so you only pay for what you use! 🎉