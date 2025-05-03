import aiohttp
import logging
import math
from typing import Dict, Any, Optional, List, Tuple
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

async def geocode_address(address: str) -> Dict[str, Any]:
    """
    Convert an address to geographic coordinates using Yandex Geocoder API.
    
    Args:
        address: The address to geocode.
        
    Returns:
        A dictionary containing latitude, longitude, and formatted_address.
        
    Raises:
        ValueError: If geocoding fails.
    """
    # Replace spaces with + for URL encoding
    formatted_address = address.replace(' ', '+').replace(',', '+')
    
    url = f"{settings.YANDEX_MAP_API_URL}/"
    params = {
        "apikey": settings.YANDEX_MAP_API_KEY,
        "geocode": formatted_address,
        "format": "json",
        "lang": "ru_RU"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"Geocoding API error: {error}")
                    raise ValueError(f"Geocoding failed: HTTP {response.status}")
                
                data = await response.json()
                
                # Extract coordinates from the response
                try:
                    feature = data["GeocoderResponseMetaData"]
                    if feature.get("found", "0") == "0":
                        raise ValueError("No results found for this address")
                    
                    point = feature.get("Point", {})
                    pos = point.get("pos", "").split()
                    
                    if len(pos) != 2:
                        raise ValueError("Invalid coordinate format in response")
                    
                    longitude, latitude = float(pos[0]), float(pos[1])
                    
                    return {
                        "latitude": latitude,
                        "longitude": longitude,
                        "formatted_address": address  # You might want to use the formatted address from the API response
                    }
                except (KeyError, IndexError) as e:
                    logger.error(f"Error parsing geocode response: {e}")
                    raise ValueError(f"Failed to parse geocoding response: {e}")
    except aiohttp.ClientError as e:
        logger.error(f"Geocoding request error: {e}")
        raise ValueError(f"Geocoding request failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in geocoding: {e}")
        raise ValueError(f"Geocoding failed: {e}")

async def calculate_distance(
    from_lat: float, 
    from_lon: float, 
    to_lat: float, 
    to_lon: float
) -> float:
    """
    Calculate the distance between two points using the Haversine formula.
    
    Args:
        from_lat: Latitude of the starting point.
        from_lon: Longitude of the starting point.
        to_lat: Latitude of the destination point.
        to_lon: Longitude of the destination point.
        
    Returns:
        Distance in kilometers.
    """
    # Earth radius in kilometers
    earth_radius = 6371
    
    # Convert coordinates to radians
    lat1_rad = math.radians(from_lat)
    lon1_rad = math.radians(from_lon)
    lat2_rad = math.radians(to_lat)
    lon2_rad = math.radians(to_lon)
    
    # Haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = earth_radius * c
    
    return distance

async def calculate_route(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    avoid_tolls: bool = False
) -> Dict[str, Any]:
    """
    Calculate a route between two points using Yandex Routing API.
    
    Args:
        from_lat: Latitude of the starting point.
        from_lon: Longitude of the starting point.
        to_lat: Latitude of the destination point.
        to_lon: Longitude of the destination point.
        avoid_tolls: Whether to avoid toll roads.
        
    Returns:
        A dictionary containing route information (distance, duration, polyline).
        
    Raises:
        ValueError: If route calculation fails.
    """
    url = settings.YANDEX_ROUTING_API_URL
    
    params = {
        "apikey": settings.YANDEX_MAP_API_KEY,
        "waypoints": f"{from_lon},{from_lat}|{to_lon},{to_lat}",
        "mode": "driving",
        "avoid_tolls": "true" if avoid_tolls else "false",
        "lang": "ru_RU"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"Routing API error: {error}")
                    
                    # Fallback to simple distance calculation
                    distance = await calculate_distance(from_lat, from_lon, to_lat, to_lon)
                    return {
                        "distance": distance * 1000,  # Convert to meters
                        "duration": distance * 3 * 60,  # Assume 20 km/h, convert to seconds
                        "traffic_duration": distance * 3 * 60 * 1.5,  # Add 50% for traffic
                        "polyline": None,
                        "is_fallback": True
                    }
                
                data = await response.json()
                
                try:
                    route = data["route"]
                    
                    return {
                        "distance": route["distance"]["value"],  # in meters
                        "duration": route["duration"]["value"],  # in seconds
                        "traffic_duration": route.get("traffic_duration", {}).get("value", route["duration"]["value"] * 1.3),  # in seconds
                        "polyline": route.get("geometry", None),
                        "is_fallback": False
                    }
                except (KeyError, IndexError) as e:
                    logger.error(f"Error parsing route response: {e}")
                    
                    # Fallback to simple distance calculation
                    distance = await calculate_distance(from_lat, from_lon, to_lat, to_lon)
                    return {
                        "distance": distance * 1000,  # Convert to meters
                        "duration": distance * 3 * 60,  # Assume 20 km/h, convert to seconds
                        "traffic_duration": distance * 3 * 60 * 1.5,  # Add 50% for traffic
                        "polyline": None,
                        "is_fallback": True
                    }
    except aiohttp.ClientError as e:
        logger.error(f"Routing request error: {e}")
        
        # Fallback to simple distance calculation
        distance = await calculate_distance(from_lat, from_lon, to_lat, to_lon)
        return {
            "distance": distance * 1000,  # Convert to meters
            "duration": distance * 3 * 60,  # Assume 20 km/h, convert to seconds
            "traffic_duration": distance * 3 * 60 * 1.5,  # Add 50% for traffic
            "polyline": None,
            "is_fallback": True
        }
    except Exception as e:
        logger.error(f"Unexpected error in routing: {e}")
        
        # Fallback to simple distance calculation
        distance = await calculate_distance(from_lat, from_lon, to_lat, to_lon)
        return {
            "distance": distance * 1000,  # Convert to meters
            "duration": distance * 3 * 60,  # Assume 20 km/h, convert to seconds
            "traffic_duration": distance * 3 * 60 * 1.5,  # Add 50% for traffic
            "polyline": None,
            "is_fallback": True
        }

