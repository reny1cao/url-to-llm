# Deployment Guide

This guide covers deploying the URL → LLM Pipeline to production environments.

## Table of Contents

- [AWS Deployment](#aws-deployment)
- [Docker Swarm Deployment](#docker-swarm-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Configuration](#configuration)
- [Monitoring](#monitoring)

## AWS Deployment

### Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform installed (for infrastructure provisioning)
- Docker images pushed to a registry (ECR or GitHub Container Registry)

### Infrastructure Setup

1. Navigate to the Terraform directory:
   ```bash
   cd infra/terraform
   ```

2. Initialize Terraform:
   ```bash
   terraform init
   ```

3. Review the deployment plan:
   ```bash
   terraform plan
   ```

4. Apply the infrastructure:
   ```bash
   terraform apply
   ```

### Service Deployment

The GitHub Actions workflow automatically deploys to AWS ECS when:
- Code is pushed to `main` (staging deployment)
- A version tag is created (production deployment)

### Manual Deployment

```bash
# Update ECS service with new image
aws ecs update-service \
  --cluster url-to-llm-prod \
  --service backend \
  --force-new-deployment
```

## Docker Swarm Deployment

1. Initialize Swarm mode:
   ```bash
   docker swarm init
   ```

2. Deploy the stack:
   ```bash
   docker stack deploy -c docker-compose.prod.yml url-to-llm
   ```

3. Scale services:
   ```bash
   docker service scale url-to-llm_backend=3
   docker service scale url-to-llm_crawler=2
   ```

## Kubernetes Deployment

### Using Helm

1. Add the Helm repository:
   ```bash
   helm repo add url-to-llm https://charts.url-to-llm.example.com
   helm repo update
   ```

2. Install the chart:
   ```bash
   helm install url-to-llm url-to-llm/url-to-llm \
     --namespace url-to-llm \
     --create-namespace \
     --values values.prod.yaml
   ```

### Manual Kubernetes Deployment

1. Apply the manifests:
   ```bash
   kubectl apply -f infra/k8s/
   ```

2. Verify deployment:
   ```bash
   kubectl get pods -n url-to-llm
   kubectl get services -n url-to-llm
   ```

## Configuration

### Environment Variables

Production environment variables should be stored securely:

- **AWS**: Use AWS Systems Manager Parameter Store or Secrets Manager
- **Kubernetes**: Use Kubernetes Secrets or external secret management tools
- **Docker Swarm**: Use Docker Secrets

Example for Kubernetes:

```bash
kubectl create secret generic url-to-llm-secrets \
  --from-literal=DATABASE_URL='postgresql://...' \
  --from-literal=SECRET_KEY='...' \
  --namespace url-to-llm
```

### Database Migration

Run database migrations before deploying new versions:

```bash
# Using kubectl
kubectl run --rm -it migrate \
  --image=ghcr.io/your-org/url-to-llm-backend:latest \
  --restart=Never \
  -- python -m alembic upgrade head
```

### SSL/TLS Configuration

1. **AWS**: Use AWS Certificate Manager with Application Load Balancer
2. **Kubernetes**: Use cert-manager with Let's Encrypt
3. **Docker Swarm**: Use Traefik with automatic Let's Encrypt

## Monitoring

### Health Checks

All services expose health endpoints:
- Backend: `GET /health`
- Frontend: `GET /api/health`

### Metrics

Prometheus metrics are exposed at:
- Backend: `GET /metrics`

### Recommended Monitoring Stack

1. **Metrics**: Prometheus + Grafana
2. **Logs**: ELK Stack (Elasticsearch, Logstash, Kibana) or CloudWatch
3. **Tracing**: Jaeger or AWS X-Ray
4. **Uptime**: Pingdom or UptimeRobot

### Grafana Dashboard

Import the provided dashboard:
```bash
curl -X POST http://grafana.example.com/api/dashboards/import \
  -H "Content-Type: application/json" \
  -d @infra/monitoring/grafana-dashboard.json
```

## Backup and Recovery

### Database Backups

Automated daily backups:
```yaml
# Kubernetes CronJob example
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:16-alpine
            command:
            - /bin/sh
            - -c
            - |
              pg_dump $DATABASE_URL | gzip > /backup/db-$(date +%Y%m%d).sql.gz
              aws s3 cp /backup/db-$(date +%Y%m%d).sql.gz s3://backups/
```

### S3 Data Backup

Configure S3 cross-region replication for the manifest bucket.

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check security group rules
   - Verify connection string
   - Check database server status

2. **S3 Access Denied**
   - Verify IAM roles and policies
   - Check S3 bucket policies
   - Ensure correct region configuration

3. **High Memory Usage**
   - Scale crawler instances
   - Adjust Playwright browser settings
   - Implement request queuing

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
export STRUCTLOG_PROCESSORS=dev
```

## Security Considerations

1. **Network Security**
   - Use VPC with private subnets
   - Configure security groups with minimal access
   - Use VPN or bastion hosts for management

2. **Secrets Management**
   - Rotate secrets regularly
   - Use least privilege IAM roles
   - Enable audit logging

3. **Data Protection**
   - Enable encryption at rest
   - Use TLS for all communications
   - Implement data retention policies

## Performance Tuning

1. **Database**
   - Configure connection pooling
   - Add appropriate indexes
   - Use read replicas for scaling

2. **Caching**
   - Configure Redis with persistence
   - Implement cache warming
   - Set appropriate TTLs

3. **CDN**
   - Use CloudFront or similar CDN
   - Configure cache headers
   - Enable compression

## Rollback Procedures

### ECS Rollback
```bash
# Get previous task definition
aws ecs describe-task-definition \
  --task-definition url-to-llm-backend \
  --query 'taskDefinition.revision'

# Update service with previous version
aws ecs update-service \
  --cluster url-to-llm-prod \
  --service backend \
  --task-definition url-to-llm-backend:PREVIOUS_REVISION
```

### Kubernetes Rollback
```bash
# View rollout history
kubectl rollout history deployment/backend -n url-to-llm

# Rollback to previous version
kubectl rollout undo deployment/backend -n url-to-llm
```

## Support

For deployment support:
- Check the [troubleshooting guide](troubleshooting.md)
- Open an issue on GitHub
- Contact the DevOps team