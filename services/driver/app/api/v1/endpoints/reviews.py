from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, List, Optional, Any
import logging

from app.core.auth import validate_token, has_role
from app.models.driver import DriverRepository
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/me")
async def get_my_reviews(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_info: Dict[str, Any] = Depends(has_role("driver"))
):
    """
    Get reviews for the current driver.
    
    This endpoint retrieves all reviews for the driver that is currently logged in.
    It makes an internal service-to-service call to the user service's reviews endpoint.
    """
    user_id = user_info["user_id"]
    
    # Make an internal service-to-service API call to the user service
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{settings.USER_SERVICE_URL}/api/v1/reviews/driver/{user_id}",
                params={"limit": limit, "offset": offset},
                headers={"Authorization": user_info["token"]}
            )
            
            if response.status_code != 200:
                logger.error(f"Error fetching driver reviews: {response.text}")
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