import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from app.core.config import settings
from app.api.router import api_router
from app.core.pinot import pinot_client
from app.dashboard.routes import dashboard_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="UberEats Clone Analytics Service",
    description="Analytics service for UberEats Clone",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api")
app.include_router(dashboard_router, tags=["dashboard"])

# Health check endpoint
@app.get("/health")
async def health_check():
    # Check Pinot connection
    pinot_healthy = await pinot_client.check_health()
    
    return {
        "status": "healthy" if pinot_healthy else "degraded",
        "service": "analytics-service",
        "version": "1.0.0",
        "pinot_connection": "up" if pinot_healthy else "down",
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Analytics Service")
    
    # Check if Pinot is healthy on startup
    pinot_healthy = await pinot_client.check_health()
    if pinot_healthy:
        logger.info("Successfully connected to Apache Pinot")
    else:
        logger.warning("Could not connect to Apache Pinot - analytics may be unavailable")
    
    # Check if tables exist
    tables = await pinot_client.get_tables()
    logger.info(f"Available Pinot tables: {tables}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)