from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import Dict, List, Optional, Any
import logging

from app.core.auth import validate_token, has_role, driver_owner_or_admin
from app.models.driver import DriverRepository
from app.models.delivery import DeliveryRepository
from app.core.database import fetch_one
from app.schemas.delivery import (
    DeliveryResponse, DeliveryStatusUpdate, DeliveryRouteResponse,
    DeliveryListResponse, DeliverySummary, DeliveryLocationHistory,
    DeliveryLocationResponse, LocationPoint
)
from app.core.kafka import (
    publish_delivery_started, publish_delivery_completed,
    publish_delivery_failed, publish_order_status_updated,
    publish_delivery_location_updated
)
from app.core.redis import (
    assign_delivery_to_driver, get_driver_deliveries as get_driver_deliveries_redis,
    complete_delivery
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=DeliveryListResponse)
async def get_my_deliveries(
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Get deliveries for the current driver.
    """
    user_id = user_info["user_id"]
    delivery_repo = DeliveryRepository()
    
    # Validate status if provided
    valid_statuses = [
        "ready_for_pickup", "out_for_delivery", "delivered", "cancelled"
    ]
    if status and status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    deliveries = await delivery_repo.get_driver_deliveries(
        driver_id=user_id,
        status=status,
        limit=limit,
        offset=offset
    )
    
    # For now, we'll assume the total is the count of returned deliveries
    # In a real application, you would want to get the total count separately
    
    return {
        "items": deliveries,
        "total": len(deliveries),
        "limit": limit,
        "offset": offset
    }

@router.get("/active", response_model=List[DeliveryResponse])
async def get_my_active_deliveries(
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Get active deliveries for the current driver.
    """
    user_id = user_info["user_id"]
    
    # Try to get from Redis first (faster for real-time data)
    redis_deliveries = await get_driver_deliveries_redis(user_id)
    
    # If Redis has data, use it
    if redis_deliveries:
        return redis_deliveries
    
    # Otherwise fall back to database
    delivery_repo = DeliveryRepository()
    return await delivery_repo.get_active_deliveries(driver_id=user_id)

@router.get("/{order_id}", response_model=DeliveryResponse)
async def get_delivery(
    order_id: str,
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Get a specific delivery by order ID.
    """
    user_id = user_info["user_id"]
    delivery_repo = DeliveryRepository()
    
    delivery = await delivery_repo.get_delivery(
        order_id=order_id,
        driver_id=user_id
    )
    
    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found"
        )
    
    return delivery

@router.post("/{order_id}/status", response_model=DeliveryResponse)
async def update_delivery_status(
    order_id: str,
    update: DeliveryStatusUpdate,
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Update the status of a delivery.
    """
    user_id = user_info["user_id"]
    delivery_repo = DeliveryRepository()
    
    # Check if delivery exists and belongs to this driver
    existing_delivery = await delivery_repo.get_delivery(
        order_id=order_id,
        driver_id=user_id
    )
    
    if not existing_delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found"
        )
    
    try:
        # Get location data from update or use None
        latitude = None
        longitude = None
        if update.location:
            latitude = update.location.get("latitude")
            longitude = update.location.get("longitude")
        
        updated_delivery = await delivery_repo.update_delivery_status(
            order_id=order_id,
            driver_id=user_id,
            status=update.status,
            latitude=latitude,
            longitude=longitude,
            notes=update.notes
        )
        
        if not updated_delivery:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update delivery status"
            )
        
        # Publish event based on status
        if update.status == "out_for_delivery":
            await publish_delivery_started({
                "order_id": order_id,
                "driver_id": user_id,
                "status": update.status
            })
        elif update.status == "delivered":
            await publish_delivery_completed({
                "order_id": order_id,
                "driver_id": user_id,
                "status": update.status
            })
            
            # Remove from Redis active deliveries
            await complete_delivery(user_id, order_id)
            
        elif update.status == "cancelled":
            await publish_delivery_failed({
                "order_id": order_id,
                "driver_id": user_id,
                "status": update.status,
                "reason": update.notes or "Cancelled by driver"
            })
            
            # Remove from Redis active deliveries
            await complete_delivery(user_id, order_id)
            
        # Publish order status update
        await publish_order_status_updated(
            order_id=order_id,
            driver_id=user_id,
            status=update.status
        )
        
        logger.info(f"Delivery status updated: {order_id} to {update.status}")
        
        return updated_delivery
        
    except ValueError as e:
        logger.error(f"Error updating delivery status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error updating delivery status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/{order_id}/route", response_model=DeliveryRouteResponse)
