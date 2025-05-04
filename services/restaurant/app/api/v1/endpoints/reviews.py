from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, List, Optional, Any
import logging

from app.core.auth import validate_token, has_role
from app.models.restaurant import RestaurantRepository
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def get_restaurant_reviews(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Get reviews for the current user's restaurant.
    
    This endpoint retrieves all reviews for the restaurant owned by the current user.
    It makes an internal service-to-service call to the user service's reviews endpoint.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    
    # Get the restaurant ID for this owner
    restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    restaurant_id = restaurant["id"]
    
    # Make an internal service-to-service API call to the user service
    # In a real application, this would use some internal authentication mechanism
    # For simplicity, we'll use the user's token for now
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{settings.USER_SERVICE_URL}/api/v1/reviews/restaurant/{restaurant_id}",
                params={"limit": limit, "offset": offset},
                headers={"Authorization": user_info["token"]}
            )
            
            if response.status_code != 200:
                logger.error(f"Error fetching reviews from user service: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch reviews"
                )
            
            return response.json()
        except Exception as e:
            logger.error(f"Error communicating with user service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to communicate with reviews service"
            )
            
@router.post("/{review_id}/response")
async def respond_to_review(
    review_id: str,
    response: Dict[str, str],
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Respond to a review for the current user's restaurant.
    
    This endpoint allows a restaurant owner to respond to a specific review.
    It makes an internal service-to-service call to the user service's review response endpoint.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    
    # Get the restaurant ID for this owner
    restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    # Make an internal service-to-service API call to the user service
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            api_response = await client.post(
                f"{settings.USER_SERVICE_URL}/api/v1/reviews/{review_id}/response",
                json={"review_response": response.get("text", "")},
                headers={"Authorization": user_info["token"]}
            )
            
            if api_response.status_code != 200:
                logger.error(f"Error responding to review: {api_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to respond to review"
                )
            
            return api_response.json()
        except Exception as e:
            logger.error(f"Error communicating with user service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to communicate with reviews service"
            )