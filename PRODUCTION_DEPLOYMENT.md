# Production Deployment Guide

This guide covers deploying the URL-to-LLM system to production.

## Prerequisites

- Docker and Docker Compose installed
- Domain name configured
- SSL certificates (Let's Encrypt recommended)
- At least 4GB RAM and 2 CPU cores
- PostgreSQL backup strategy
- S3-compatible storage (AWS S3, MinIO, etc.)

## Quick Start

1. **Clone and configure**:
```bash
git clone https://github.com/yourusername/url-to-llm.git
cd url-to-llm
cp .env.example .env
# Edit .env with production values
```

2. **Build and start services**:
```bash
make prod-build
make prod-up
make migrate
```

3. **Verify deployment**:
```bash
# Check service health
curl http://your-domain/health

# Monitor workers
docker-compose logs -f celery-worker

# Access Flower (if enabled)
open http://your-domain:5555
```

## Environment Configuration

### Required Variables

```bash
# Database (use managed PostgreSQL in production)
DATABASE_URL=postgresql://user:pass@host:5432/url_to_llm

# Redis (use managed Redis in production)
REDIS_URL=redis://redis-host:6379

# S3 Storage
S3_ENDPOINT=https://s3.amazonaws.com
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_BUCKET=your-llm-manifests
CDN_URL=https://cdn.yourdomain.com

# Security (generate strong keys!)
SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256

# Domain Configuration
ALLOWED_ORIGINS=["https://yourdomain.com"]

# Production Settings
ENVIRONMENT=production
DEBUG=false
```

### Optional Services

```bash
# Proxy Pool (for distributed crawling)
PROXY_POOL_URL=http://proxy-service:8888

# CAPTCHA Solving
CAPSOLVER_API_KEY=your-api-key

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/xxx
```

## Architecture

### Services Overview

1. **Backend API** (FastAPI)
   - Handles HTTP/WebSocket requests
   - Manages authentication and jobs
   - Serves MCP endpoints

2. **Celery Workers**
   - Execute crawl tasks
   - Scale horizontally based on load
   - Automatic retry on failures

3. **Frontend** (Next.js)
   - Server-side rendered UI
   - Real-time WebSocket updates
   - Responsive design

4. **Nginx** (Reverse Proxy)
   - SSL termination
   - Rate limiting
   - Load balancing

## Scaling Strategy

### Horizontal Scaling

```bash
# Scale workers based on queue size
make worker-scale N=8

# Or use Docker Compose directly
docker-compose up -d --scale celery-worker=8
```

### Database Optimization

```sql
-- Add indexes for performance
CREATE INDEX idx_jobs_created_by_status ON jobs(created_by, status);
CREATE INDEX idx_pages_host_crawled_at ON pages(host, crawled_at DESC);

-- Partition tables by date (optional)
CREATE TABLE pages_2024_01 PARTITION OF pages
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### Redis Configuration

```redis
# Persistence
save 900 1
save 300 10
save 60 10000

# Memory optimization
maxmemory 2gb
maxmemory-policy allkeys-lru
```

## Monitoring

### Health Checks

```yaml
# docker-compose.prod.yml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Metrics Collection

1. **Prometheus** (metrics):
```yaml
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"
```

2. **Grafana** (visualization):
```yaml
grafana:
  image: grafana/grafana
  ports:
    - "3001:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

### Application Logs

```bash
# Aggregate logs with Loki
docker-compose logs -f | docker run -i grafana/promtail -config.file=/etc/promtail/config.yml

# Or use CloudWatch/Datadog/etc
```

## Security Best Practices

1. **SSL/TLS Configuration**:
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
```

2. **Rate Limiting**:
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20 nodelay;
```

3. **Security Headers**:
```nginx
add_header Strict-Transport-Security "max-age=31536000" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Content-Security-Policy "default-src 'self'" always;
```

4. **Database Security**:
- Use connection pooling
- Enable SSL for database connections
- Implement row-level security
- Regular backups

## Backup Strategy

### Database Backups

```bash
# Daily backups
0 2 * * * pg_dump $DATABASE_URL | gzip > /backups/db-$(date +\%Y\%m\%d).sql.gz

# Keep 30 days of backups
find /backups -name "db-*.sql.gz" -mtime +30 -delete
```

### S3 Sync

```bash
# Sync manifests to backup bucket
aws s3 sync s3://llm-manifests s3://llm-manifests-backup --delete
```

## Disaster Recovery

1. **Database Recovery**:
```bash
gunzip < /backups/db-20240101.sql.gz | psql $DATABASE_URL
```

2. **Redis Recovery**:
```bash
redis-cli --rdb /backups/dump.rdb
```

3. **Application Recovery**:
```bash
# Roll back to previous version
docker-compose down
git checkout v1.2.3
make prod-build
make prod-up
```

## Performance Tuning

### PostgreSQL

```sql
-- Adjust based on available RAM
ALTER SYSTEM SET shared_buffers = '1GB';
ALTER SYSTEM SET effective_cache_size = '3GB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
```

### Celery Workers

```python
# Optimize for your workload
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100
```

### Nginx

```nginx
worker_processes auto;
worker_connections 2048;
keepalive_timeout 65;
gzip on;
gzip_types text/plain application/json;
```

## Troubleshooting

### Common Issues

1. **Workers not processing tasks**:
```bash
# Check worker logs
docker-compose logs celery-worker

# Inspect queue
docker-compose exec redis redis-cli llen celery

# Restart workers
docker-compose restart celery-worker
```

2. **Database connection exhausted**:
```bash
# Check connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Kill idle connections
psql $DATABASE_URL -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '1 hour';"
```

3. **Memory issues**:
```bash
# Check memory usage
docker stats

# Limit container memory
docker-compose up -d --memory="2g" celery-worker
```

## Maintenance

### Regular Tasks

- **Weekly**: Check disk space, review logs
- **Monthly**: Update dependencies, security patches
- **Quarterly**: Performance review, capacity planning

### Update Procedure

```bash
# 1. Backup everything
make backup-all

# 2. Test in staging
git checkout develop
make test-all

# 3. Deploy with zero downtime
docker-compose build backend
docker-compose up -d --no-deps backend

# 4. Run migrations
make migrate

# 5. Deploy workers
docker-compose up -d --no-deps celery-worker

# 6. Deploy frontend
docker-compose up -d --no-deps frontend
```

## Support

- Documentation: https://github.com/yourusername/url-to-llm/wiki
- Issues: https://github.com/yourusername/url-to-llm/issues
- Email: support@yourdomain.com

Remember to customize all configurations for your specific needs!