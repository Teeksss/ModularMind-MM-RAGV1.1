import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.api.v1.api import api_router
from app.core.config import settings
from app.api.error_handler import setup_error_handlers
from app.api.rate_limit_middleware import setup_rate_limiting
from app.utils.monitoring import setup_monitoring
from app.services.fine_tuning_scheduler import get_fine_tuning_scheduler
from app.db.mongodb import connect_to_mongo, close_mongo_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.version,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# Setup error handlers
setup_error_handlers(app)

# Setup monitoring
setup_monitoring(app)

# Setup rate limiting
setup_rate_limiting(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Include health check endpoints
from app.api.v1.endpoints.health_check import router as health_router
app.include_router(health_router, prefix="/health", tags=["Health"])

# Database connection events
@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()
    logger.info("Connected to MongoDB")


@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()
    logger.info("Disconnected from MongoDB")


# Start background services
@app.on_event("startup")
async def start_background_services():
    # Start fine-tuning scheduler
    fine_tuning_scheduler = get_fine_tuning_scheduler()
    await fine_tuning_scheduler.start()
    logger.info("Started fine-tuning scheduler")


# Shutdown background services
@app.on_event("shutdown")
async def stop_background_services():
    # Stop fine-tuning scheduler
    fine_tuning_scheduler = get_fine_tuning_scheduler()
    await fine_tuning_scheduler.stop()
    logger.info("Stopped fine-tuning scheduler")


# Simple root endpoint
@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "docs": "/docs" if settings.environment != "production" else None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development"
    )