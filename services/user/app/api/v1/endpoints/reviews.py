from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import Dict, List, Optional, Any

from app.core.auth import validate_token, has_role
from app.models.review import ReviewRepository
from app.schemas.review import (
    ReviewCreate,
    ReviewResponse,
    ReviewResponseUpdate,
    ReviewListResponse
)

router = APIRouter()

@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review: ReviewCreate,
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Create a new review for an order.
    Users can only review orders they have placed.
    """
    user_id = user_info["user_id"]
    review_repo = ReviewRepository()

    # In a real application, validate that:
    # 1. The order exists
    # 2. The order belongs to this user
    # 3. The order is in 'delivered' status
    # 4. The user hasn't already reviewed this order
    # For this exercise, we'll skip some of these validations

    try:
        new_review = await review_repo.create_review(
            customer_id=user_id,
            order_id=review.order_id,
            restaurant_id=review.restaurant_id,
            driver_id=review.driver_id,
            food_rating=review.food_rating,
            delivery_rating=review.delivery_rating,
            review_text=review.review_text
        )
        
        return new_review
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/me", response_model=ReviewListResponse)
async def get_my_reviews(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Get reviews written by the current user.
    """
    user_id = user_info["user_id"]
    review_repo = ReviewRepository()
    
    reviews = await review_repo.get_user_reviews(
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    return {
        "items": reviews,
        "total": len(reviews),
        "limit": limit,
        "offset": offset
    }

@router.get("/restaurant/{restaurant_id}", response_model=ReviewListResponse)
async def get_restaurant_reviews(
    restaurant_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Get reviews for a specific restaurant.
    """
    review_repo = ReviewRepository()
    
    reviews = await review_repo.get_restaurant_reviews(
        restaurant_id=restaurant_id,
        limit=limit,
        offset=offset
    )
    
    return {
        "items": reviews,
        "total": len(reviews),
        "limit": limit,
        "offset": offset
    }

@router.get("/driver/{driver_id}", response_model=ReviewListResponse)
async def get_driver_reviews(
    driver_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Get reviews for a specific driver.
    """
    review_repo = ReviewRepository()
    
    reviews = await review_repo.get_driver_reviews(
        driver_id=driver_id,
        limit=limit,
        offset=offset
    )
    
    return {
        "items": reviews,
        "total": len(reviews),
        "limit": limit,
        "offset": offset
    }

@router.post("/{review_id}/response", response_model=ReviewResponse)
async def respond_to_review(
    review_id: str,
    response: ReviewResponseUpdate,
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Add a response to a customer review.
    Only restaurant owners can respond to reviews for their own restaurant.
    """
    user_id = user_info["user_id"]
    review_repo = ReviewRepository()
    
    # First, get the review to check if it belongs to this restaurant owner
    # In a real application, we would verify that the user is the owner of the restaurant
    # For simplicity, we'll skip this validation for now
    
    try:
        updated_review = await review_repo.update_review_response(
            review_id=review_id,
            response_text=response.review_response
        )
        
        if not updated_review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        return updated_review
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )