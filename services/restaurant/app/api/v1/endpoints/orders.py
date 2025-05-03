from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta

from app.core.auth import validate_token, has_role, restaurant_owner_or_admin
from app.models.restaurant import RestaurantRepository
from app.models.order import RestaurantOrderRepository
from app.schemas.order import (
    OrderResponse, OrderListResponse, OrderUpdateRequest,
    OrderHistoryParams, OrderStatisticsResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/restaurant", response_model=OrderListResponse)
async def get_restaurant_orders(
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Get orders for the current user's restaurant.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    order_repo = RestaurantOrderRepository()
    
    # Get the user's restaurant
    restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    # Validate status if provided
    valid_statuses = [
        "placed", "confirmed", "preparing", "ready_for_pickup", 
        "out_for_delivery", "delivered", "picked_up", "cancelled"
    ]
    if status and status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    orders = await order_repo.get_restaurant_orders(
        restaurant_id=restaurant["id"],
        status=status,
        limit=limit,
        offset=offset
    )
    
    # For now, we'll assume the total is the count of returned orders
    # In a real application, you would want to get the total count separately
    
    return {
        "items": orders,
        "total": len(orders),
        "limit": limit,
        "offset": offset
    }

@router.get("/restaurant/active", response_model=List[OrderResponse])
async def get_active_orders(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Get active orders for the current user's restaurant.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    order_repo = RestaurantOrderRepository()
    
    # Get the user's restaurant
    restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    orders = await order_repo.get_active_orders(
        restaurant_id=restaurant["id"],
        limit=limit,
        offset=offset
    )
    
    return orders

@router.get("/restaurant/{order_id}", response_model=OrderResponse)
async def get_restaurant_order(
    order_id: str,
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Get a specific order for the current user's restaurant.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    order_repo = RestaurantOrderRepository()
    
    # Get the user's restaurant
    restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    order = await order_repo.get_order_by_id(
        order_id=order_id,
        restaurant_id=restaurant["id"]
    )
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order

@router.post("/restaurant/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    update_request: OrderUpdateRequest,
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Update the status of an order.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    order_repo = RestaurantOrderRepository()
    
    # Get the user's restaurant
    restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    # Check if order exists and belongs to this restaurant
    existing_order = await order_repo.get_order_by_id(
        order_id=order_id,
        restaurant_id=restaurant["id"]
    )
    
    if not existing_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    try:
        updated_order = await order_repo.update_order_status(
            order_id=order_id,
            restaurant_id=restaurant["id"],
            status=update_request.status,
            notes=update_request.notes
        )
        
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update order status"
            )
        
        logger.info(f"Order status updated: {order_id} to {update_request.status}")
        
        return updated_order
        
    except ValueError as e:
        logger.error(f"Error updating order status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error updating order status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/restaurant/history", response_model=Dict[str, Any])
async def get_order_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Get order history for the current user's restaurant.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    order_repo = RestaurantOrderRepository()
    
    # Get the user's restaurant
    restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    # Validate date formats if provided
    if start_date:
        try:
            datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    if end_date:
        try:
            datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    history = await order_repo.get_order_history(
        restaurant_id=restaurant["id"],
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    return history

@router.get("/restaurant/statistics", response_model=OrderStatisticsResponse)
async def get_order_statistics(
    period: str = Query("day", regex="^(day|week|month|year)$"),
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Get order statistics for the current user's restaurant.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    order_repo = RestaurantOrderRepository()
    
    # Get the user's restaurant
    restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    statistics = await order_repo.get_order_statistics(
        restaurant_id=restaurant["id"],
        period=period
    )
    
    return statistics