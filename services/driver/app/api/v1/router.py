from fastapi import APIRouter
from app.api.v1.endpoints import drivers, deliveries, reviews

api_router = APIRouter(prefix="/v1")

# Include all API routes from various endpoints
api_router.include_router(drivers.router, prefix="/drivers", tags=["drivers"])
api_router.include_router(deliveries.router, prefix="/deliveries", tags=["deliveries"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])