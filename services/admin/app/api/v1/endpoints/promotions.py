from fastapi import APIRouter, Depends, Path, Query, HTTPException, status
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.auth import get_current_admin
from app.models.promotion import PromotionRepository
from app.schemas.promotion import (
    PromotionCreate, PromotionUpdate, PromotionResponse,
    PromoValidationRequest, PromoValidationResponse
)
from app.core.kafka import publish_promotion_created, publish_promotion_updated, publish_promotion_deleted

router = APIRouter()
promotion_repository = PromotionRepository()

@router.post("", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED)
async def create_promotion(
    promotion_data: PromotionCreate,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Create a new promotion.
    
    This endpoint allows an admin to create a new promotion.
    """
    try:
        promotion = await promotion_repository.create_promotion(
            name=promotion_data.name,
            description=promotion_data.description,
            promo_code=promotion_data.promo_code,
            discount_type=promotion_data.discount_type,
            discount_value=promotion_data.discount_value,
            min_order_amount=promotion_data.min_order_amount,
            max_discount_amount=promotion_data.max_discount_amount,
            start_date=promotion_data.start_date,
            end_date=promotion_data.end_date,
            is_active=promotion_data.is_active,
            usage_limit=promotion_data.usage_limit,
            applies_to=promotion_data.applies_to,
            applies_to_ids=promotion_data.applies_to_ids,
            created_by=current_admin["id"]
        )
        
        # Publish promotion created event
        await publish_promotion_created(promotion)
        
        return promotion
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("", response_model=List[PromotionResponse])
async def get_promotions(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100, description="Number of promotions to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get a list of promotions.
    
    This endpoint allows an admin to retrieve a list of promotions.
    """
    promotions = await promotion_repository.get_promotions(
        is_active=is_active,
        limit=limit,
        offset=offset
    )
    
    return promotions

@router.get("/active", response_model=List[PromotionResponse])
async def get_active_promotions(
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get a list of active promotions.
    
    This endpoint allows an admin to retrieve a list of active promotions.
    """
    promotions = await promotion_repository.get_active_promotions()
    
    return promotions

@router.get("/{promotion_id}", response_model=PromotionResponse)
async def get_promotion(
    promotion_id: str = Path(..., description="The ID of the promotion"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get a promotion by ID.
    
    This endpoint allows an admin to retrieve a promotion by its ID.
    """
    promotion = await promotion_repository.get_promotion_by_id(promotion_id)
    
    if not promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promotion not found"
        )
    
    return promotion

@router.put("/{promotion_id}", response_model=PromotionResponse)
async def update_promotion(
    promotion_data: PromotionUpdate,
    promotion_id: str = Path(..., description="The ID of the promotion to update"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Update a promotion.
    
    This endpoint allows an admin to update a promotion.
    """
    # Check if promotion exists
    existing_promotion = await promotion_repository.get_promotion_by_id(promotion_id)
    
    if not existing_promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promotion not found"
        )
    
    try:
        updated_promotion = await promotion_repository.update_promotion(
            promotion_id=promotion_id,
            name=promotion_data.name,
            description=promotion_data.description,
            discount_type=promotion_data.discount_type,
            discount_value=promotion_data.discount_value,
            min_order_amount=promotion_data.min_order_amount,
            max_discount_amount=promotion_data.max_discount_amount,
            start_date=promotion_data.start_date,
            end_date=promotion_data.end_date,
            is_active=promotion_data.is_active,
            usage_limit=promotion_data.usage_limit,
            applies_to=promotion_data.applies_to,
            applies_to_ids=promotion_data.applies_to_ids
        )
        
        # Publish promotion updated event
        if updated_promotion:
            await publish_promotion_updated(updated_promotion)
        
        return updated_promotion
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{promotion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_promotion(
    promotion_id: str = Path(..., description="The ID of the promotion to delete"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Delete a promotion.
    
    This endpoint allows an admin to delete a promotion.
    """
    # Check if promotion exists
    existing_promotion = await promotion_repository.get_promotion_by_id(promotion_id)
    
    if not existing_promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promotion not found"
        )
    
    success = await promotion_repository.delete_promotion(promotion_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete promotion"
        )
    
    # Publish promotion deleted event
    await publish_promotion_deleted(promotion_id, current_admin["id"])

@router.post("/validate", response_model=PromoValidationResponse)
async def validate_promotion(
    validation_data: PromoValidationRequest,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Validate a promotion code.
    
    This endpoint allows an admin to validate a promotion code.
    """
    # Simulate a user ID (in a real application, this would be the customer ID)
    user_id = current_admin["id"]
    
    promotion = await promotion_repository.validate_promotion(
        promo_code=validation_data.promo_code,
        order_amount=validation_data.order_amount,
        user_id=user_id,
        restaurant_id=validation_data.restaurant_id
    )
    
    if not promotion:
        return {
            "is_valid": False,
            "message": "Invalid promotion code"
        }
    
    # Calculate the discount
    discount_amount = await promotion_repository.calculate_discount(
        promotion=promotion,
        order_amount=validation_data.order_amount
    )
    
    return {
        "is_valid": True,
        "discount_amount": discount_amount,
        "discount_type": promotion["discount_type"],
        "promotion": promotion
    }