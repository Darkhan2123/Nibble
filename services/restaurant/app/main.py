import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from typing import List
import logging

from app.core.config import settings
from app.api.v1.router import api_router
from app.core.logging import setup_logging
from app.core.database import get_db, init_db
from app.core.redis import init_redis

# Setup logging
logger = logging.getLogger(__name__)
setup_logging()

# Initialize FastAPI app
app = FastAPI(
    title="UberEats Clone Restaurant Service",
    description="Restaurant and menu management service",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "restaurant-service",
        "version": "1.0.0",
    }

# Startup event to initialize database and Redis connections
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Restaurant Service")
    # Initialize database
    await init_db()
    # Initialize Redis
    await init_redis()
    logger.info("Restaurant Service started successfully")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)