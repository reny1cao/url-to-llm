"""S3/MinIO client for storing documentation content.

This module provides an async S3 client optimized for storing and retrieving
documentation content including HTML pages, markdown files, and assets.
"""

import asyncio
from typing import Optional, Union, Dict, Any, List
from contextlib import asynccontextmanager
import mimetypes
from pathlib import Path

import aioboto3
from botocore.exceptions import ClientError
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class S3Client:
    """Async S3 client for documentation storage.
    
    This client provides methods for uploading, downloading, and managing
    documentation content in S3-compatible storage (including MinIO).
    """
    
    def __init__(self):
        """Initialize the S3 client with configuration from settings."""
        self.endpoint_url = settings.s3_endpoint_url
        self.access_key = settings.s3_access_key
        self.secret_key = settings.s3_secret_key
        self.bucket_name = settings.s3_bucket
        self.region = settings.s3_region
        
        # Check if we're using GCS instead
        if settings.s3_endpoint_url == "dummy" and hasattr(settings, 'gcs_bucket'):
            # Use GCS S3-compatible API
            self.endpoint_url = "https://storage.googleapis.com"
            self.bucket_name = settings.gcs_bucket
            logger.info("Using GCS S3-compatible API", bucket=self.bucket_name)
        
        # Initialize session
        self.session = aioboto3.Session()
        
        # Ensure mimetypes are initialized
        mimetypes.init()
    
    @asynccontextmanager
    async def get_client(self):
        """Get an async S3 client context manager."""
        async with self.session.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            use_ssl=self.endpoint_url.startswith('https')
        ) as client:
            yield client
    
    async def ensure_bucket_exists(self) -> bool:
        """Ensure the bucket exists, create if not.
        
        Returns:
            bool: True if bucket exists or was created successfully
        """
        async with self.get_client() as client:
            try:
                await client.head_bucket(Bucket=self.bucket_name)
                return True
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code == '404':
                    # Bucket doesn't exist, create it
                    try:
                        await client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                            if self.region != 'us-east-1' else {}
                        )
                        logger.info("Created S3 bucket", bucket=self.bucket_name)
                        
                        # Set bucket policy for public read on documentation
                        await self._set_bucket_policy(client)
                        return True
                    except ClientError as create_error:
                        logger.error("Failed to create bucket", 
                                   bucket=self.bucket_name, 
                                   error=str(create_error))
                        return False
                else:
                    logger.error("Failed to check bucket", 
                               bucket=self.bucket_name, 
                               error=str(e))
                    return False
    
    async def upload_content(
        self,
        content: Union[bytes, str],
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        cache_control: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload content to S3.
        
        Args:
            content: The content to upload (bytes or string)
            key: The S3 key (path) for the object
            content_type: MIME type of the content
            metadata: Additional metadata to store with the object
            cache_control: Cache-Control header value
            
        Returns:
            Dict containing upload result including ETag and version ID
        """
        # Convert string to bytes if necessary
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        # Guess content type if not provided
        if not content_type:
            content_type = mimetypes.guess_type(key)[0] or 'application/octet-stream'
        
        # Prepare upload parameters
        upload_params = {
            'Bucket': self.bucket_name,
            'Key': key,
            'Body': content,
            'ContentType': content_type
        }
        
        if metadata:
            upload_params['Metadata'] = metadata
        
        if cache_control:
            upload_params['CacheControl'] = cache_control
        
        async with self.get_client() as client:
            try:
                response = await client.put_object(**upload_params)
                
                logger.info("Uploaded content to S3", 
                          key=key, 
                          size=len(content),
                          content_type=content_type)
                
                return {
                    'key': key,
                    'etag': response.get('ETag', '').strip('"'),
                    'version_id': response.get('VersionId'),
                    'size': len(content)
                }
                
            except ClientError as e:
                logger.error("Failed to upload to S3", 
                           key=key, 
                           error=str(e))
                raise
    
    async def download_content(self, key: str) -> Optional[bytes]:
        """Download content from S3.
        
        Args:
            key: The S3 key (path) of the object
            
        Returns:
            The content as bytes, or None if not found
        """
        async with self.get_client() as client:
            try:
                response = await client.get_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                
                content = await response['Body'].read()
                
                logger.info("Downloaded content from S3", 
                          key=key, 
                          size=len(content))
                
                return content
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code == 'NoSuchKey':
                    logger.warning("Object not found in S3", key=key)
                    return None
                else:
                    logger.error("Failed to download from S3", 
                               key=key, 
                               error=str(e))
                    raise
    
    async def delete_content(self, key: str) -> bool:
        """Delete content from S3.
        
        Args:
            key: The S3 key (path) of the object
            
        Returns:
            True if deleted successfully, False otherwise
        """
        async with self.get_client() as client:
            try:
                await client.delete_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                
                logger.info("Deleted content from S3", key=key)
                return True
                
            except ClientError as e:
                logger.error("Failed to delete from S3", 
                           key=key, 
                           error=str(e))
                return False
    
    async def list_objects(self, prefix: str = "", max_keys: int = 1000) -> List[Dict[str, Any]]:
        """List objects in S3 with a given prefix.
        
        Args:
            prefix: The prefix to filter objects
            max_keys: Maximum number of objects to return
            
        Returns:
            List of object metadata dictionaries
        """
        objects = []
        
        async with self.get_client() as client:
            try:
                paginator = client.get_paginator('list_objects_v2')
                
                async for page in paginator.paginate(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                    PaginationConfig={'MaxItems': max_keys}
                ):
                    for obj in page.get('Contents', []):
                        objects.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'etag': obj['ETag'].strip('"')
                        })
                
                return objects
                
            except ClientError as e:
                logger.error("Failed to list objects in S3", 
                           prefix=prefix, 
                           error=str(e))
                raise
    
    async def copy_object(self, source_key: str, dest_key: str) -> bool:
        """Copy an object within S3.
        
        Args:
            source_key: The source S3 key
            dest_key: The destination S3 key
            
        Returns:
            True if copied successfully
        """
        async with self.get_client() as client:
            try:
                copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
                
                await client.copy_object(
                    CopySource=copy_source,
                    Bucket=self.bucket_name,
                    Key=dest_key
                )
                
                logger.info("Copied object in S3", 
                          source=source_key, 
                          dest=dest_key)
                return True
                
            except ClientError as e:
                logger.error("Failed to copy object in S3", 
                           source=source_key, 
                           dest=dest_key,
                           error=str(e))
                return False
    
    async def generate_presigned_url(
        self, 
        key: str, 
        expiration: int = 3600,
        http_method: str = 'GET'
    ) -> Optional[str]:
        """Generate a presigned URL for temporary access.
        
        Args:
            key: The S3 key of the object
            expiration: URL expiration time in seconds
            http_method: HTTP method for the URL (GET or PUT)
            
        Returns:
            The presigned URL or None if failed
        """
        async with self.get_client() as client:
            try:
                url = await client.generate_presigned_url(
                    ClientMethod='get_object' if http_method == 'GET' else 'put_object',
                    Params={'Bucket': self.bucket_name, 'Key': key},
                    ExpiresIn=expiration
                )
                
                return url
                
            except ClientError as e:
                logger.error("Failed to generate presigned URL", 
                           key=key, 
                           error=str(e))
                return None
    
    def get_public_url(self, key: str) -> str:
        """Get the public URL for an object.
        
        Args:
            key: The S3 key of the object
            
        Returns:
            The public URL
        """
        # For MinIO or S3 with public access
        if 'amazonaws.com' in self.endpoint_url:
            # AWS S3 URL format
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
        else:
            # MinIO or custom S3 URL format
            return f"{self.endpoint_url}/{self.bucket_name}/{key}"
    
    async def _set_bucket_policy(self, client):
        """Set bucket policy for public read access on documentation."""
        # Policy allows public read for documentation content
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{self.bucket_name}/sites/*"
                }
            ]
        }
        
        import json
        try:
            await client.put_bucket_policy(
                Bucket=self.bucket_name,
                Policy=json.dumps(policy)
            )
            logger.info("Set bucket policy for public documentation access")
        except ClientError as e:
            logger.warning("Failed to set bucket policy", error=str(e))


# Singleton instance
s3_client = S3Client()


async def get_s3_client() -> S3Client:
    """Get the S3 client instance.
    
    This is a dependency injection function for FastAPI.
    """
    return s3_client