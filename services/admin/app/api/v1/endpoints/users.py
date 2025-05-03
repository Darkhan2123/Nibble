from fastapi import APIRouter, Depends, Path, Query, HTTPException, status
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.auth import get_current_admin
from app.core.http_client import user_service_client, restaurant_service_client, driver_service_client
from app.core.kafka import publish_restaurant_approval, publish_driver_approval

router = APIRouter()

@router.get("/customers")
async def get_customers(
    search: Optional[str] = Query(None, description="Search by name or email"),
    limit: int = Query(50, ge=1, le=100, description="Number of customers to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get a list of customers.
    
    This endpoint allows an admin to retrieve a list of customers.
    """
    try:
        customers = await user_service_client.get(
            path="/api/v1/admin/customers",
            params={
                "search": search,
                "limit": limit,
                "offset": offset,
                "admin_token": current_admin.get("id")
            },
            token=current_admin.get("token")
        )
        
        return customers
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving customers: {str(e)}"
        )

@router.get("/customers/{user_id}")
async def get_customer(
    user_id: str = Path(..., description="The ID of the customer"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get a customer by ID.
    
    This endpoint allows an admin to retrieve a customer by their ID.
    """
    try:
        customer = await user_service_client.get(
            path=f"/api/v1/admin/customers/{user_id}",
            params={"admin_token": current_admin.get("id")},
            token=current_admin.get("token")
        )
        
        return customer
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving customer: {str(e)}"
        )

@router.get("/restaurants")
async def get_restaurants(
    search: Optional[str] = Query(None, description="Search by name"),
    is_approved: Optional[bool] = Query(None, description="Filter by approval status"),
    limit: int = Query(50, ge=1, le=100, description="Number of restaurants to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get a list of restaurants.
    
    This endpoint allows an admin to retrieve a list of restaurants.
    """
    try:
        restaurants = await restaurant_service_client.get(
            path="/api/v1/admin/restaurants",
            params={
                "search": search,
                "is_approved": is_approved,
                "limit": limit,
                "offset": offset,
                "admin_token": current_admin.get("id")
            },
            token=current_admin.get("token")
        )
        
        return restaurants
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving restaurants: {str(e)}"
        )

@router.get("/restaurants/{restaurant_id}")
async def get_restaurant(
    restaurant_id: str = Path(..., description="The ID of the restaurant"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get a restaurant by ID.
    
    This endpoint allows an admin to retrieve a restaurant by its ID.
    """
    try:
        restaurant = await restaurant_service_client.get(
            path=f"/api/v1/admin/restaurants/{restaurant_id}",
            params={"admin_token": current_admin.get("id")},
            token=current_admin.get("token")
        )
        
        return restaurant
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving restaurant: {str(e)}"
        )

@router.put("/restaurants/{restaurant_id}/approve")
async def approve_restaurant(
    restaurant_id: str = Path(..., description="The ID of the restaurant to approve"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Approve a restaurant.
    
    This endpoint allows an admin to approve a restaurant.
    """
    try:
        # Call restaurant service to approve the restaurant
        restaurant = await restaurant_service_client.put(
            path=f"/api/v1/admin/restaurants/{restaurant_id}/approve",
            json={"admin_id": current_admin.get("id")},
            token=current_admin.get("token")
        )
        
        # Publish event
        await publish_restaurant_approval(
            restaurant_id=restaurant_id,
            approved=True,
            admin_id=current_admin.get("id")
        )
        
        return restaurant
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving restaurant: {str(e)}"
        )

@router.put("/restaurants/{restaurant_id}/reject")
async def reject_restaurant(
    restaurant_id: str = Path(..., description="The ID of the restaurant to reject"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Reject a restaurant.
    
    This endpoint allows an admin to reject a restaurant.
    """
    try:
        # Call restaurant service to reject the restaurant
        restaurant = await restaurant_service_client.put(
            path=f"/api/v1/admin/restaurants/{restaurant_id}/reject",
            json={"admin_id": current_admin.get("id")},
            token=current_admin.get("token")
        )
        
        # Publish event
        await publish_restaurant_approval(
            restaurant_id=restaurant_id,
            approved=False,
            admin_id=current_admin.get("id")
        )
        
        return restaurant
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rejecting restaurant: {str(e)}"
        )

@router.get("/drivers")
async def get_drivers(
    search: Optional[str] = Query(None, description="Search by name"),
    is_approved: Optional[bool] = Query(None, description="Filter by approval status"),
    limit: int = Query(50, ge=1, le=100, description="Number of drivers to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get a list of drivers.
    
    This endpoint allows an admin to retrieve a list of drivers.
    """
    try:
        drivers = await driver_service_client.get(
            path="/api/v1/admin/drivers",
            params={
                "search": search,
                "is_approved": is_approved,
                "limit": limit,
                "offset": offset,
                "admin_token": current_admin.get("id")
            },
            token=current_admin.get("token")
        )
        
        return drivers
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving drivers: {str(e)}"
        )

@router.get("/drivers/{driver_id}")
async def get_driver(
    driver_id: str = Path(..., description="The ID of the driver"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get a driver by ID.
    
    This endpoint allows an admin to retrieve a driver by their ID.
    """
    try:
        driver = await driver_service_client.get(
            path=f"/api/v1/admin/drivers/{driver_id}",
            params={"admin_token": current_admin.get("id")},
            token=current_admin.get("token")
        )
        
        return driver
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving driver: {str(e)}"
        )

@router.put("/drivers/{driver_id}/approve")
async def approve_driver(
    driver_id: str = Path(..., description="The ID of the driver to approve"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Approve a driver.
    
    This endpoint allows an admin to approve a driver.
    """
    try:
        # Call driver service to approve the driver
        driver = await driver_service_client.put(
            path=f"/api/v1/admin/drivers/{driver_id}/approve",
            json={"admin_id": current_admin.get("id")},
            token=current_admin.get("token")
        )
        
        # Publish event
        await publish_driver_approval(
            driver_id=driver_id,
            approved=True,
            admin_id=current_admin.get("id")
        )
        
        return driver
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving driver: {str(e)}"
        )

@router.put("/drivers/{driver_id}/reject")
async def reject_driver(
    driver_id: str = Path(..., description="The ID of the driver to reject"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Reject a driver.
    
    This endpoint allows an admin to reject a driver.
    """
    try:
        # Call driver service to reject the driver
        driver = await driver_service_client.put(
            path=f"/api/v1/admin/drivers/{driver_id}/reject",
            json={"admin_id": current_admin.get("id")},
            token=current_admin.get("token")
        )
        
        # Publish event
        await publish_driver_approval(
            driver_id=driver_id,
            approved=False,
            admin_id=current_admin.get("id")
        )
        
        return driver
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rejecting driver: {str(e)}"
        )

@router.get("/user-activity/{user_id}")
async def get_user_activity(
    user_id: str = Path(..., description="The ID of the user"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get activity for a specific user.
    
    This endpoint allows an admin to view activity for a specific user.
    """
    # This would normally fetch from a system activity log
    # For now, we'll return mock data
    
    now = datetime.utcnow()
    
    activities = [
        {
            "id": str(i),
            "type": ["login", "order", "profile_update", "payment"][i % 4],
            "action": "performed",
            "timestamp": (now - timedelta(days=i, hours=i)).isoformat(),
            "details": {
                "ip_address": f"192.168.1.{i}",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        }
        for i in range(1, 11)
    ]
    
    return {
        "user_id": user_id,
        "activities": activities
    }