from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
import logging
import aiohttp
from app.core.auth import validate_token
from app.models.address import AddressRepository
from app.schemas.address import MapResponse, DeliveryTimeEstimateResponse
from app.core.maps import estimate_delivery_time, generate_map_html
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

@router.get("/nearby", summary="Get nearby restaurants")
async def get_nearby_restaurants(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude of the location to search around"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude of the location to search around"),
    radius: int = Query(2000, ge=100, le=50000, description="Search radius in meters"),
    cuisine_type: Optional[List[str]] = Query(None, description="Filter by cuisine type"),
    price_range: Optional[List[int]] = Query(None, description="Filter by price range (1-4)"),
    sort_by: str = Query("distance", description="Sort by distance, rating, or price"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Get a list of restaurants near a specified location.
    """
    # Forward the request to the restaurant service
    try:
        restaurant_service_url = "http://restaurant:8002/api/v1/restaurants/search"
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius,
            "sort_by": sort_by,
            "limit": limit,
            "offset": offset
        }
        
        if cuisine_type:
            params["cuisine_type"] = cuisine_type
            
        if price_range:
            params["price_range"] = price_range
            
        headers = {
            "Authorization": f"Bearer {token.get('raw_token', '')}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(restaurant_service_url, params=params, headers=headers) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"Restaurant service error: {error}")
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to retrieve nearby restaurants"
                    )
                
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to restaurant service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Restaurant service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_nearby_restaurants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/{restaurant_id}/menu", summary="Get restaurant menu")
async def get_restaurant_menu(
    restaurant_id: str,
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Get the menu for a specific restaurant.
    """
    # Forward the request to the restaurant service
    try:
        restaurant_service_url = f"http://restaurant:8002/api/v1/restaurants/{restaurant_id}/menu"
        
        headers = {
            "Authorization": f"Bearer {token.get('raw_token', '')}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(restaurant_service_url, headers=headers) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"Restaurant service error: {error}")
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to retrieve restaurant menu"
                    )
                
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to restaurant service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Restaurant service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_restaurant_menu: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/{restaurant_id}/delivery-map", response_model=MapResponse)
async def get_delivery_map(
    restaurant_id: str,
    address_id: str,
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Generate a map showing the delivery route from a restaurant to a user's address.
    """
    address_repo = AddressRepository()
    
    # Get the user's address
    user_address = await address_repo.get_address_by_id(address_id, token["user_id"])
    
    if not user_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found or doesn't belong to you"
        )
    
    # Get the restaurant's information
    try:
        restaurant_service_url = f"http://restaurant:8002/api/v1/restaurants/{restaurant_id}"
        
        headers = {
            "Authorization": f"Bearer {token.get('raw_token', '')}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(restaurant_service_url, headers=headers) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"Restaurant service error: {error}")
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to retrieve restaurant information"
                    )
                
                restaurant = await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to restaurant service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Restaurant service unavailable"
        )
    
    # Get restaurant location from its address
    try:
        restaurant_address_id = restaurant.get("address_id")
        restaurant_service_url = f"http://restaurant:8002/api/v1/restaurants/address/{restaurant_address_id}"
        
        headers = {
            "Authorization": f"Bearer {token.get('raw_token', '')}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(restaurant_service_url, headers=headers) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"Restaurant service error: {error}")
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to retrieve restaurant address"
                    )
                
                restaurant_address = await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to restaurant service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Restaurant service unavailable"
        )
    
    # Get restaurant coordinates
    restaurant_lat = restaurant_address.get("location", {}).get("latitude", 0)
    restaurant_lon = restaurant_address.get("location", {}).get("longitude", 0)
    
    # Get user coordinates
    user_lat = user_address.get("location", {}).get("latitude", 0)
    user_lon = user_address.get("location", {}).get("longitude", 0)
    
    # Format the full address for display
    address_line1 = user_address.get("address_line1", "")
    address_line2 = user_address.get("address_line2", "")
    city = user_address.get("city", "")
    state = user_address.get("state", "")
    postal_code = user_address.get("postal_code", "")
    
    user_address_display = f"{address_line1}"
    if address_line2:
        user_address_display += f", {address_line2}"
    user_address_display += f", {city}, {state} {postal_code}"
    
    # Estimate delivery time
    try:
        estimate = await estimate_delivery_time(
            restaurant_lat=restaurant_lat,
            restaurant_lon=restaurant_lon,
            customer_lat=user_lat,
            customer_lon=user_lon,
            preparation_time_minutes=restaurant.get("estimated_preparation_time", 15)
        )
        
        # Generate the map HTML
        map_html = generate_map_html(
            restaurant_lat=restaurant_lat,
            restaurant_lon=restaurant_lon,
            restaurant_name=restaurant.get("name", "Restaurant"),
            customer_lat=user_lat,
            customer_lon=user_lon,
            customer_address=user_address_display
        )
        
        return {
            "html": map_html,
            "estimated_delivery_time": estimate.get("total_time_minutes", 30)
        }
    except Exception as e:
        logger.error(f"Error generating delivery map: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate delivery map"
        )

@router.get("/{restaurant_id}/delivery-estimate", response_model=DeliveryTimeEstimateResponse)
async def get_delivery_estimate(
    restaurant_id: str,
    address_id: str,
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Get an estimate of the delivery time from a restaurant to a user's address.
    """
    address_repo = AddressRepository()
    
    # Get the user's address
    user_address = await address_repo.get_address_by_id(address_id, token["user_id"])
    
    if not user_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found or doesn't belong to you"
        )
    
    # Get the restaurant's information
    try:
        restaurant_service_url = f"http://restaurant:8002/api/v1/restaurants/{restaurant_id}"
        
        headers = {
            "Authorization": f"Bearer {token.get('raw_token', '')}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(restaurant_service_url, headers=headers) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"Restaurant service error: {error}")
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to retrieve restaurant information"
                    )
                
                restaurant = await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to restaurant service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Restaurant service unavailable"
        )
    
    # Get restaurant location from its address
    try:
        restaurant_address_id = restaurant.get("address_id")
        restaurant_service_url = f"http://restaurant:8002/api/v1/restaurants/address/{restaurant_address_id}"
        
        headers = {
            "Authorization": f"Bearer {token.get('raw_token', '')}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(restaurant_service_url, headers=headers) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"Restaurant service error: {error}")
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to retrieve restaurant address"
                    )
                
                restaurant_address = await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to restaurant service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Restaurant service unavailable"
        )
    
    # Get restaurant coordinates
    restaurant_lat = restaurant_address.get("location", {}).get("latitude", 0)
    restaurant_lon = restaurant_address.get("location", {}).get("longitude", 0)
    
    # Get user coordinates
    user_lat = user_address.get("location", {}).get("latitude", 0)
    user_lon = user_address.get("location", {}).get("longitude", 0)
    
    # Estimate delivery time
    try:
        estimate = await estimate_delivery_time(
            restaurant_lat=restaurant_lat,
            restaurant_lon=restaurant_lon,
            customer_lat=user_lat,
            customer_lon=user_lon,
            preparation_time_minutes=restaurant.get("estimated_preparation_time", 15)
        )
        
        return estimate
    except Exception as e:
        logger.error(f"Error estimating delivery time: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to estimate delivery time"
        )