async def estimate_delivery_time(
    restaurant_lat: float,
    restaurant_lon: float,
    customer_lat: float,
    customer_lon: float,
    preparation_time_minutes: int = 15
) -> Dict[str, Any]:
    """
    Estimate the delivery time from a restaurant to a customer.
    
    Args:
        restaurant_lat: Latitude of the restaurant.
        restaurant_lon: Longitude of the restaurant.
        customer_lat: Latitude of the customer.
        customer_lon: Longitude of the customer.
        preparation_time_minutes: Food preparation time in minutes.
        
    Returns:
        A dictionary containing estimated delivery time information.
    """
    try:
        # Calculate the route
        route = await calculate_route(
            restaurant_lat, 
            restaurant_lon,
            customer_lat,
            customer_lon
        )
        
        # Convert seconds to minutes and round up
        travel_time_minutes = math.ceil(route["traffic_duration"] / 60)
        
        # Add preparation time
        total_time_minutes = travel_time_minutes + preparation_time_minutes
        
        return {
            "preparation_time_minutes": preparation_time_minutes,
            "travel_time_minutes": travel_time_minutes,
            "total_time_minutes": total_time_minutes,
            "distance_km": route["distance"] / 1000,  # Convert meters to kilometers
            "is_traffic_considered": not route.get("is_fallback", False)
        }
    except Exception as e:
        logger.error(f"Error estimating delivery time: {e}")
        
        # Fallback to a simple estimate
        distance = await calculate_distance(restaurant_lat, restaurant_lon, customer_lat, customer_lon)
        travel_time_minutes = math.ceil(distance * 3)  # Assume 20 km/h
        total_time_minutes = travel_time_minutes + preparation_time_minutes
        
        return {
            "preparation_time_minutes": preparation_time_minutes,
            "travel_time_minutes": travel_time_minutes,
            "total_time_minutes": total_time_minutes,
            "distance_km": distance,
            "is_traffic_considered": False
        }

