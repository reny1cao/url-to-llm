"""Google Cloud Storage implementation."""

import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import structlog

from google.cloud import storage
from google.cloud.exceptions import NotFound

from .base import StorageBackend

logger = structlog.get_logger()


class GCSStorage(StorageBackend):
    """Google Cloud Storage backend implementation."""
    
    def __init__(self, bucket_name: str, client: Optional[storage.Client] = None):
        """Initialize GCS storage backend."""
        self.bucket_name = bucket_name
        self.client = client or storage.Client()
        self._bucket = None
    
    @property
    def bucket(self) -> storage.Bucket:
        """Lazy load bucket."""
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
            # Create bucket if it doesn't exist (for development)
            if not self._bucket.exists():
                logger.info(f"Creating GCS bucket: {self.bucket_name}")
                self._bucket.create(location="US")
        return self._bucket
    
    async def put_page(self, host: str, url: str, content: str, content_type: str = "text/html") -> str:
        """Store a page in GCS."""
        path = self._get_page_path(host, url)
        blob = self.bucket.blob(path)
        
        # Set content type and encoding
        blob.content_type = content_type
        blob.content_encoding = "utf-8"
        
        # Upload content
        blob.upload_from_string(content.encode('utf-8'))
        
        # Set metadata
        blob.metadata = {
            "host": host,
            "url": url,
            "crawled_at": datetime.utcnow().isoformat()
        }
        blob.patch()
        
        logger.info("Stored page in GCS", path=path, size=len(content))
        return f"gs://{self.bucket_name}/{path}"
    
    async def get_page(self, host: str, url: str) -> Optional[str]:
        """Retrieve a page from GCS."""
        path = self._get_page_path(host, url)
        blob = self.bucket.blob(path)
        
        try:
            content = blob.download_as_text()
            logger.info("Retrieved page from GCS", path=path)
            return content
        except NotFound:
            logger.warning("Page not found in GCS", path=path)
            return None
    
    async def put_manifest(self, host: str, manifest: Dict[str, Any]) -> str:
        """Store a manifest in GCS."""
        path = f"manifests/{host}/manifest.json"
        blob = self.bucket.blob(path)
        
        # Convert manifest to JSON
        content = json.dumps(manifest, indent=2, ensure_ascii=False)
        
        # Upload with metadata
        blob.content_type = "application/json"
        blob.upload_from_string(content.encode('utf-8'))
        
        # Set cache control for manifests
        blob.cache_control = "public, max-age=3600"  # 1 hour cache
        blob.patch()
        
        logger.info("Stored manifest in GCS", path=path)
        return f"gs://{self.bucket_name}/{path}"
    
    async def get_manifest(self, host: str) -> Optional[Dict[str, Any]]:
        """Retrieve a manifest from GCS."""
        path = f"manifests/{host}/manifest.json"
        blob = self.bucket.blob(path)
        
        try:
            content = blob.download_as_text()
            manifest = json.loads(content)
            logger.info("Retrieved manifest from GCS", path=path)
            return manifest
        except NotFound:
            logger.warning("Manifest not found in GCS", path=path)
            return None
        except json.JSONDecodeError as e:
            logger.error("Invalid manifest JSON", path=path, error=str(e))
            return None
    
    async def delete_page(self, host: str, url: str) -> bool:
        """Delete a page from GCS."""
        path = self._get_page_path(host, url)
        blob = self.bucket.blob(path)
        
        try:
            blob.delete()
            logger.info("Deleted page from GCS", path=path)
            return True
        except NotFound:
            logger.warning("Page not found for deletion", path=path)
            return False
    
    async def list_pages(self, host: str, prefix: Optional[str] = None) -> list[str]:
        """List all pages for a host."""
        base_prefix = f"pages/{host}/"
        if prefix:
            base_prefix += prefix
        
        blobs = self.bucket.list_blobs(prefix=base_prefix)
        pages = []
        
        for blob in blobs:
            # Extract URL from blob name
            url = blob.name.replace(base_prefix, "")
            if url:
                pages.append(url)
        
        logger.info("Listed pages from GCS", host=host, count=len(pages))
        return pages
    
    def get_signed_url(self, path: str, expiration_minutes: int = 60) -> str:
        """Generate a signed URL for temporary access."""
        blob = self.bucket.blob(path)
        
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="GET"
        )
        
        return url
    
    async def get_stats(self, host: str) -> Dict[str, Any]:
        """Get storage statistics for a host."""
        prefix = f"pages/{host}/"
        blobs = self.bucket.list_blobs(prefix=prefix)
        
        total_size = 0
        page_count = 0
        
        for blob in blobs:
            total_size += blob.size or 0
            page_count += 1
        
        return {
            "page_count": page_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }