"""Main FastAPI application."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from .core.config import settings
from .dependencies import cleanup_dependencies, init_dependencies
from .routers import auth, mcp, users
from .api import crawl, websocket

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting application")
    await init_dependencies()

    yield

    # Shutdown
    logger.info("Shutting down application")
    await cleanup_dependencies()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(mcp.router)
app.include_router(crawl.router)
app.include_router(websocket.router)

# Development endpoints
if settings.environment == "development":
    from .routers import dev
    app.include_router(dev.router)

# Mount Prometheus metrics
if settings.enable_metrics:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "mcp_enabled": settings.mcp_enabled,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    import redis.asyncio as redis
    from .core.config import settings
    from .db.session import get_db_pool
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Check database
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        health_status["checks"]["database"] = {"status": "ok", "latency_ms": 0}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "error", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        redis_client = await redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        health_status["checks"]["redis"] = {"status": "ok", "latency_ms": 0}
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "error", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Check S3/MinIO
    try:
        import aioboto3
        session = aioboto3.Session()
        async with session.client(
            's3',
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region
        ) as s3:
            await s3.head_bucket(Bucket=settings.s3_bucket)
        health_status["checks"]["s3"] = {"status": "ok", "latency_ms": 0}
    except Exception as e:
        health_status["checks"]["s3"] = {"status": "error", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    return health_status


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        exc_info=exc
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": "internal_error"
        }
    )