def generate_map_html(
    restaurant_lat: float,
    restaurant_lon: float,
    restaurant_name: str,
    customer_lat: float,
    customer_lon: float,
    customer_address: str,
    api_key: str = None
) -> str:
    """
    Generate HTML with a Yandex map showing the route from restaurant to customer.
    
    Args:
        restaurant_lat: Latitude of the restaurant.
        restaurant_lon: Longitude of the restaurant.
        restaurant_name: Name of the restaurant.
        customer_lat: Latitude of the customer.
        customer_lon: Longitude of the customer.
        customer_address: Customer's address.
        api_key: Yandex Maps API key. If None, uses the configured API key.
        
    Returns:
        HTML string with the map.
    """
    if api_key is None:
        api_key = settings.YANDEX_MAP_API_KEY
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Delivery Route</title>
        <style>
            html, body, #map {{
                width: 100%;
                height: 100%;
                margin: 0;
                padding: 0;
            }}
            .route-info {{
                background-color: white;
                padding: 10px;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0,0,0,0.3);
                position: absolute;
                top: 10px;
                left: 10px;
                z-index: 1000;
            }}
            .loading {{
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 24px;
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0,0,0,0.3);
                z-index: 2000;
            }}
        </style>
    </head>
    <body>
        <div id="loading" class="loading">Loading map and calculating route...</div>
        <div id="map"></div>
        <div id="routeInfo" class="route-info" style="display:none;">
            <h3>Delivery Route Information</h3>
            <div id="routeDetails"></div>
        </div>
        
        <script src="https://api-maps.yandex.ru/2.1/?lang=ru_RU&apikey={api_key}"></script>
        <script>
            let map, route;
            
            ymaps.ready(init);
            
            function init() {{
                // Hide loading message
                document.getElementById('loading').style.display = 'none';
                
                // Show route info panel
                document.getElementById('routeInfo').style.display = 'block';
                
                // Create map centered at the midpoint between restaurant and customer
                const centerLat = ({restaurant_lat} + {customer_lat}) / 2;
                const centerLon = ({restaurant_lon} + {customer_lon}) / 2;
                
                map = new ymaps.Map("map", {{
                    center: [centerLat, centerLon],
                    zoom: 12,
                    controls: ['zoomControl', 'typeSelector', 'fullscreenControl']
                }});
                
                // Add restaurant marker
                const restaurantMarker = new ymaps.Placemark(
                    [{restaurant_lat}, {restaurant_lon}],
                    {{
                        balloonContent: '<strong>{restaurant_name}</strong><br>Restaurant location'
                    }},
                    {{
                        preset: 'islands#redFoodIcon'
                    }}
                );
                map.geoObjects.add(restaurantMarker);
                
                // Add customer marker
                const customerMarker = new ymaps.Placemark(
                    [{customer_lat}, {customer_lon}],
                    {{
                        balloonContent: '<strong>Delivery Address</strong><br>{customer_address}'
                    }},
                    {{
                        preset: 'islands#blueHomeIcon'
                    }}
                );
                map.geoObjects.add(customerMarker);
                
                // Calculate route
                ymaps.route([
                    ['{restaurant_lat}', '{restaurant_lon}'],
                    ['{customer_lat}', '{customer_lon}']
                ], {{
                    mapStateAutoApply: true,
                    avoidTrafficJams: true
                }}).then(function(routeResult) {{
                    route = routeResult;
                    
                    // Add route to map
                    map.geoObjects.add(route);
                    
                    // Get the first route
                    const path = route.getPaths().get(0);
                    
                    // Calculate metrics
                    const distance = path.getLength(); // meters
                    const duration = path.getTime(); // seconds
                    const jamsTime = path.getJamsTime(); // seconds with traffic jams
                    
                    // Format distance
                    let distanceText;
                    if (distance >= 1000) {{
                        distanceText = (distance / 1000).toFixed(1) + ' km';
                    }} else {{
                        distanceText = Math.round(distance) + ' m';
                    }}
                    
                    // Format duration
                    const formatTime = (seconds) => {{
                        const minutes = Math.floor(seconds / 60);
                        if (minutes < 60) {{
                            return minutes + ' min';
                        }} else {{
                            const hours = Math.floor(minutes / 60);
                            const remainingMinutes = minutes % 60;
                            return hours + ' h ' + remainingMinutes + ' min';
                        }}
                    }};
                    
                    const durationText = formatTime(duration);
                    const jamsTimeText = formatTime(jamsTime);
                    
                    // Display route information
                    document.getElementById('routeDetails').innerHTML = `
                        <p><strong>Distance:</strong> ${{distanceText}}</p>
                        <p><strong>Normal duration:</strong> ${{durationText}}</p>
                        <p><strong>Duration with traffic:</strong> ${{jamsTimeText}}</p>
                    `;
                    
                    // Fit the map to show the entire route
                    map.setBounds(route.getBounds(), {{ checkZoomRange: true, zoomMargin: 20 }});
                    
                }}
                ).catch(function(error) {{
                    console.error("Error calculating route:", error);
                    document.getElementById('routeDetails').innerHTML = 
                        '<p>Error calculating route. Please try again later.</p>';
                }});
            }}
        </script>
    </body>
    </html>
    """
    
    return html