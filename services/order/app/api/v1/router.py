from fastapi import APIRouter
from app.api.v1.endpoints import orders, cart, payments, webhooks

api_router = APIRouter()

api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(cart.router, prefix="/cart", tags=["cart"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])