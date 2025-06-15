"""Configuration for Google Cloud services."""

import os
from typing import Optional
from google.cloud import storage, secretmanager
import structlog

logger = structlog.get_logger()


class CloudConfig:
    """Handle Google Cloud specific configuration."""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("PROJECT_ID"))
        self.is_cloud_run = os.getenv("K_SERVICE") is not None
        self._secret_client = None
        self._storage_client = None
    
    @property
    def secret_client(self):
        """Lazy load Secret Manager client."""
        if self._secret_client is None and self.is_cloud_run:
            self._secret_client = secretmanager.SecretManagerServiceClient()
        return self._secret_client
    
    @property
    def storage_client(self):
        """Lazy load Storage client."""
        if self._storage_client is None:
            self._storage_client = storage.Client()
        return self._storage_client
    
    def get_secret(self, secret_id: str, version: str = "latest") -> Optional[str]:
        """Retrieve secret from Secret Manager."""
        if not self.is_cloud_run:
            # In local development, use environment variables
            return os.getenv(secret_id.upper().replace("-", "_"))
        
        try:
            name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"
            response = self.secret_client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error("Failed to access secret", secret_id=secret_id, error=str(e))
            return None
    
    def get_database_url(self) -> str:
        """Get database URL with Cloud SQL proxy support."""
        if self.is_cloud_run:
            # Use Unix socket for Cloud SQL
            instance_connection_name = os.getenv("INSTANCE_CONNECTION_NAME")
            if instance_connection_name:
                db_user = os.getenv("DB_USER", "postgres")
                db_pass = self.get_secret("db-password") or os.getenv("DB_PASS")
                db_name = os.getenv("DB_NAME", "url_to_llm")
                
                # Unix socket path for Cloud SQL
                return f"postgresql://{db_user}:{db_pass}@/{db_name}?host=/cloudsql/{instance_connection_name}"
        
        # Fallback to standard DATABASE_URL
        return os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/url_to_llm")
    
    def get_redis_url(self) -> str:
        """Get Redis URL for Memorystore or local Redis."""
        if self.is_cloud_run:
            # Try to get from Secret Manager first
            redis_url = self.get_secret("redis-url")
            if redis_url:
                return redis_url
            
            # Build from environment variables
            redis_host = os.getenv("REDIS_HOST")
            redis_port = os.getenv("REDIS_PORT", "6379")
            redis_auth = os.getenv("REDIS_AUTH", "")
            
            if redis_host:
                auth_string = f":{redis_auth}@" if redis_auth else ""
                return f"redis://{auth_string}{redis_host}:{redis_port}/0"
        
        return os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    def get_storage_bucket(self) -> str:
        """Get GCS bucket name."""
        if self.is_cloud_run:
            bucket = self.get_secret("gcs-bucket") or os.getenv("GCS_BUCKET")
            if bucket:
                return bucket
        
        return os.getenv("STORAGE_BUCKET", "url-to-llm-dev")


# Global instance
cloud_config = CloudConfig()