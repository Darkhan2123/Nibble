import aiohttp
import logging
from typing import Dict, Any, Optional
import json

from app.core.config import settings

logger = logging.getLogger(__name__)

async def get_driver_location(driver_id: str) -> Optional[Dict[str, float]]:
    """
    Get a driver's current location from the driver service.
    Returns the latitude and longitude.
    """
    driver_service_url = f"{settings.DRIVER_SERVICE_URL}/v1/drivers/{driver_id}"
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"}
            async with session.get(driver_service_url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Error fetching driver location: {response.status} - {await response.text()}")
                    return None
                
                data = await response.json()
                
                # Extract location if available
                if "current_location" in data and data["current_location"]:
                    return {
                        "latitude": data["current_location"]["latitude"],
                        "longitude": data["current_location"]["longitude"]
                    }
                
                logger.warning(f"No location data available for driver {driver_id}")
                return None
                
    except Exception as e:
        logger.error(f"Error fetching driver location: {str(e)}")
        return None

async def get_restaurant_location(restaurant_id: str) -> Optional[Dict[str, float]]:
    """
    Get a restaurant's location from the restaurant service.
    Returns the latitude and longitude.
    """
    restaurant_service_url = f"{settings.RESTAURANT_SERVICE_URL}/v1/restaurants/{restaurant_id}"
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"}
            async with session.get(restaurant_service_url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Error fetching restaurant location: {response.status} - {await response.text()}")
                    return None
                
                data = await response.json()
                
                # Extract location if available
                if "address" in data and data["address"] and "location" in data["address"]:
                    return {
                        "latitude": data["address"]["location"]["latitude"],
                        "longitude": data["address"]["location"]["longitude"]
                    }
                
                logger.warning(f"No location data available for restaurant {restaurant_id}")
                return None
                
    except Exception as e:
        logger.error(f"Error fetching restaurant location: {str(e)}")
        return None

async def get_delivery_route(order_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the delivery route for an order from the driver service.
    Returns the route data including polyline.
    """
    route_url = f"{settings.DRIVER_SERVICE_URL}/v1/deliveries/{order_id}/route"
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"}
            async with session.get(route_url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Error fetching delivery route: {response.status} - {await response.text()}")
                    return None
                
                return await response.json()
                
    except Exception as e:
        logger.error(f"Error fetching delivery route: {str(e)}")
        return None