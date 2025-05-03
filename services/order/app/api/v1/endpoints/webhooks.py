from fastapi import APIRouter, Depends, HTTPException, Request, status, Body
from typing import Dict, Any, Optional
import logging

from app.core.auth import validate_service_key
from app.core.redis import update_driver_location_for_order, update_order_tracking_data
from app.models.order import OrderRepository

logger = logging.getLogger(__name__)
router = APIRouter()
order_repository = OrderRepository()

@router.post("/driver-location", status_code=status.HTTP_200_OK)
async def update_driver_location(
    data: Dict[str, Any] = Body(...),
    _: Dict[str, Any] = Depends(validate_service_key)
):
    """
    Webhook endpoint for driver location updates.
    
    This endpoint receives location updates from the driver service
    and updates the real-time tracking data for the corresponding orders.
    """
    try:
        # Validate required fields
        required_fields = ["driver_id", "latitude", "longitude"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
        
        driver_id = data["driver_id"]
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])
        order_id = data.get("order_id")
        
        # If order_id is provided, update for specific order
        if order_id:
            await update_driver_location_for_order(
                order_id=order_id,
                latitude=latitude,
                longitude=longitude
            )
            logger.info(f"Updated location for driver {driver_id} on order {order_id}")
            return {"status": "success", "message": "Location updated for specific order"}
        
        # Otherwise, find driver's active orders and update all
        active_orders = await order_repository.get_active_orders_by_driver(driver_id)
        
        if not active_orders:
            logger.info(f"No active orders found for driver {driver_id}")
            return {"status": "success", "message": "No active orders found for driver"}
        
        # Update location for all active orders
        for order in active_orders:
            await update_driver_location_for_order(
                order_id=order["id"],
                latitude=latitude,
                longitude=longitude
            )
        
        logger.info(f"Updated location for driver {driver_id} on {len(active_orders)} orders")
        return {
            "status": "success",
            "message": f"Location updated for {len(active_orders)} orders",
            "order_count": len(active_orders)
        }
        
    except ValueError as e:
        logger.error(f"Invalid location data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid location data"
        )
    except Exception as e:
        logger.error(f"Error processing location update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the location update"
        )

@router.post("/delivery-status", status_code=status.HTTP_200_OK)
async def update_delivery_status(
    data: Dict[str, Any] = Body(...),
    _: Dict[str, Any] = Depends(validate_service_key)
):
    """
    Webhook endpoint for delivery status updates.
    
    This endpoint receives status updates from the driver service
    and updates the real-time tracking data for the corresponding orders.
    """
    try:
        # Validate required fields
        required_fields = ["order_id", "status"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
        
        order_id = data["order_id"]
        status = data["status"]
        driver_id = data.get("driver_id")
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        
        # Update order status in database
        updated_order = await order_repository.update_order_status(
            order_id=order_id,
            status=status,
            updated_by=driver_id or "system",
            notes=data.get("notes")
        )
        
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found or status update failed"
            )
        
        # Update tracking data
        tracking_data = {
            "status": status,
            "last_status_update": updated_order["updated_at"].isoformat()
        }
        
        # Add location if provided
        if latitude is not None and longitude is not None:
            tracking_data["driver_location"] = {
                "latitude": float(latitude),
                "longitude": float(longitude)
            }
            
            # Also update location history
            await update_driver_location_for_order(
                order_id=order_id,
                latitude=float(latitude),
                longitude=float(longitude)
            )
        
        # Add estimated delivery time if provided
        if "estimated_delivery_time" in data:
            tracking_data["estimated_delivery_time"] = data["estimated_delivery_time"]
        
        await update_order_tracking_data(order_id, tracking_data)
        
        logger.info(f"Updated delivery status for order {order_id} to {status}")
        return {"status": "success", "message": "Delivery status updated"}
        
    except Exception as e:
        logger.error(f"Error processing status update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the status update"
        )