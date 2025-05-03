from fastapi import APIRouter, Depends, Query, HTTPException, Path, status
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from app.core.pinot import get_pinot_client, PinotClient
from app.core.auth import get_current_admin
from app.schemas.driver import (
    DriverPerformanceMetric, 
    DriverPerformanceResponse,
    DeliveryTimeDistribution,
    DailyStats,
    DriverDailyStatsResponse
)

router = APIRouter()

@router.get("/performance", response_model=DriverPerformanceResponse)
async def get_driver_performance(
    start_date: Optional[datetime] = Query(None, description="Start date for the analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for the analytics period"),
    limit: int = Query(10, description="Number of top drivers to return", ge=1, le=100),
    pinot: PinotClient = Depends(get_pinot_client),
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get performance metrics for all drivers.
    
    Returns metrics for the top drivers by delivery count including:
    - Total number of deliveries
    - Average delivery time
    - Average rating
    - Total tips received
    
    This endpoint requires admin privileges.
    """
    # Get driver performance metrics from Pinot
    driver_metrics = await pinot.get_driver_performance_metrics(
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    # Calculate time period for response
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=7)
    if not end_date:
        end_date = datetime.utcnow()
    
    # Format the response
    return {
        "metrics": driver_metrics,
        "total_drivers": len(driver_metrics),
        "time_period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    }

@router.get("/drivers/{driver_id}/performance", response_model=DriverPerformanceResponse)
async def get_specific_driver_performance(
    driver_id: str = Path(..., description="ID of the driver to get metrics for"),
    start_date: Optional[datetime] = Query(None, description="Start date for the analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for the analytics period"),
    pinot: PinotClient = Depends(get_pinot_client),
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get performance metrics for a specific driver.
    
    Returns detailed performance metrics for the specified driver including:
    - Total number of deliveries
    - Average delivery time
    - Average rating
    - Total tips received
    
    This endpoint requires admin privileges.
    """
    # Get driver performance metrics from Pinot
    driver_metrics = await pinot.get_driver_performance_metrics(
        start_date=start_date,
        end_date=end_date,
        driver_id=driver_id
    )
    
    # Return 404 if driver not found or has no deliveries
    if not driver_metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No delivery data found for driver {driver_id} in the specified time period"
        )
    
    # Calculate time period for response
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=7)
    if not end_date:
        end_date = datetime.utcnow()
    
    # Format the response
    return {
        "metrics": driver_metrics,
        "total_drivers": 1,
        "time_period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    }

@router.get("/delivery-times", response_model=DeliveryTimeDistribution)
async def get_driver_delivery_times(
    start_date: Optional[datetime] = Query(None, description="Start date for the analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for the analytics period"),
    pinot: PinotClient = Depends(get_pinot_client),
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get the distribution of delivery times across all drivers.
    
    Returns the count of deliveries in different time ranges:
    - Under 15 minutes
    - 15-30 minutes
    - 30-45 minutes
    - 45-60 minutes
    - Over 60 minutes
    
    This endpoint requires admin privileges.
    """
    # Get delivery time distribution from Pinot
    time_distribution = await pinot.get_driver_delivery_times_distribution(
        start_date=start_date,
        end_date=end_date
    )
    
    # Calculate total deliveries
    total_deliveries = sum(time_distribution.values())
    
    # Calculate time period for response
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=7)
    if not end_date:
        end_date = datetime.utcnow()
    
    # Format the response
    return {
        "time_ranges": time_distribution,
        "total_deliveries": total_deliveries,
        "time_period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    }

@router.get("/drivers/{driver_id}/delivery-times", response_model=DeliveryTimeDistribution)
async def get_specific_driver_delivery_times(
    driver_id: str = Path(..., description="ID of the driver to get delivery times for"),
    start_date: Optional[datetime] = Query(None, description="Start date for the analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for the analytics period"),
    pinot: PinotClient = Depends(get_pinot_client),
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get the distribution of delivery times for a specific driver.
    
    Returns the count of deliveries in different time ranges:
    - Under 15 minutes
    - 15-30 minutes
    - 30-45 minutes
    - 45-60 minutes
    - Over 60 minutes
    
    This endpoint requires admin privileges.
    """
    # Get delivery time distribution from Pinot
    time_distribution = await pinot.get_driver_delivery_times_distribution(
        start_date=start_date,
        end_date=end_date,
        driver_id=driver_id
    )
    
    # Calculate total deliveries
    total_deliveries = sum(time_distribution.values())
    
    # Return 404 if driver not found or has no deliveries
    if total_deliveries == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No delivery data found for driver {driver_id} in the specified time period"
        )
    
    # Calculate time period for response
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=7)
    if not end_date:
        end_date = datetime.utcnow()
    
    # Format the response
    return {
        "time_ranges": time_distribution,
        "total_deliveries": total_deliveries,
        "time_period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    }

@router.get("/drivers/{driver_id}/daily-stats", response_model=DriverDailyStatsResponse)
async def get_driver_daily_stats(
    driver_id: str = Path(..., description="ID of the driver to get daily stats for"),
    start_date: Optional[datetime] = Query(None, description="Start date for the analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for the analytics period"),
    pinot: PinotClient = Depends(get_pinot_client),
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get daily statistics for a specific driver.
    
    Returns daily metrics for the specified driver including:
    - Total number of deliveries per day
    - Average delivery time per day
    - Total tips received per day
    
    This endpoint requires admin privileges.
    """
    # Get driver daily stats from Pinot
    daily_stats = await pinot.get_driver_daily_stats(
        start_date=start_date,
        end_date=end_date,
        driver_id=driver_id
    )
    
    # Return 404 if driver not found or has no deliveries
    if not daily_stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No delivery data found for driver {driver_id} in the specified time period"
        )
    
    # Calculate time period for response
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=7)
    if not end_date:
        end_date = datetime.utcnow()
    
    # Format the response
    return {
        "driver_id": driver_id,
        "daily_stats": daily_stats,
        "time_period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    }