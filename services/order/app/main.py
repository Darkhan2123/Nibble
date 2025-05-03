import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from typing import List
import logging

from app.core.config import settings
from app.api.router import api_router
from app.core.logging import setup_logging
from app.core.database import get_db, init_db
from app.core.kafka import init_kafka

# Setup logging
logger = logging.getLogger(__name__)
setup_logging()

# Initialize FastAPI app
app = FastAPI(
    title="UberEats Clone Order Service",
    description="Order processing and management service",
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
        "service": "order-service",
        "version": "1.0.0",
    }

# Startup event to initialize database connections and Kafka
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Order Service")
    await init_db()
    await init_kafka()
    
    # Start background tasks for order processing
    from app.workers.order_processors import start_background_tasks
    await start_background_tasks()
    logger.info("Background tasks started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)