from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, addresses, profiles, restaurants, orders, map_view

api_router = APIRouter(prefix="/v1")

# Include all API routes from various endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(addresses.router, prefix="/addresses", tags=["addresses"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(restaurants.router, prefix="/restaurants", tags=["restaurants"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(map_view.router, prefix="/maps", tags=["maps"])