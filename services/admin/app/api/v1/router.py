from fastapi import APIRouter
from app.api.v1.endpoints import promotions, support_tickets, dashboard, users

api_router = APIRouter()

api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(promotions.router, prefix="/promotions", tags=["promotions"])
api_router.include_router(support_tickets.router, prefix="/tickets", tags=["support-tickets"])