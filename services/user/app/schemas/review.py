from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class ReviewBase(BaseModel):
    order_id: str
    restaurant_id: str
    driver_id: Optional[str] = None
    food_rating: Optional[int] = Field(None, ge=0, le=5, description="Rating from 0 to 5 stars")
    delivery_rating: Optional[int] = Field(None, ge=0, le=5, description="Rating from 0 to 5 stars")
    review_text: Optional[str] = None
    
    @validator('food_rating', 'delivery_rating')
    def validate_rating(cls, v):
        if v is not None and (v < 0 or v > 5):
            raise ValueError('Rating must be between 0 and 5')
        return v

class ReviewCreate(ReviewBase):
    pass

class ReviewResponse(ReviewBase):
    id: str
    customer_id: str
    reviewed_at: datetime
    review_response: Optional[str] = None
    response_at: Optional[datetime] = None
    is_flagged: bool = False
    flagged_reason: Optional[str] = None
    
    # Customer information
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_picture_url: Optional[str] = None
    
    # Restaurant information (for user reviews)
    restaurant_name: Optional[str] = None
    restaurant_logo: Optional[str] = None

class ReviewResponseUpdate(BaseModel):
    review_response: str = Field(..., min_length=1)

class ReviewListResponse(BaseModel):
    items: List[ReviewResponse]
    total: int
    limit: int
    offset: int