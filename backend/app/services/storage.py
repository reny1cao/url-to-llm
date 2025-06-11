"""Storage service for S3/MinIO operations."""

import io
from typing import Optional
import aioboto3
from botocore.exceptions import ClientError
import structlog

from ..core.config import settings

logger = structlog.get_logger()


class StorageService:
    """Service for managing S3/MinIO storage operations."""
    
    def __init__(self):
        self.endpoint = settings.s3_endpoint
        self.access_key = settings.s3_access_key
        self.secret_key = settings.s3_secret_key
        self.bucket = settings.s3_bucket
        self.session = aioboto3.Session()
    
    async def get_manifest(self, host: str) -> Optional[str]:
        """Get manifest content for a host."""
        key = f"manifests/{host}/llm.txt"
        
        try:
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            ) as s3:
                response = await s3.get_object(Bucket=self.bucket, Key=key)
                content = await response['Body'].read()
                return content.decode('utf-8')
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.info("Manifest not found", host=host, key=key)
                return None
            logger.error("Failed to get manifest", host=host, error=str(e))
            raise
    
    async def put_manifest(self, host: str, content: str) -> str:
        """Store manifest content for a host."""
        key = f"manifests/{host}/llm.txt"
        
        try:
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            ) as s3:
                await s3.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=content.encode('utf-8'),
                    ContentType='text/plain',
                )
                
                # Return the public URL
                return f"{settings.cdn_url}/{key}"
        except Exception as e:
            logger.error("Failed to store manifest", host=host, error=str(e))
            raise
    
    async def list_manifests(self, prefix: Optional[str] = None) -> list[str]:
        """List all manifest keys."""
        prefix = f"manifests/{prefix}" if prefix else "manifests/"
        
        try:
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            ) as s3:
                response = await s3.list_objects_v2(
                    Bucket=self.bucket,
                    Prefix=prefix,
                )
                
                if 'Contents' not in response:
                    return []
                
                return [obj['Key'] for obj in response['Contents']]
        except Exception as e:
            logger.error("Failed to list manifests", error=str(e))
            raise
    
    async def delete_manifest(self, host: str) -> bool:
        """Delete manifest for a host."""
        key = f"manifests/{host}/llm.txt"
        
        try:
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            ) as s3:
                await s3.delete_object(Bucket=self.bucket, Key=key)
                return True
        except Exception as e:
            logger.error("Failed to delete manifest", host=host, error=str(e))
            return False