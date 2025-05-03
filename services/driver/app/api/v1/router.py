from fastapi import APIRouter
from app.api.v1.endpoints import drivers, deliveries

api_router = APIRouter(prefix="/v1")

# Include all API routes from various endpoints
api_router.include_router(drivers.router, prefix="/drivers", tags=["drivers"])
api_router.include_router(deliveries.router, prefix="/deliveries", tags=["deliveries"])