async def get_delivery_route(
    order_id: str,
    avoid_tolls: bool = Query(False, description="Whether to avoid toll roads"),
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Calculate the delivery route for an order.
    """
    user_id = user_info["user_id"]
    delivery_repo = DeliveryRepository()
    
    # Check if delivery exists and belongs to this driver
    existing_delivery = await delivery_repo.get_delivery(
        order_id=order_id,
        driver_id=user_id
    )
    
    if not existing_delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found"
        )
    
    route = await delivery_repo.calculate_delivery_route(
        order_id=order_id,
        driver_id=user_id,
        avoid_tolls=avoid_tolls
    )
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not calculate delivery route"
        )
    
    return route

@router.get("/{order_id}/location-history", response_model=DeliveryLocationHistory)
async def get_delivery_location_history(
    order_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Get the location history for a delivery.
    This is useful for tracking the path a driver took during a delivery.
    """
    user_id = user_info["user_id"]
    delivery_repo = DeliveryRepository()
    
    # Check if delivery exists and belongs to this driver
    existing_delivery = await delivery_repo.get_delivery(
        order_id=order_id,
        driver_id=user_id
    )
    
    if not existing_delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found"
        )
    
    location_history = await delivery_repo.get_delivery_location_history(
        order_id=order_id,
        limit=limit,
        offset=offset
    )
    
    # Convert to response format
    locations = []
    for location in location_history:
        locations.append(
            LocationPoint(
                latitude=location["latitude"],
                longitude=location["longitude"],
                recorded_at=location["recorded_at"],
                status=location["status"]
            )
        )
    
    return {
        "order_id": order_id,
        "driver_id": user_id,
        "locations": locations,
        "total_locations": len(locations)
    }
    
@router.post("/{order_id}/location", response_model=DeliveryLocationResponse)
async def update_delivery_location(
    order_id: str,
    location: Dict[str, float],
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Update the current location of a delivery.
    This should be called periodically by the driver app to track the delivery progress.
    """
    user_id = user_info["user_id"]
    delivery_repo = DeliveryRepository()
    
    # Validate location data
    if "latitude" not in location or "longitude" not in location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location must include latitude and longitude"
        )
    
    latitude = location["latitude"]
    longitude = location["longitude"]
    
    if latitude < -90 or latitude > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude must be between -90 and 90"
        )
    
    if longitude < -180 or longitude > 180:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Longitude must be between -180 and 180"
        )
    
    # Check if delivery exists and belongs to this driver
    existing_delivery = await delivery_repo.get_delivery(
        order_id=order_id,
        driver_id=user_id
    )
    
    if not existing_delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found"
        )
    
    # Only allow location updates for active deliveries
    if existing_delivery["status"] not in ["ready_for_pickup", "out_for_delivery"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update location for delivery with status {existing_delivery['status']}"
        )
    
    # Update delivery location
    query = """
    UPDATE order_service.orders
    SET 
        current_location = ST_SetSRID(ST_MakePoint($1, $2), 4326),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = $3 AND driver_id = $4
    RETURNING id, status, updated_at
    """
    
    try:
        result = await fetch_one(query, longitude, latitude, order_id, user_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update delivery location"
            )
        
        # Send Kafka event for location update
        await publish_delivery_location_updated(
            order_id=order_id,
            driver_id=user_id,
            latitude=latitude,
            longitude=longitude,
            status=existing_delivery["status"]
        )
        
        return {
            "order_id": order_id,
            "status": result["status"],
            "current_location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "updated_at": result["updated_at"]
        }
    
    except Exception as e:
        logger.error(f"Error updating delivery location: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating delivery location"
        )