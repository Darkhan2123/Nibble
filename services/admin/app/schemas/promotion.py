from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator

class PromotionBase(BaseModel):
    """Base model for promotion data."""
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(..., min_length=2)
    promo_code: str = Field(..., min_length=2, max_length=50)
    discount_type: str = Field(..., description="Type of discount: percentage, fixed_amount, free_delivery")
    discount_value: float = Field(..., gt=0)
    min_order_amount: float = Field(..., ge=0)
    max_discount_amount: Optional[float] = Field(None, gt=0)
    start_date: datetime
    end_date: datetime
    is_active: bool = True
    usage_limit: Optional[int] = Field(None, gt=0)
    applies_to: List[str] = Field(..., description="List of entities this applies to: all, restaurant_id, menu_item_id, cuisine_type")
    applies_to_ids: Optional[List[str]] = None
    
    @validator('end_date')
    def end_date_must_be_after_start_date(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
    
    @validator('discount_type')
    def validate_discount_type(cls, v):
        valid_types = ['percentage', 'fixed_amount', 'free_delivery', 'free_item']
        if v not in valid_types:
            raise ValueError(f'discount_type must be one of {valid_types}')
        return v
    
    @validator('applies_to')
    def validate_applies_to(cls, v):
        valid_types = ['all', 'restaurant_id', 'menu_item_id', 'cuisine_type']
        for item in v:
            if item not in valid_types:
                raise ValueError(f'applies_to must be one of {valid_types}')
        return v

class PromotionCreate(PromotionBase):
    """Model for creating a new promotion."""
    pass

class PromotionUpdate(BaseModel):
    """Model for updating a promotion."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = Field(None, gt=0)
    min_order_amount: Optional[float] = Field(None, ge=0)
    max_discount_amount: Optional[float] = Field(None, gt=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    usage_limit: Optional[int] = Field(None, gt=0)
    applies_to: Optional[List[str]] = None
    applies_to_ids: Optional[List[str]] = None
    
    @validator('discount_type')
    def validate_discount_type(cls, v):
        if v is not None:
            valid_types = ['percentage', 'fixed_amount', 'free_delivery', 'free_item']
            if v not in valid_types:
                raise ValueError(f'discount_type must be one of {valid_types}')
        return v
    
    @validator('applies_to')
    def validate_applies_to(cls, v):
        if v is not None:
            valid_types = ['all', 'restaurant_id', 'menu_item_id', 'cuisine_type']
            for item in v:
                if item not in valid_types:
                    raise ValueError(f'applies_to must be one of {valid_types}')
        return v

class PromotionResponse(PromotionBase):
    """Model for promotion response."""
    id: str
    current_usage: int = 0
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class PromoValidationRequest(BaseModel):
    """Model for promotion validation request."""
    promo_code: str
    order_amount: float = Field(..., gt=0)
    restaurant_id: Optional[str] = None

class PromoValidationResponse(BaseModel):
    """Model for promotion validation response."""
    is_valid: bool
    discount_amount: Optional[float] = None
    discount_type: Optional[str] = None
    message: Optional[str] = None
    promotion: Optional[PromotionResponse] = None