from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, List, Optional, Any
import logging

from app.core.auth import validate_token, has_role, has_any_role, driver_owner_or_admin
from app.models.driver import DriverRepository
from app.schemas.driver import (
    DriverProfileCreate, DriverProfileUpdate, DriverProfileResponse,
    DriverLocationUpdate, DriverAvailabilityUpdate,
    DriverStatisticsResponse, DriverEarningsResponse, NearbyDriversResponse
)
from app.core.kafka import (
    publish_driver_registered, publish_driver_updated,
    publish_driver_location_updated, publish_driver_availability_changed
)
from app.core.redis import (
    update_driver_location, get_driver_location, get_nearby_drivers as get_nearby_drivers_redis
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=DriverProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_driver_profile(
    profile: DriverProfileCreate,
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Create a new driver profile. Only users with the 'driver' role can do this.
    """
    user_id = user_info["user_id"]
    driver_repo = DriverRepository()
    
    # Check if driver profile already exists
    existing_profile = await driver_repo.get_driver_by_id(user_id)
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Driver profile already exists for this user"
        )
    
    try:
        new_profile = await driver_repo.create_driver_profile(
            user_id=user_id,
            vehicle_type=profile.vehicle_type,
            vehicle_make=profile.vehicle_make,
            vehicle_model=profile.vehicle_model,
            vehicle_year=profile.vehicle_year,
            license_plate=profile.license_plate,
            driver_license_number=profile.driver_license_number,
            driver_license_expiry=profile.driver_license_expiry,
            insurance_number=profile.insurance_number,
            insurance_expiry=profile.insurance_expiry,
            banking_info=profile.banking_info
        )
        
        # Publish driver registered event
        await publish_driver_registered({
            "driver_id": user_id,
            "vehicle_type": profile.vehicle_type
        })
        
        logger.info(f"Driver profile created for user ID: {user_id}")
        
        return new_profile
        
    except ValueError as e:
        logger.error(f"Error creating driver profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating driver profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/me", response_model=DriverProfileResponse)
async def get_my_driver_profile(
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Get the current user's driver profile.
    """
    user_id = user_info["user_id"]
    driver_repo = DriverRepository()
    
    profile = await driver_repo.get_driver_by_id(user_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    # Add location data if available
    location_data = await get_driver_location(user_id)
    if location_data:
        profile["current_location"] = {
            "latitude": location_data["latitude"],
            "longitude": location_data["longitude"]
        }
    
    return profile

@router.put("/me", response_model=DriverProfileResponse)
async def update_my_driver_profile(
    profile: DriverProfileUpdate,
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Update the current user's driver profile.
    """
    user_id = user_info["user_id"]
    driver_repo = DriverRepository()
    
    # Check if profile exists
    existing_profile = await driver_repo.get_driver_by_id(user_id)
    if not existing_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    try:
        updated_profile = await driver_repo.update_driver_profile(
            user_id=user_id,
            update_data=profile.dict(exclude_unset=True)
        )
        
        # Publish driver updated event
        await publish_driver_updated({
            "driver_id": user_id,
            "vehicle_type": updated_profile.get("vehicle_type"),
            "is_available": updated_profile.get("is_available")
        })
        
        # If availability changed, publish that event too
        if profile.is_available is not None and profile.is_available != existing_profile.get("is_available"):
            await publish_driver_availability_changed(
                driver_id=user_id,
                is_available=profile.is_available
            )
        
        logger.info(f"Driver profile updated for user ID: {user_id}")
        
        return updated_profile
        
    except ValueError as e:
        logger.error(f"Error updating driver profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error updating driver profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.post("/me/location", response_model=DriverProfileResponse)
async def update_my_location(
    location: DriverLocationUpdate,
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Update the current user's location.
    """
    user_id = user_info["user_id"]
    driver_repo = DriverRepository()
    
    # Check if profile exists
    existing_profile = await driver_repo.get_driver_by_id(user_id)
    if not existing_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    try:
        # Update in PostgreSQL for persistence
        updated_profile = await driver_repo.update_driver_location(
            user_id=user_id,
            latitude=location.latitude,
            longitude=location.longitude,
            is_available=location.is_available
        )
        
        # Update in Redis for real-time access
        await update_driver_location(
            driver_id=user_id,
            latitude=location.latitude,
            longitude=location.longitude,
            is_available=location.is_available if location.is_available is not None else existing_profile.get("is_available", False)
        )
        
        # Publish location updated event
        await publish_driver_location_updated(
            driver_id=user_id,
            latitude=location.latitude,
            longitude=location.longitude,
            is_available=location.is_available if location.is_available is not None else existing_profile.get("is_available", False)
        )
        
        logger.info(f"Driver location updated for user ID: {user_id}")
        
        # Add location data to response
        updated_profile["current_location"] = {
            "latitude": location.latitude,
            "longitude": location.longitude
        }
        
        return updated_profile
        
    except Exception as e:
        logger.error(f"Unexpected error updating driver location: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.post("/me/availability", response_model=DriverProfileResponse)
async def update_my_availability(
    availability: DriverAvailabilityUpdate,
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Update the current user's availability status.
    """
    user_id = user_info["user_id"]
    driver_repo = DriverRepository()
    
    # Check if profile exists
    existing_profile = await driver_repo.get_driver_by_id(user_id)
    if not existing_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    try:
        updated_profile = await driver_repo.update_driver_availability(
            user_id=user_id,
            is_available=availability.is_available
        )
        
        # Get current location from Redis
        location_data = await get_driver_location(user_id)
        if location_data:
            # Update in Redis with new availability
            await update_driver_location(
                driver_id=user_id,
                latitude=location_data["latitude"],
                longitude=location_data["longitude"],
                is_available=availability.is_available
            )
        
        # Publish availability changed event
        await publish_driver_availability_changed(
            driver_id=user_id,
            is_available=availability.is_available
        )
        
        logger.info(f"Driver availability updated for user ID: {user_id}")
        
        # Add location data to response if available
        if location_data:
            updated_profile["current_location"] = {
                "latitude": location_data["latitude"],
                "longitude": location_data["longitude"]
            }
        
        return updated_profile
        
    except Exception as e:
        logger.error(f"Unexpected error updating driver availability: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/me/statistics", response_model=DriverStatisticsResponse)
async def get_my_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Get statistics for the current driver.
    """
    user_id = user_info["user_id"]
    driver_repo = DriverRepository()
    
    # Check if profile exists
    existing_profile = await driver_repo.get_driver_by_id(user_id)
    if not existing_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    statistics = await driver_repo.get_driver_statistics(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return statistics

@router.get("/me/earnings", response_model=List[DriverEarningsResponse])
async def get_my_earnings(
    start_date: str,
    end_date: str,
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Get earnings breakdown for the current driver within a specified date range.
    """
    user_id = user_info["user_id"]
    driver_repo = DriverRepository()
    
    # Check if profile exists
    existing_profile = await driver_repo.get_driver_by_id(user_id)
    if not existing_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    earnings = await driver_repo.get_driver_earnings(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return earnings

@router.get("/nearby", response_model=NearbyDriversResponse)
async def get_nearby_drivers(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius: int = Query(5000, ge=100, le=20000),  # radius in meters, default 5km
    limit: int = Query(10, ge=1, le=100),
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Get nearby available drivers within a specified radius.
    """
    # Try to get from Redis first (faster for real-time data)
    nearby_drivers = await get_nearby_drivers_redis(
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        limit=limit
    )
    
    # If no results from Redis, try database
    if not nearby_drivers:
        driver_repo = DriverRepository()
        nearby_drivers = await driver_repo.get_nearby_drivers(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            limit=limit
        )
    
    return {
        "drivers": nearby_drivers,
        "count": len(nearby_drivers)
    }

@router.get("/{driver_id}", response_model=DriverProfileResponse)
async def get_driver_profile(
    driver_id: str,
    user_info: Dict[str, Any] = Depends(has_any_role(["admin", "restaurant"]))
):
    """
    Get a driver profile by ID. Only admins and restaurants can access this.
    """
    driver_repo = DriverRepository()
    
    profile = await driver_repo.get_driver_by_id(driver_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    # Add location data if available
    location_data = await get_driver_location(driver_id)
    if location_data:
        profile["current_location"] = {
            "latitude": location_data["latitude"],
            "longitude": location_data["longitude"]
        }
    
    return profile