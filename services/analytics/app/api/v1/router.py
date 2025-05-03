from fastapi import APIRouter
from app.api.v1.endpoints import orders, restaurants, drivers

api_router = APIRouter()

api_router.include_router(orders.router, prefix="/orders", tags=["order-analytics"])
api_router.include_router(restaurants.router, prefix="/restaurants", tags=["restaurant-analytics"])
api_router.include_router(drivers.router, prefix="/drivers", tags=["driver-analytics"])