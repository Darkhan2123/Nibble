from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.core.auth import get_current_admin
from app.core.http_client import (
    user_service_client, restaurant_service_client, 
    driver_service_client, order_service_client, 
    analytics_service_client
)
from app.models.support_ticket import SupportTicketRepository

router = APIRouter()
ticket_repository = SupportTicketRepository()

@router.get("/summary")
async def get_dashboard_summary(
    days: int = Query(7, ge=1, le=90, description="Number of days for statistics"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get a summary of key metrics for the dashboard.
    
    This endpoint provides a summary of users, orders, restaurants, etc.
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Retrieve data from various services in parallel using the clients
        # Normally, we'd use something like asyncio.gather for parallel requests
        
        # Get total users from user service
        users_data = await user_service_client.get(
            path="/api/v1/admin/stats",
            params={"admin_token": current_admin.get("id")},
            token=current_admin.get("token")
        )
        
        # Get restaurant data
        restaurant_data = await restaurant_service_client.get(
            path="/api/v1/admin/stats",
            params={"admin_token": current_admin.get("id")},
            token=current_admin.get("token")
        )
        
        # Get order data
        order_data = await order_service_client.get(
            path="/api/v1/admin/stats",
            params={
                "admin_token": current_admin.get("id"),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            token=current_admin.get("token")
        )
        
        # Get driver data
        driver_data = await driver_service_client.get(
            path="/api/v1/admin/stats",
            params={"admin_token": current_admin.get("id")},
            token=current_admin.get("token")
        )
        
        # Get ticket stats
        open_tickets = await ticket_repository.get_tickets(status="open")
        in_progress_tickets = await ticket_repository.get_tickets(status="in_progress")
        
        # Compile the summary
        summary = {
            "users": {
                "total": users_data.get("total_users", 0),
                "active": users_data.get("active_users", 0),
                "new_this_period": users_data.get("new_users", 0)
            },
            "restaurants": {
                "total": restaurant_data.get("total_restaurants", 0),
                "active": restaurant_data.get("active_restaurants", 0),
                "pending_approval": restaurant_data.get("pending_approval", 0)
            },
            "drivers": {
                "total": driver_data.get("total_drivers", 0),
                "active": driver_data.get("active_drivers", 0),
                "pending_approval": driver_data.get("pending_approval", 0)
            },
            "orders": {
                "total": order_data.get("total_orders", 0),
                "completed": order_data.get("completed_orders", 0),
                "cancelled": order_data.get("cancelled_orders", 0),
                "revenue": order_data.get("total_revenue", 0)
            },
            "support": {
                "open_tickets": len(open_tickets),
                "in_progress_tickets": len(in_progress_tickets)
            },
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            }
        }
        
        return summary
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving dashboard data: {str(e)}"
        )

@router.get("/orders-chart")
async def get_orders_chart(
    days: int = Query(7, ge=1, le=90, description="Number of days for statistics"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get order data for charts on the dashboard.
    
    This endpoint provides data for order charts.
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get order chart data from analytics service
        analytics_data = await analytics_service_client.get(
            path="/api/v1/orders/hourly-distribution",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            token=current_admin.get("token")
        )
        
        return analytics_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving order chart data: {str(e)}"
        )

@router.get("/revenue-chart")
async def get_revenue_chart(
    days: int = Query(7, ge=1, le=90, description="Number of days for statistics"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get revenue data for charts on the dashboard.
    
    This endpoint provides data for revenue charts.
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get revenue chart data from analytics service
        analytics_data = await analytics_service_client.get(
            path="/api/v1/orders/revenue",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "group_by": "day"
            },
            token=current_admin.get("token")
        )
        
        return analytics_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving revenue chart data: {str(e)}"
        )

@router.get("/top-restaurants")
async def get_top_restaurants(
    days: int = Query(30, ge=1, le=365, description="Number of days for statistics"),
    limit: int = Query(10, ge=1, le=100, description="Number of restaurants to return"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get the top performing restaurants.
    
    This endpoint provides data on the top restaurants by order count or revenue.
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get top restaurants from analytics service
        analytics_data = await analytics_service_client.get(
            path="/api/v1/orders/top-restaurants",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "limit": limit
            },
            token=current_admin.get("token")
        )
        
        return analytics_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving top restaurants: {str(e)}"
        )

@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50, description="Number of activities to return"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get recent system activity.
    
    This endpoint provides a feed of recent activity across the system.
    """
    # This would normally fetch from a system activity log
    # For now, we'll return mock data
    
    now = datetime.utcnow()
    
    activities = [
        {
            "id": "1",
            "type": "order",
            "action": "created",
            "subject_id": f"order-{i}",
            "subject_name": f"Order #{1000 + i}",
            "timestamp": (now - timedelta(minutes=i*5)).isoformat(),
            "details": {
                "customer_id": f"user-{i}",
                "restaurant_id": f"restaurant-{i % 5}",
                "amount": 25.99 + i
            }
        }
        for i in range(limit)
    ]
    
    return {
        "activities": activities,
        "total": limit
    }