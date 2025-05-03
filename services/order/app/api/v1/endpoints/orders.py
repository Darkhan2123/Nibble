from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import asyncpg
import uuid
from datetime import datetime, timedelta

from app.core.http_client import get_driver_location, get_restaurant_location, get_delivery_route

from app.core.auth import get_current_user, get_current_admin, get_current_restaurant, get_current_driver
from app.models.order import OrderRepository
from app.schemas.order import (
    OrderCreateRequest, OrderResponse, OrderStatusUpdateRequest, 
    OrderDriverAssignRequest, OrderEstimatedTimeUpdateRequest,
    OrderTipUpdateRequest, OrderRatingRequest, OrderStatusHistoryResponse,
    OrderListResponse, OrderTrackingResponse
)
from app.core.redis import (
    update_order_status, add_to_processing_queue, 
    get_order_status, get_order_tracking_data, 
    update_order_tracking_data, get_driver_path_for_order
)
from app.core.kafka import (
    publish_order_created, publish_order_updated, publish_order_status_changed,
    publish_order_cancelled, publish_customer_notification, 
    publish_restaurant_notification, publish_driver_notification
)

logger = logging.getLogger(__name__)
router = APIRouter()
order_repository = OrderRepository()

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new order.
    
    This endpoint allows a user to create a new order. The order will be created with
    status 'placed' and payment status 'pending'. The user must be authenticated.
    """
    try:
        # Create order in database
        order = await order_repository.create_order(
            customer_id=current_user["id"],
            restaurant_id=order_data.restaurant_id,
            address_id=order_data.address_id,
            items=[item.dict() for item in order_data.items],
            subtotal=order_data.subtotal,
            delivery_fee=order_data.delivery_fee,
            payment_method=order_data.payment_method,
            special_instructions=order_data.special_instructions,
            promo_discount=order_data.promo_discount or 0
        )
        
        # Update real-time status
        await update_order_status(
            order_id=order["id"],
            status="placed",
            data={
                "customer_id": current_user["id"],
                "restaurant_id": order_data.restaurant_id,
                "payment_status": "pending",
                "order_number": order["order_number"]
            }
        )
        
        # Queue for processing
        await add_to_processing_queue(
            order_id=order["id"],
            data={
                "status": "payment_pending",
                "customer_id": current_user["id"],
                "payment_method": order_data.payment_method,
                "total_amount": order["total_amount"]
            }
        )
        
        # Publish events
        await publish_order_created(order)
        
        # Notify restaurant
        restaurant_message = f"New order #{order['order_number']} received and awaiting payment confirmation."
        await publish_restaurant_notification(
            restaurant_id=order_data.restaurant_id,
            message=restaurant_message,
            notification_type="new_order"
        )
        
        return order
        
    except asyncpg.exceptions.ForeignKeyViolationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid restaurant ID or address ID"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the order"
        )

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    order_id: str = Path(..., description="The ID of the order to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get an order by ID.
    
    This endpoint allows a user to retrieve an order by its ID. The user must be the
    customer who placed the order, the restaurant that received the order, the driver
    assigned to the order, or an admin.
    """
    order = await order_repository.get_order_by_id(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check permissions
    user_id = current_user["id"]
    user_role = current_user["role"]
    
    is_customer = user_id == order["customer_id"]
    is_restaurant = user_id == order["restaurant_id"]
    is_driver = order.get("driver_id") and user_id == order["driver_id"]
    is_admin = user_role == "admin"
    
    if not (is_customer or is_restaurant or is_driver or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this order"
        )
    
    return order

@router.get("/number/{order_number}", response_model=OrderResponse)
async def get_order_by_number(
    order_number: str = Path(..., description="The order number to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get an order by its order number.
    
    This endpoint allows a user to retrieve an order by its order number. The user must be the
    customer who placed the order, the restaurant that received the order, the driver
    assigned to the order, or an admin.
    """
    order = await order_repository.get_order_by_number(order_number)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check permissions
    user_id = current_user["id"]
    user_role = current_user["role"]
    
    is_customer = user_id == order["customer_id"]
    is_restaurant = user_id == order["restaurant_id"]
    is_driver = order.get("driver_id") and user_id == order["driver_id"]
    is_admin = user_role == "admin"
    
    if not (is_customer or is_restaurant or is_driver or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this order"
        )
    
    return order

@router.get("/customer/me", response_model=OrderListResponse)
async def get_my_orders(
    status: Optional[str] = Query(None, description="Filter by order status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get orders for the current customer.
    
    This endpoint allows a customer to retrieve their orders. The orders can be
    filtered by status.
    """
    offset = (page - 1) * limit
    orders = await order_repository.get_orders_by_customer(
        customer_id=current_user["id"],
        status=status,
        limit=limit,
        offset=offset
    )
    
    # Get total count for pagination
    # In a real implementation, we'd use a COUNT query
    # For simplicity, we'll just use the number of orders returned
    total = len(orders)
    
    return {
        "orders": orders,
        "total": total,
        "page": page,
        "limit": limit
    }

@router.get("/restaurant/{restaurant_id}", response_model=OrderListResponse)
async def get_restaurant_orders(
    restaurant_id: str = Path(..., description="The ID of the restaurant"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_restaurant)
):
    """
    Get orders for a restaurant.
    
    This endpoint allows a restaurant to retrieve its orders. The orders can be
    filtered by status.
    """
    # Check if the current user is the restaurant owner
    if current_user["id"] != restaurant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view orders for this restaurant"
        )
    
    offset = (page - 1) * limit
    orders = await order_repository.get_orders_by_restaurant(
        restaurant_id=restaurant_id,
        status=status,
        limit=limit,
        offset=offset
    )
    
    # Get total count for pagination
    # In a real implementation, we'd use a COUNT query
    # For simplicity, we'll just use the number of orders returned
    total = len(orders)
    
    return {
        "orders": orders,
        "total": total,
        "page": page,
        "limit": limit
    }

@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_status: OrderStatusUpdateRequest,
    order_id: str = Path(..., description="The ID of the order to update"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update an order's status.
    
    This endpoint allows updating the status of an order. The user must have
    permission to update the order's status based on their role.
    """
    # Get the order first
    order = await order_repository.get_order_by_id(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check permissions
    user_id = current_user["id"]
    user_role = current_user["role"]
    
    # Permission rules:
    # - Customer can cancel their own orders
    # - Restaurant can update status for their orders
    # - Driver can update status for assigned orders
    # - Admin can update any order
    is_customer = user_id == order["customer_id"]
    is_restaurant = user_id == order["restaurant_id"]
    is_driver = order.get("driver_id") and user_id == order["driver_id"]
    is_admin = user_role == "admin"
    
    # Status-specific permission checks
    new_status = order_status.status
    
    if new_status == "cancelled":
        # Only customer, restaurant, or admin can cancel
        if not (is_customer or is_restaurant or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to cancel this order"
            )
    
    elif new_status in ["confirmed", "preparing", "ready_for_pickup"]:
        # Only restaurant or admin can update to these statuses
        if not (is_restaurant or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this order's status"
            )
    
    elif new_status in ["out_for_delivery", "delivered"]:
        # Only driver or admin can update to these statuses
        if not (is_driver or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this order's status"
            )
    
    else:
        # For any other status, only admin can update
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this order's status"
            )
    
    try:
        # Update order status
        updated_order = await order_repository.update_order_status(
            order_id=order_id,
            status=new_status,
            updated_by=user_id,
            notes=order_status.notes
        )
        
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update order status"
            )
        
        # Update real-time status
        await update_order_status(
            order_id=order_id,
            status=new_status,
            data={"updated_by": user_id}
        )
        
        # Publish events
        await publish_order_status_changed(order_id, new_status)
        await publish_order_updated(updated_order)
        
        # Send notifications
        customer_message = ""
        restaurant_message = ""
        
        if new_status == "cancelled":
            customer_message = f"Your order #{updated_order['order_number']} has been cancelled."
            restaurant_message = f"Order #{updated_order['order_number']} has been cancelled."
        
        elif new_status == "confirmed":
            customer_message = f"Your order #{updated_order['order_number']} has been confirmed and is being prepared."
            
        elif new_status == "preparing":
            customer_message = f"Your order #{updated_order['order_number']} is now being prepared."
            
        elif new_status == "ready_for_pickup":
            customer_message = f"Your order #{updated_order['order_number']} is ready for pickup by a driver."
            
        elif new_status == "out_for_delivery":
            customer_message = f"Your order #{updated_order['order_number']} is out for delivery."
            restaurant_message = f"Order #{updated_order['order_number']} is out for delivery."
            
        elif new_status == "delivered":
            customer_message = f"Your order #{updated_order['order_number']} has been delivered. Enjoy your meal!"
            restaurant_message = f"Order #{updated_order['order_number']} has been delivered."
        
        # Send notifications
        if customer_message:
            await publish_customer_notification(
                user_id=updated_order["customer_id"],
                message=customer_message,
                notification_type="order_update"
            )
        
        if restaurant_message:
            await publish_restaurant_notification(
                restaurant_id=updated_order["restaurant_id"],
                message=restaurant_message,
                notification_type="order_update"
            )
        
        return updated_order
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the order status"
        )

@router.put("/{order_id}/driver", response_model=OrderResponse)
async def assign_driver(
    driver_data: OrderDriverAssignRequest,
    order_id: str = Path(..., description="The ID of the order to update"),
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Assign a driver to an order.
    
    This endpoint allows an admin to assign a driver to an order.
    """
    try:
        updated_order = await order_repository.update_driver_assignment(
            order_id=order_id,
            driver_id=driver_data.driver_id
        )
        
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found or not ready for pickup"
            )
            
        # Notify driver
        await publish_driver_notification(
            driver_id=driver_data.driver_id,
            message=f"You have been assigned to order #{updated_order['order_number']}.",
            notification_type="order_assignment"
        )
        
        return updated_order
        
    except Exception as e:
        logger.error(f"Error assigning driver: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while assigning the driver"
        )

@router.put("/{order_id}/estimated-time", response_model=OrderResponse)
async def update_estimated_time(
    time_data: OrderEstimatedTimeUpdateRequest,
    order_id: str = Path(..., description="The ID of the order to update"),
    current_user: Dict[str, Any] = Depends(get_current_driver)
):
    """
    Update the estimated delivery time for an order.
    
    This endpoint allows a driver to update the estimated delivery time for an order.
    """
    # Get the order first
    order = await order_repository.get_order_by_id(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if the current user is the assigned driver
    if current_user["id"] != order.get("driver_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this order"
        )
    
    try:
        updated_order = await order_repository.update_estimated_delivery_time(
            order_id=order_id,
            estimated_time=time_data.estimated_delivery_time
        )
        
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update estimated delivery time"
            )
        
        # Update real-time status
        await update_order_status(
            order_id=order_id,
            status=updated_order["status"],
            data={"estimated_delivery_time": time_data.estimated_delivery_time.isoformat()}
        )
        
        # Notify customer
        await publish_customer_notification(
            user_id=updated_order["customer_id"],
            message=f"The estimated delivery time for your order #{updated_order['order_number']} has been updated to {time_data.estimated_delivery_time.strftime('%H:%M')}.",
            notification_type="order_update"
        )
        
        return updated_order
        
    except Exception as e:
        logger.error(f"Error updating estimated delivery time: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the estimated delivery time"
        )

@router.put("/{order_id}/tip", response_model=OrderResponse)
async def add_tip(
    tip_data: OrderTipUpdateRequest,
    order_id: str = Path(..., description="The ID of the order to update"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Add or update a tip for an order.
    
    This endpoint allows a customer to add or update a tip for their order.
    """
    # Get the order first
    order = await order_repository.get_order_by_id(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if the current user is the customer
    if current_user["id"] != order["customer_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add tips to your own orders"
        )
    
    try:
        updated_order = await order_repository.add_tip(
            order_id=order_id,
            tip_amount=tip_data.tip_amount
        )
        
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add tip"
            )
        
        # If there's a driver, notify them
        if updated_order.get("driver_id"):
            await publish_driver_notification(
                driver_id=updated_order["driver_id"],
                message=f"You received a ${tip_data.tip_amount:.2f} tip for order #{updated_order['order_number']}.",
                notification_type="tip_received"
            )
        
        return updated_order
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding tip: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while adding the tip"
        )

@router.post("/{order_id}/rating", status_code=status.HTTP_201_CREATED)
async def rate_order(
    rating_data: OrderRatingRequest,
    order_id: str = Path(..., description="The ID of the order to rate"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Rate an order.
    
    This endpoint allows a customer to rate their completed order.
    """
    try:
        rating = await order_repository.add_rating(
            order_id=order_id,
            customer_id=current_user["id"],
            food_rating=rating_data.food_rating,
            delivery_rating=rating_data.delivery_rating,
            review_text=rating_data.review_text
        )
        
        return {
            "message": "Rating submitted successfully",
            "rating": rating
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error rating order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while rating the order"
        )

@router.get("/{order_id}/history", response_model=List[OrderStatusHistoryResponse])
async def get_order_history(
    order_id: str = Path(..., description="The ID of the order"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get an order's status history.
    
    This endpoint allows retrieving the status history of an order. The user must have
    permission to view the order.
    """
    # Get the order first
    order = await order_repository.get_order_by_id(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check permissions
    user_id = current_user["id"]
    user_role = current_user["role"]
    
    is_customer = user_id == order["customer_id"]
    is_restaurant = user_id == order["restaurant_id"]
    is_driver = order.get("driver_id") and user_id == order["driver_id"]
    is_admin = user_role == "admin"
    
    if not (is_customer or is_restaurant or is_driver or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this order's history"
        )
    
    history = await order_repository.get_order_status_history(order_id)
    return history

@router.get("/{order_id}/tracking", response_model=OrderTrackingResponse)
async def track_order(
    order_id: str = Path(..., description="The ID of the order to track"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get real-time tracking information for an order.
    
    This endpoint provides real-time tracking information for an order, including
    current status, driver location, and estimated delivery time.
    """
    # Get the order first
    order = await order_repository.get_order_by_id(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check permissions
    user_id = current_user["id"]
    user_role = current_user["role"]
    
    is_customer = user_id == order["customer_id"]
    is_restaurant = user_id == order["restaurant_id"]
    is_driver = order.get("driver_id") and user_id == order["driver_id"]
    is_admin = user_role == "admin"
    
    if not (is_customer or is_restaurant or is_driver or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to track this order"
        )
    
    # Get real-time status from Redis
    redis_status = await get_order_status(order_id)
    tracking_data = await get_order_tracking_data(order_id)
    
    # Status from Redis if available, otherwise from DB
    current_status = redis_status.get("status") if redis_status else order["status"]
    
    # Initialize response
    response = {
        "order_id": order_id,
        "order_number": order["order_number"],
        "customer_id": order["customer_id"],
        "restaurant_id": order["restaurant_id"],
        "status": current_status,
        "delivery_address_id": order["delivery_address_id"],
        "driver_id": order.get("driver_id"),
        "driver_location": None,
        "estimated_delivery_time": order.get("estimated_delivery_time"),
        "restaurant_location": None,
        "last_status_update": datetime.fromisoformat(redis_status.get("updated_at")) if redis_status and "updated_at" in redis_status else order["updated_at"],
        "is_location_available": False,
        "eta_minutes": None,
        "route_polyline": None
    }
    
    # For active deliveries with drivers, get more information
    if order.get("driver_id") and current_status in ["ready_for_pickup", "out_for_delivery"]:
        # Get driver location
        if tracking_data and "driver_location" in tracking_data:
            response["driver_location"] = tracking_data["driver_location"]
            response["is_location_available"] = True
        else:
            # Try to get from driver service
            driver_location = await get_driver_location(order["driver_id"])
            if driver_location:
                response["driver_location"] = driver_location
                response["is_location_available"] = True
                
                # Update tracking data in Redis
                await update_order_tracking_data(
                    order_id=order_id,
                    data={"driver_location": driver_location}
                )
        
        # Get restaurant location if in "ready_for_pickup" status
        if current_status == "ready_for_pickup":
            if tracking_data and "restaurant_location" in tracking_data:
                response["restaurant_location"] = tracking_data["restaurant_location"]
            else:
                # Try to get from restaurant service
                restaurant_location = await get_restaurant_location(order["restaurant_id"])
                if restaurant_location:
                    response["restaurant_location"] = restaurant_location
                    
                    # Update tracking data in Redis
                    if tracking_data:
                        tracking_data["restaurant_location"] = restaurant_location
                        await update_order_tracking_data(order_id, tracking_data)
                    else:
                        await update_order_tracking_data(
                            order_id=order_id,
                            data={"restaurant_location": restaurant_location}
                        )
                        
        # Calculate ETA if we have sufficient data
        if response["driver_location"] and (current_status == "out_for_delivery" or response["restaurant_location"]):
            # Try to get route from driver service
            route_data = await get_delivery_route(order_id)
            
            if route_data:
                # Extract ETA from route data
                if current_status == "ready_for_pickup":
                    response["eta_minutes"] = round(route_data.get("estimated_pickup_time", 0))
                else:  # out_for_delivery
                    response["eta_minutes"] = round(route_data.get("estimated_delivery_time", 0))
                
                # Extract polyline for map display
                if current_status == "ready_for_pickup":
                    response["route_polyline"] = route_data.get("route_to_restaurant", {}).get("polyline")
                else:  # out_for_delivery
                    response["route_polyline"] = route_data.get("route_to_customer", {}).get("polyline")
            else:
                # Fallback: very simple ETA calculation
                if order.get("estimated_delivery_time"):
                    eta = order["estimated_delivery_time"] - datetime.utcnow()
                    if eta > timedelta(0):  # Only if it's in the future
                        response["eta_minutes"] = round(eta.total_seconds() / 60)
    
    return response

@router.get("/{order_id}/driver-path", response_model=List[Dict[str, Any]])
async def get_driver_path(
    order_id: str = Path(..., description="The ID of the order"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of points to return"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the path history of a driver for an order.
    
    This endpoint returns the location history of a driver for an order,
    useful for displaying the path taken during delivery.
    """
    # Get the order first
    order = await order_repository.get_order_by_id(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check permissions
    user_id = current_user["id"]
    user_role = current_user["role"]
    
    is_customer = user_id == order["customer_id"]
    is_restaurant = user_id == order["restaurant_id"]
    is_driver = order.get("driver_id") and user_id == order["driver_id"]
    is_admin = user_role == "admin"
    
    if not (is_customer or is_restaurant or is_driver or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this order's driver path"
        )
    
    # Get path from Redis
    path = await get_driver_path_for_order(order_id, limit)
    
    if not path:
        return []
    
    return path