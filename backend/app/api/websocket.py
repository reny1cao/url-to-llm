"""WebSocket endpoints for real-time updates."""

from typing import Dict, Set
from uuid import UUID
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
import structlog

from ..services.auth import verify_websocket_token
from ..dependencies import get_job_repository, get_db
from ..models.jobs import JobProgress

logger = structlog.get_logger()

router = APIRouter()

# Store active WebSocket connections
# In production, use Redis pub/sub for multiple workers
class ConnectionManager:
    def __init__(self):
        # job_id -> set of websocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # user_id -> set of websocket connections
        self.user_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, job_id: str, user_id: str):
        """Accept websocket connection."""
        await websocket.accept()
        
        # Add to job connections
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
        
        # Add to user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        
        logger.info("WebSocket connected", job_id=job_id, user_id=user_id)
    
    def disconnect(self, websocket: WebSocket, job_id: str, user_id: str):
        """Remove websocket connection."""
        # Remove from job connections
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        
        # Remove from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
                
        logger.info("WebSocket disconnected", job_id=job_id, user_id=user_id)
    
    async def send_job_update(self, job_id: str, message: dict):
        """Send update to all connections watching a job."""
        if job_id in self.active_connections:
            dead_connections = set()
            
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error("Failed to send message", error=str(e))
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for conn in dead_connections:
                self.active_connections[job_id].discard(conn)
    
    async def send_user_notification(self, user_id: str, message: dict):
        """Send notification to all connections for a user."""
        if user_id in self.user_connections:
            dead_connections = set()
            
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error("Failed to send message", error=str(e))
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for conn in dead_connections:
                self.user_connections[user_id].discard(conn)


# Global connection manager
# In production, use dependency injection
manager = ConnectionManager()


@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_updates(
    websocket: WebSocket,
    job_id: UUID,
    token: str = Query(...),
):
    """WebSocket endpoint for real-time job updates."""
    # Verify token and get user
    user = await verify_websocket_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    # Get job repository
    from ..repositories.jobs import JobRepository
    pool = await get_db()
    job_repo = JobRepository(pool)
    
    # Verify user owns the job
    job = await job_repo.get_job(job_id)
    if not job or job.created_by != user.id:
        await websocket.close(code=4003, reason="Forbidden")
        return
    
    # Connect websocket
    await manager.connect(websocket, str(job_id), user.id)
    
    try:
        # Send initial job status
        await websocket.send_json({
            "type": "job_status",
            "job": job.dict()
        })
        
        # Send recent progress history
        progress_history = await job_repo.get_job_progress_history(job_id, limit=10)
        await websocket.send_json({
            "type": "progress_history",
            "progress": [p.dict() for p in progress_history]
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for any message from client (ping/pong)
            data = await websocket.receive_text()
            
            # Handle ping
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, str(job_id), user.id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        manager.disconnect(websocket, str(job_id), user.id)


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...),
):
    """WebSocket endpoint for user notifications."""
    # Verify token and get user
    user = await verify_websocket_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    # Connect websocket for notifications
    await manager.connect(websocket, f"user_{user.id}", user.id)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to notifications"
        })
        
        # Keep connection alive
        while True:
            # Wait for any message from client
            data = await websocket.receive_text()
            
            # Handle ping
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"user_{user.id}", user.id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        manager.disconnect(websocket, f"user_{user.id}", user.id)


# Helper function to send progress updates
# This is called from background tasks
async def send_progress_update(job_id: str, progress: JobProgress):
    """Send progress update to WebSocket clients."""
    message = {
        "type": "progress_update",
        "progress": progress.dict()
    }
    await manager.send_job_update(job_id, message)


async def send_job_completed(job_id: str, job_data: dict):
    """Send job completion notification."""
    message = {
        "type": "job_completed",
        "job": job_data
    }
    await manager.send_job_update(job_id, message)