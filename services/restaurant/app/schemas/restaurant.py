from pydantic import BaseModel, Field, EmailStr, validator, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime, time
import re

class RestaurantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    cuisine_type: List[str] = Field(..., min_items=1)
    price_range: int = Field(..., ge=1, le=4)
    phone_number: str = Field(..., min_length=10, max_length=15)
    email: EmailStr
    address_id: str
    website_url: Optional[HttpUrl] = None
    delivery_fee: Optional[float] = Field(None, ge=0)
    minimum_order_amount: Optional[float] = Field(None, ge=0)
    estimated_delivery_time: Optional[int] = Field(None, ge=5, le=120)

    @validator('phone_number')
    def validate_phone_number(cls, v):
        pattern = r'^\+?[0-9]{10,15}$'
        if not re.match(pattern, v):
            raise ValueError('Phone number must be in a valid format')
        return v
    
    @validator('cuisine_type')
    def validate_cuisine_type(cls, v):
        if not v:
            raise ValueError('At least one cuisine type is required')
        return v
    
    @validator('price_range')
    def validate_price_range(cls, v):
        if v < 1 or v > 4:
            raise ValueError('Price range must be between 1 and 4')
        return v

class RestaurantCreate(RestaurantBase):
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None

class RestaurantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    cuisine_type: Optional[List[str]] = Field(None, min_items=1)
    price_range: Optional[int] = Field(None, ge=1, le=4)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)
    email: Optional[EmailStr] = None
    website_url: Optional[HttpUrl] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    delivery_fee: Optional[float] = Field(None, ge=0)
    minimum_order_amount: Optional[float] = Field(None, ge=0)
    estimated_delivery_time: Optional[int] = Field(None, ge=5, le=120)
    is_active: Optional[bool] = None

    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v is None:
            return v
        pattern = r'^\+?[0-9]{10,15}$'
        if not re.match(pattern, v):
            raise ValueError('Phone number must be in a valid format')
        return v
    
    @validator('cuisine_type')
    def validate_cuisine_type(cls, v):
        if v is not None and not v:
            raise ValueError('At least one cuisine type is required')
        return v
    
    @validator('price_range')
    def validate_price_range(cls, v):
        if v is not None and (v < 1 or v > 4):
            raise ValueError('Price range must be between 1 and 4')
        return v

class Address(BaseModel):
    id: str
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    latitude: float
    longitude: float

class RestaurantResponse(RestaurantBase):
    id: str
    user_id: str
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    is_featured: bool
    is_verified: bool
    is_active: bool
    average_rating: float
    total_ratings: int
    commission_rate: float
    created_at: datetime
    updated_at: datetime
    address: Optional[Address] = None
    distance_km: Optional[float] = None
    formatted_address: Optional[str] = None

class RestaurantListResponse(BaseModel):
    items: List[RestaurantResponse]
    total: int
    limit: int
    offset: int

class RestaurantSearchParams(BaseModel):
    query: Optional[str] = None
    cuisine_type: Optional[List[str]] = None
    price_range: Optional[List[int]] = None
    is_open: Optional[bool] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius: Optional[int] = Field(None, ge=100, le=50000)  # in meters
    sort_by: str = Field("distance", pattern="^(distance|rating|price)$")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    
    @validator('latitude', 'longitude')
    def validate_coordinates(cls, v, values, **kwargs):
        field_name = kwargs['field'].name
        
        # If this is latitude and longitude is already set, or vice versa,
        # make sure they are both provided or both None
        if field_name == 'latitude' and v is not None and values.get('longitude') is None:
            raise ValueError('Both latitude and longitude must be provided together')
        if field_name == 'longitude' and v is not None and values.get('latitude') is None:
            raise ValueError('Both latitude and longitude must be provided together')
        
        return v
    
    @validator('radius')
    def validate_radius(cls, v, values):
        # If radius is provided, coordinates must also be provided
        if v is not None and (values.get('latitude') is None or values.get('longitude') is None):
            raise ValueError('Radius requires latitude and longitude to be provided')
        return v

class OperatingHoursBase(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)  # 0 = Sunday, 6 = Saturday
    open_time: time
    close_time: time
    is_closed: bool = False

    @validator('day_of_week')
    def validate_day_of_week(cls, v):
        if v < 0 or v > 6:
            raise ValueError('Day of week must be between 0 (Sunday) and 6 (Saturday)')
        return v
    
    @validator('close_time')
    def validate_close_time(cls, v, values):
        if 'open_time' in values and v <= values['open_time']:
            raise ValueError('Close time must be after open time')
        return v

class OperatingHoursUpdate(OperatingHoursBase):
    pass

class OperatingHoursResponse(OperatingHoursBase):
    id: str
    restaurant_id: str

class RestaurantAnalyticsResponse(BaseModel):
    total_orders: int
    total_revenue: float
    average_order_value: float
    popular_items: List[Dict[str, Any]]
    busiest_times: List[Dict[str, Any]]

class ReviewSummary(BaseModel):
    id: str
    customer_name: str
    food_rating: Optional[int]
    delivery_rating: Optional[int]
    review_text: Optional[str]
    reviewed_at: datetime
    has_response: bool

class RestaurantDashboardResponse(BaseModel):
    total_orders_today: int
    active_orders: int
    completed_orders_today: int
    cancelled_orders_today: int
    today_revenue: float
    current_status: str
    recent_reviews: List[ReviewSummary]
    average_rating: Optional[float]