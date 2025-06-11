"""Application configuration."""

from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Application
    app_name: str = "URL to LLM API"
    debug: bool = False
    environment: str = "development"

    # Database
    database_url: str
    redis_url: str = "redis://localhost:6379"

    # S3/MinIO
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    cdn_url: str = "https://cdn.example.com"

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # OAuth2
    oauth_client_id: str
    oauth_client_secret: str
    allowed_redirect_uris: List[str] = ["http://localhost:3000/auth/callback"]

    # CORS
    allowed_origins: List[str] = ["http://localhost:3000"]

    # Rate limiting
    rate_limit_per_minute: int = 120

    # MCP
    mcp_enabled: bool = True
    mcp_tools_prefix: str = "/tools"

    # Monitoring
    enable_metrics: bool = True
    enable_tracing: bool = True

    # External services
    capsolver_api_key: Optional[str] = None
    proxy_pool_url: Optional[str] = None


# Global settings instance
settings = Settings()
