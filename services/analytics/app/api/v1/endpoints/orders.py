from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from app.core.pinot import get_pinot_client, PinotClient
from app.core.auth import get_current_admin, get_current_restaurant

router = APIRouter()

@router.get("/count")
async def get_order_count(
    start_date: Optional[datetime] = Query(None, description="Start date for the analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for the analytics period"),
    restaurant_id: Optional[str] = Query(None, description="Filter by restaurant ID"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    pinot: PinotClient = Depends(get_pinot_client),
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get the count of orders in a given time period.
    
    This endpoint requires admin privileges.
    """
    count = await pinot.get_order_count(
        start_date=start_date,
        end_date=end_date,
        restaurant_id=restaurant_id,
        status=status
    )
    
    return {"order_count": count}

@router.get("/revenue")
async def get_order_revenue(
    start_date: Optional[datetime] = Query(None, description="Start date for the analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for the analytics period"),
    restaurant_id: Optional[str] = Query(None, description="Filter by restaurant ID"),
    pinot: PinotClient = Depends(get_pinot_client),
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get the total revenue from orders in a given time period.
    
    This endpoint requires admin privileges.
    """
    revenue = await pinot.get_order_revenue(
        start_date=start_date,
        end_date=end_date,
        restaurant_id=restaurant_id
    )
    
    return {"total_revenue": revenue}

@router.get("/status-breakdown")
async def get_order_status_breakdown(
    start_date: Optional[datetime] = Query(None, description="Start date for the analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for the analytics period"),
    restaurant_id: Optional[str] = Query(None, description="Filter by restaurant ID"),
    pinot: PinotClient = Depends(get_pinot_client),
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get the breakdown of orders by status in a given time period.
    
    This endpoint requires admin privileges.
    """
    status_breakdown = await pinot.get_order_status_breakdown(
        start_date=start_date,
        end_date=end_date,
        restaurant_id=restaurant_id
    )
    
    return {"status_breakdown": status_breakdown}

@router.get("/hourly-distribution")
async def get_orders_by_hour(
    start_date: Optional[datetime] = Query(None, description="Start date for the analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for the analytics period"),
    restaurant_id: Optional[str] = Query(None, description="Filter by restaurant ID"),
    pinot: PinotClient = Depends(get_pinot_client),
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get the number of orders by hour of day in a given time period.
    
    This endpoint requires admin privileges.
    """
    hours_breakdown = await pinot.get_orders_by_hour(
        start_date=start_date,
        end_date=end_date,
        restaurant_id=restaurant_id
    )
    
    return {"hourly_distribution": hours_breakdown}

@router.get("/top-restaurants")
async def get_top_restaurants(
    start_date: Optional[datetime] = Query(None, description="Start date for the analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for the analytics period"),
    limit: int = Query(10, ge=1, le=100, description="Number of restaurants to return"),
    pinot: PinotClient = Depends(get_pinot_client),
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get the top restaurants by order count in a given time period.
    
    This endpoint requires admin privileges.
    """
    top_restaurants = await pinot.get_top_restaurants(
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    return {"top_restaurants": top_restaurants}

@router.get("/average-values")
async def get_average_values(
    start_date: Optional[datetime] = Query(None, description="Start date for the analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for the analytics period"),
    restaurant_id: Optional[str] = Query(None, description="Filter by restaurant ID"),
    pinot: PinotClient = Depends(get_pinot_client),
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get average values for orders in a given time period.
    
    This endpoint requires admin privileges.
    """
    avg_order_value = await pinot.get_average_order_value(
        start_date=start_date,
        end_date=end_date,
        restaurant_id=restaurant_id
    )
    
    avg_delivery_time = await pinot.get_average_delivery_time(
        start_date=start_date,
        end_date=end_date,
        restaurant_id=restaurant_id
    )
    
    return {
        "average_order_value": avg_order_value,
        "average_delivery_time_minutes": avg_delivery_time
    }

@router.get("/restaurant-analytics")
async def get_restaurant_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date for the analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for the analytics period"),
    pinot: PinotClient = Depends(get_pinot_client),
    current_user: Dict[str, Any] = Depends(get_current_restaurant)
):
    """
    Get analytics for the current restaurant.
    
    This endpoint is for restaurant owners/managers to see their analytics.
    """
    restaurant_id = current_user["id"]
    
    # Get order count
    order_count = await pinot.get_order_count(
        start_date=start_date,
        end_date=end_date,
        restaurant_id=restaurant_id
    )
    
    # Get revenue
    revenue = await pinot.get_order_revenue(
        start_date=start_date,
        end_date=end_date,
        restaurant_id=restaurant_id
    )
    
    # Get status breakdown
    status_breakdown = await pinot.get_order_status_breakdown(
        start_date=start_date,
        end_date=end_date,
        restaurant_id=restaurant_id
    )
    
    # Get hourly distribution
    hourly_distribution = await pinot.get_orders_by_hour(
        start_date=start_date,
        end_date=end_date,
        restaurant_id=restaurant_id
    )
    
    # Get average values
    avg_order_value = await pinot.get_average_order_value(
        start_date=start_date,
        end_date=end_date,
        restaurant_id=restaurant_id
    )
    
    avg_delivery_time = await pinot.get_average_delivery_time(
        start_date=start_date,
        end_date=end_date,
        restaurant_id=restaurant_id
    )
    
    return {
        "restaurant_id": restaurant_id,
        "order_count": order_count,
        "total_revenue": revenue,
        "status_breakdown": status_breakdown,
        "hourly_distribution": hourly_distribution,
        "average_order_value": avg_order_value,
        "average_delivery_time_minutes": avg_delivery_time
    }