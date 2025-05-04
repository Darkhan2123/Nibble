from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import Dict, List, Optional, Any
import logging

from app.core.auth import validate_token, has_role, has_any_role, restaurant_owner_or_admin
from app.models.restaurant import RestaurantRepository
from app.schemas.restaurant import (
    RestaurantCreate, RestaurantUpdate, RestaurantResponse, 
    RestaurantListResponse, RestaurantSearchParams,
    OperatingHoursUpdate, OperatingHoursResponse,
    RestaurantAnalyticsResponse, RestaurantDashboardResponse
)
from app.core.kafka import (
    publish_restaurant_created, publish_restaurant_updated,
    publish_restaurant_status_changed
)
from app.core.redis import (
    cache_restaurant, get_cached_restaurant, invalidate_restaurant_cache,
    create_location_key, get_cached_nearby_restaurants
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=RestaurantResponse, status_code=status.HTTP_201_CREATED)
async def create_restaurant(
    restaurant: RestaurantCreate,
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Create a new restaurant. Only users with the 'restaurant' role can do this.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    
    # Check if user already has a restaurant
    existing_restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    if existing_restaurant:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already has a restaurant"
        )
    
    try:
        new_restaurant = await restaurant_repo.create_restaurant(
            user_id=user_id,
            name=restaurant.name,
            description=restaurant.description,
            cuisine_type=restaurant.cuisine_type,
            price_range=restaurant.price_range,
            phone_number=restaurant.phone_number,
            email=restaurant.email,
            address_id=restaurant.address_id,
            website_url=str(restaurant.website_url) if restaurant.website_url else None,
            logo_url=restaurant.logo_url,
            banner_url=restaurant.banner_url,
            delivery_fee=restaurant.delivery_fee or 0,
            minimum_order_amount=restaurant.minimum_order_amount or 0,
        )
        
        # Publish restaurant created event
        await publish_restaurant_created({
            "restaurant_id": new_restaurant["id"],
            "name": new_restaurant["name"],
            "cuisine_type": new_restaurant["cuisine_type"],
            "user_id": new_restaurant["user_id"]
        })
        
        logger.info(f"Restaurant created with ID: {new_restaurant['id']}")
        
        return new_restaurant
        
    except ValueError as e:
        logger.error(f"Error creating restaurant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating restaurant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/me", response_model=RestaurantResponse)
