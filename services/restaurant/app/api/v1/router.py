from fastapi import APIRouter
from app.api.v1.endpoints import restaurants, menu, orders, reviews

api_router = APIRouter(prefix="/v1")

# Include all API routes from various endpoints
api_router.include_router(restaurants.router, prefix="/restaurants", tags=["restaurants"])
api_router.include_router(menu.router, prefix="/menu", tags=["menu"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])