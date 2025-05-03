import aiohttp
import logging
import json
from typing import Dict, Any, Optional, Tuple, List
import math

from app.core.config import settings

logger = logging.getLogger(__name__)

async def geocode_address(address: str) -> Optional[Dict[str, Any]]:
    """
    Geocode an address using Yandex Maps API.
    Returns coordinates and formatted address.
    """
    params = {
        "apikey": settings.YANDEX_MAP_API_KEY,
        "geocode": address,
        "format": "json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(settings.YANDEX_MAP_API_URL, params=params) as response:
                if response.status != 200:
                    logger.error(f"Yandex Maps API error: {response.status} - {await response.text()}")
                    return None
                
                data = await response.json()
                
                # Check if geocoding was successful
                if "response" not in data or "GeoObjectCollection" not in data["response"]:
                    logger.error(f"Unexpected Yandex Maps API response: {data}")
                    return None
                
                # Get the first result
                feature_members = data["response"]["GeoObjectCollection"].get("featureMember", [])
                if not feature_members:
                    logger.warning(f"No geocoding results found for address: {address}")
                    return None
                
                geo_object = feature_members[0]["GeoObject"]
                
                # Get coordinates (format: "latitude longitude")
                point = geo_object.get("Point", {}).get("pos", "")
                if not point:
                    logger.warning(f"No coordinates found for address: {address}")
                    return None
                
                longitude, latitude = map(float, point.split())
                
                # Get formatted address
                formatted_address = geo_object.get("metaDataProperty", {}).get("GeocoderMetaData", {}).get("text", "")
                
                return {
                    "latitude": latitude,
                    "longitude": longitude,
                    "formatted_address": formatted_address
                }
                
    except Exception as e:
        logger.error(f"Error geocoding address '{address}': {str(e)}")
        return None

async def calculate_route(
    from_lat: float, 
    from_lon: float, 
    to_lat: float, 
    to_lon: float,
    avoid_tolls: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Calculate a route between two points using Yandex Maps API.
    Returns distance, duration, and polyline for the route.
    """
    params = {
        "apikey": settings.YANDEX_MAP_API_KEY,
        "mode": "driving",  # Can be driving, masstransit, pedestrian, bicycle
        "origin": f"{from_lat},{from_lon}",
        "destination": f"{to_lat},{to_lon}",
        "format": "json",
        "lang": "en_US",
        "avoid_tolls": "true" if avoid_tolls else "false"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(settings.YANDEX_ROUTING_API_URL, params=params) as response:
                if response.status != 200:
                    logger.error(f"Yandex Maps API error: {response.status} - {await response.text()}")
                    # Fall back to simplified calculation if API call fails
                    return await calculate_simplified_route(from_lat, from_lon, to_lat, to_lon)
                
                data = await response.json()
                
                if "error" in data:
                    logger.error(f"Yandex Maps API error: {data['error']['message']}")
                    return await calculate_simplified_route(from_lat, from_lon, to_lat, to_lon)
                
                # Extract the route information
                try:
                    route = data["route"]
                    
                    # Extract distance in kilometers
                    distance = route["length"] / 1000  # Convert meters to kilometers
                    
                    # Extract duration in seconds
                    duration = route["duration"]
                    
                    # Extract polyline (list of coordinates)
                    polyline = []
                    for point in route["geometry"]:
                        polyline.append([point["lat"], point["lon"]])
                    
                    return {
                        "distance": distance,  # kilometers
                        "duration": duration,  # seconds
                        "polyline": polyline,
                        "source": "yandex_api"
                    }
                except (KeyError, ValueError) as e:
                    logger.error(f"Error parsing Yandex Maps API response: {str(e)}")
                    return await calculate_simplified_route(from_lat, from_lon, to_lat, to_lon)
    
    except Exception as e:
        logger.error(f"Error calculating route with Yandex API: {str(e)}")
        return await calculate_simplified_route(from_lat, from_lon, to_lat, to_lon)

async def calculate_simplified_route(
    from_lat: float, 
    from_lon: float, 
    to_lat: float, 
    to_lon: float
) -> Dict[str, Any]:
    """
    Simplified route calculation as a fallback when the API call fails.
    Uses direct distance calculation and estimated duration based on average speed.
    """
    try:
        # Calculate "as the crow flies" distance
        distance = calculate_distance(from_lat, from_lon, to_lat, to_lon)
        
        # Estimate duration - assume 30 km/h average speed
        # This is a very crude approximation
        duration_seconds = (distance / 30) * 3600
        
        # Create a simple polyline (just start and end points)
        polyline = [
            [from_lat, from_lon],
            [to_lat, to_lon]
        ]
        
        return {
            "distance": distance,  # kilometers
            "duration": duration_seconds,  # seconds
            "polyline": polyline,
            "source": "simplified_calculation"
        }
    except Exception as e:
        logger.error(f"Error in simplified route calculation: {str(e)}")
        # Return very basic information as a last resort
        return {
            "distance": 0,
            "duration": 0,
            "polyline": [[from_lat, from_lon], [to_lat, to_lon]],
            "source": "error_fallback"
        }

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the Haversine distance between two points in kilometers.
    This calculates the "as the crow flies" distance, not the actual driving distance.
    """
    # Earth radius in kilometers
    R = 6371.0
    
    # Convert coordinates to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Differences
    d_lat = lat2_rad - lat1_rad
    d_lon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    
    return distance

def estimate_delivery_time(distance_km: float, traffic_factor: float = 1.2) -> int:
    """
    Estimate delivery time in minutes based on distance.
    Assumes an average speed of 30 km/h in urban areas.
    traffic_factor: Multiplier to account for traffic (1.0 = no traffic, 2.0 = heavy traffic)
    """
    # Base time calculation: distance / speed (in minutes)
    base_time_minutes = (distance_km / 30) * 60
    
    # Add traffic factor
    estimated_time = base_time_minutes * traffic_factor
    
    # Add fixed time for pickup and dropoff (10 minutes)
    estimated_time += 10
    
    return round(estimated_time)