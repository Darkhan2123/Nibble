from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
import logging
import os
from pathlib import Path

from app.core.auth import validate_token
from app.models.address import AddressRepository
from app.core.config import get_settings
from app.core.maps import estimate_delivery_time

logger = logging.getLogger(__name__)
settings = get_settings()

# Set up Jinja2 templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter()

@router.get("/restaurant-to-address", response_class=HTMLResponse)
async def show_restaurant_to_address_map(
    request: Request,
    restaurant_id: str,
    address_id: str,
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Show a map with a route from a restaurant to a user's address.
    """
    address_repo = AddressRepository()
    
    # Get the user's address
    user_address = await address_repo.get_address_by_id(address_id, token["user_id"])
    
    if not user_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found or doesn't belong to you"
        )
    
    # Get the restaurant's information (mock data for now)
    # In a real implementation, this would call the restaurant service
    restaurant = {
        "id": restaurant_id,
        "name": "Sample Restaurant",
        "estimated_preparation_time": 15,
        "address": {
            "location": {
                "latitude": 51.1801,  # Example coordinates for Astana
                "longitude": 71.4459
            }
        }
    }
    
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
            restaurant_lat=restaurant["address"]["location"]["latitude"],
            restaurant_lon=restaurant["address"]["location"]["longitude"],
            customer_lat=user_lat,
            customer_lon=user_lon,
            preparation_time_minutes=restaurant.get("estimated_preparation_time", 15)
        )
        
        # Render the template
        return templates.TemplateResponse(
            "map.html", 
            {
                "request": request,
                "api_key": settings.YANDEX_MAP_API_KEY,
                "restaurant_lat": restaurant["address"]["location"]["latitude"],
                "restaurant_lon": restaurant["address"]["location"]["longitude"],
                "restaurant_name": restaurant["name"],
                "customer_lat": user_lat,
                "customer_lon": user_lon,
                "customer_address": user_address_display,
                "preparation_time": restaurant.get("estimated_preparation_time", 15)
            }
        )
    except Exception as e:
        logger.error(f"Error generating delivery map: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate delivery map"
        )