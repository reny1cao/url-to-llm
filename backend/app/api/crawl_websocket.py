"""WebSocket endpoint for real-time crawl progress updates."""

from typing import Dict, Set
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

logger = structlog.get_logger()

router = APIRouter()

class CrawlConnectionManager:
    def __init__(self):
        # host -> set of websocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store latest progress for each host
        self.crawl_progress: Dict[str, dict] = {}
    
    async def connect(self, websocket: WebSocket, host: str):
        """Accept websocket connection."""
        await websocket.accept()
        
        if host not in self.active_connections:
            self.active_connections[host] = set()
        self.active_connections[host].add(websocket)
        
        # Send current progress if available
        if host in self.crawl_progress:
            await websocket.send_json({
                "type": "progress",
                "host": host,
                **self.crawl_progress[host]
            })
        
        logger.info("Crawl WebSocket connected", host=host)
    
    def disconnect(self, websocket: WebSocket, host: str):
        """Remove websocket connection."""
        if host in self.active_connections:
            self.active_connections[host].discard(websocket)
            if not self.active_connections[host]:
                del self.active_connections[host]
        logger.info("Crawl WebSocket disconnected", host=host)
    
    async def send_crawl_update(self, host: str, progress: dict):
        """Send update to all connections watching a host."""
        # Store latest progress
        self.crawl_progress[host] = progress
        
        if host in self.active_connections:
            dead_connections = set()
            
            message = {
                "type": "progress",
                "host": host,
                **progress
            }
            
            for connection in self.active_connections[host]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error("Failed to send crawl update", error=str(e))
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for conn in dead_connections:
                self.active_connections[host].discard(conn)
    
    async def send_crawl_complete(self, host: str, result: dict):
        """Send crawl completion notification."""
        # Clear progress
        if host in self.crawl_progress:
            del self.crawl_progress[host]
        
        if host in self.active_connections:
            message = {
                "type": "complete",
                "host": host,
                **result
            }
            
            dead_connections = set()
            for connection in self.active_connections[host]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error("Failed to send completion", error=str(e))
                    dead_connections.add(connection)
            
            # Clean up
            for conn in dead_connections:
                self.active_connections[host].discard(conn)

# Global crawl manager
crawl_manager = CrawlConnectionManager()

@router.websocket("/ws/crawl/{host}")
async def websocket_crawl_progress(
    websocket: WebSocket,
    host: str
):
    """WebSocket endpoint for real-time crawl progress updates."""
    await crawl_manager.connect(websocket, host)
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        crawl_manager.disconnect(websocket, host)
    except Exception as e:
        logger.error("Crawl WebSocket error", error=str(e))
        crawl_manager.disconnect(websocket, host)

# Helper function for crawler to send updates
async def send_crawl_progress(host: str, pages_crawled: int, pages_discovered: int, 
                            pages_added: int, pages_updated: int, current_url: str = None,
                            bytes_downloaded: int = 0):
    """Send crawl progress update."""
    progress = {
        "pages_crawled": pages_crawled,
        "pages_discovered": pages_discovered,
        "pages_added": pages_added,
        "pages_updated": pages_updated,
        "current_url": current_url,
        "bytes_downloaded": bytes_downloaded,
        "progress_percent": min(100, int((pages_crawled / max(pages_discovered, 1)) * 100))
    }
    await crawl_manager.send_crawl_update(host, progress)

async def send_crawl_completed(host: str, pages_crawled: int, pages_added: int, 
                             pages_updated: int, errors: list = None):
    """Send crawl completion notification."""
    result = {
        "pages_crawled": pages_crawled,
        "pages_added": pages_added,
        "pages_updated": pages_updated,
        "errors": errors or [],
        "success": True
    }
    await crawl_manager.send_crawl_complete(host, result)