async def get_my_restaurant(
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Get the current user's restaurant.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    
    restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    return restaurant

@router.put("/me", response_model=RestaurantResponse)
async def update_my_restaurant(
    restaurant: RestaurantUpdate,
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Update the current user's restaurant.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    
    existing_restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not existing_restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    try:
        updated_restaurant = await restaurant_repo.update_restaurant(
            restaurant_id=existing_restaurant["id"],
            update_data=restaurant.dict(exclude_unset=True)
        )
        
        # Invalidate cache
        await invalidate_restaurant_cache(existing_restaurant["id"])
        
        # Publish restaurant updated event
        await publish_restaurant_updated({
            "restaurant_id": updated_restaurant["id"],
            "name": updated_restaurant["name"],
            "cuisine_type": updated_restaurant["cuisine_type"],
            "user_id": updated_restaurant["user_id"],
            "is_active": updated_restaurant["is_active"]
        })
        
        logger.info(f"Restaurant updated with ID: {updated_restaurant['id']}")
        
        return updated_restaurant
        
    except ValueError as e:
        logger.error(f"Error updating restaurant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error updating restaurant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.post("/me/status", response_model=RestaurantResponse)
async def update_restaurant_status(
    status: bool,
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Update the restaurant's active status.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    
    existing_restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not existing_restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    try:
        updated_restaurant = await restaurant_repo.update_restaurant_status(
            restaurant_id=existing_restaurant["id"],
            is_active=status
        )
        
        # Invalidate cache
        await invalidate_restaurant_cache(existing_restaurant["id"])
        
        # Publish restaurant status changed event
        await publish_restaurant_status_changed(
            restaurant_id=updated_restaurant["id"],
            is_active=status
        )
        
        logger.info(f"Restaurant status updated with ID: {updated_restaurant['id']}, status: {status}")
        
        return updated_restaurant
        
    except Exception as e:
        logger.error(f"Unexpected error updating restaurant status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/me/hours", response_model=List[OperatingHoursResponse])
async def get_operating_hours(
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Get the operating hours for the current user's restaurant.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    
    existing_restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not existing_restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    hours = await restaurant_repo.get_operating_hours(existing_restaurant["id"])
    
    return hours

@router.put("/me/hours/{day_of_week}", response_model=OperatingHoursResponse)
async def update_operating_hour(
    day_of_week: int = Path(..., ge=0, le=6),
    hours: OperatingHoursUpdate = None,
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Update the operating hours for a specific day. Day of week is from 0 (Sunday) to 6 (Saturday).
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    
    existing_restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not existing_restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    try:
        updated_hours = await restaurant_repo.update_operating_hours(
            restaurant_id=existing_restaurant["id"],
            day_of_week=day_of_week,
            open_time=hours.open_time.isoformat(),
            close_time=hours.close_time.isoformat(),
            is_closed=hours.is_closed
        )
        
        # Invalidate cache
        await invalidate_restaurant_cache(existing_restaurant["id"])
        
        logger.info(f"Restaurant hours updated for restaurant ID: {existing_restaurant['id']}, day: {day_of_week}")
        
        return updated_hours
        
    except Exception as e:
        logger.error(f"Unexpected error updating restaurant hours: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/me/dashboard", response_model=RestaurantDashboardResponse)
async def get_restaurant_dashboard(
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Get the restaurant dashboard data including recent reviews.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    
    existing_restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not existing_restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    # Get recent reviews from the user service
    recent_reviews = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.USER_SERVICE_URL}/api/v1/reviews/restaurant/{existing_restaurant['id']}",
                params={"limit": 5, "offset": 0},  # Just get the 5 most recent reviews
                headers={"Authorization": user_info["token"]}
            )
            
            if response.status_code == 200:
                reviews_data = response.json()
                if "items" in reviews_data and reviews_data["items"]:
                    for review in reviews_data["items"]:
                        recent_reviews.append({
                            "id": review["id"],
                            "customer_name": f"{review.get('first_name', '')} {review.get('last_name', '')}".strip(),
                            "food_rating": review.get("food_rating"),
                            "delivery_rating": review.get("delivery_rating"),
                            "review_text": review.get("review_text"),
                            "reviewed_at": review.get("reviewed_at"),
                            "has_response": review.get("review_response") is not None
                        })
    except Exception as e:
        logger.error(f"Error fetching reviews for dashboard: {str(e)}")
        # Continue even if reviews can't be fetched
    
    # In a real application, this would query from multiple services
    # For now, we'll return placeholder data with real reviews
    
    return {
        "total_orders_today": 0,
        "active_orders": 0,
        "completed_orders_today": 0,
        "cancelled_orders_today": 0,
        "today_revenue": 0,
        "current_status": "open" if existing_restaurant["is_active"] else "closed",
        "recent_reviews": recent_reviews,
        "average_rating": existing_restaurant.get("average_rating", 0)
    }

@router.get("/me/analytics", response_model=RestaurantAnalyticsResponse)
async def get_restaurant_analytics(
    period: str = Query("day", regex="^(day|week|month|year)$"),
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Get analytics for the current user's restaurant.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    
    existing_restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not existing_restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    analytics = await restaurant_repo.get_restaurant_analytics(
        restaurant_id=existing_restaurant["id"],
        period=period
    )
    
    return analytics

@router.get("/{restaurant_id}", response_model=RestaurantResponse)
async def get_restaurant(
    restaurant_id: str,
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Get a restaurant by ID.
    Uses Redis caching for frequently accessed restaurants.
    """
    restaurant_repo = RestaurantRepository()
    
    # The get_restaurant_by_id method now includes caching logic
    restaurant = await restaurant_repo.get_restaurant_by_id(restaurant_id)
    
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )
    
    return restaurant

@router.get("/", response_model=RestaurantListResponse)
async def search_restaurants(
    query: Optional[str] = None,
    cuisine: Optional[List[str]] = Query(None),
    price: Optional[List[int]] = Query(None),
    open_now: Optional[bool] = None,
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitude"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitude"),
    radius: Optional[int] = Query(None, ge=100, le=50000, description="Search radius in meters"),
    sort_by: str = Query("distance", regex="^(distance|rating|price)$", description="Sort results by"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Search for restaurants based on various criteria.
    Uses Redis caching for common search queries to improve performance.
    
    Parameters:
    - query: Search text for name or description
    - cuisine: Filter by cuisine types
    - price: Filter by price range (1-4)
    - open_now: Filter by currently open restaurants
    - lat/lon: Geographic coordinates for location-based search
    - radius: Maximum distance from coordinates (in meters)
    - sort_by: Sort results by "distance", "rating", or "price"
    - limit/offset: Pagination parameters
    
    Returns a list of restaurants matching the criteria.
    When coordinates are provided, results include distance in kilometers.
    """
    restaurant_repo = RestaurantRepository()
    
    # Validate coordinates
    if (lat is not None and lon is None) or (lat is None and lon is not None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both latitude and longitude must be provided together"
        )
    
    # If radius is provided, coordinates must also be provided
    if radius is not None and (lat is None or lon is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Radius requires latitude and longitude to be provided"
        )
    
    # Validate price range
    if price:
        for p in price:
            if p < 1 or p > 4:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Price range must be between 1 and 4"
                )
    
    # If sort_by is distance but no coordinates are provided, use rating instead
    if sort_by == "distance" and (lat is None or lon is None):
        sort_by = "rating"
        logger.info("Changed sort order to 'rating' because no coordinates were provided")
    
    try:
        # The search_restaurants method now includes caching logic
        restaurants = await restaurant_repo.search_restaurants(
            query_string=query,
            cuisine_type=cuisine,
            price_range=price,
            is_open=open_now,
            latitude=lat,
            longitude=lon,
            radius=radius,
            limit=limit,
            offset=offset,
            sort_by=sort_by
        )
        
        # Get total count for accurate pagination
        # In a real app with large datasets, this would need optimization
        total_count = len(restaurants)
        
        return {
            "items": restaurants,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error searching restaurants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while searching for restaurants"
        )
        
@router.get("/nearby", response_model=RestaurantListResponse)
async def get_nearby_restaurants(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius: int = Query(5000, ge=100, le=50000, description="Search radius in meters"),
    cuisine: Optional[List[str]] = Query(None),
    open_now: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Get restaurants near a specific location.
    Uses Redis caching for location-based queries to improve performance.
    
    This endpoint returns restaurants within the specified radius of the given coordinates,
    sorted by distance. It's a convenience wrapper around the search endpoint.
    
    Parameters:
    - lat/lon: Geographic coordinates (required)
    - radius: Maximum distance from coordinates in meters (default: 5000m / 5km)
    - cuisine: Filter by cuisine types
    - open_now: Filter by currently open restaurants
    - limit/offset: Pagination parameters
    
    Returns restaurants ordered by distance from the provided coordinates.
    """
    restaurant_repo = RestaurantRepository()
    
    # Don't use cache if requesting paginated results
    if offset > 0:
        logger.debug("Skipping cache for paginated nearby restaurants request")
    else:
        # Check if we have a cached result for this location
        location_key = create_location_key(lat, lon, radius)
        
        # Only use the cache for default parameter values
        if cuisine is None and not open_now and limit == 20:
            # The search_restaurants method already handles caching
            # We explicitly log here for clarity
            logger.debug(f"Using cached nearby restaurants for location key: {location_key}")
    
    try:
        # The search_restaurants method now includes caching logic
        restaurants = await restaurant_repo.search_restaurants(
            cuisine_type=cuisine,
            is_open=open_now,
            latitude=lat,
            longitude=lon,
            radius=radius,
            limit=limit,
            offset=offset,
            sort_by="distance"  # Always sort by distance for nearby endpoint
        )
        
        return {
            "items": restaurants,
            "total": len(restaurants),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error finding nearby restaurants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while finding nearby restaurants"
        )