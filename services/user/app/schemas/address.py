from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List
from datetime import datetime

class LocationSchema(BaseModel):
    latitude: float
    longitude: float

class AddressBase(BaseModel):
    address_line1: str = Field(..., min_length=1, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field("Казахстан", min_length=1, max_length=100)
    is_default: bool = False
    address_type: str = Field(..., description="Type of address ('home', 'work', 'other', 'business')")
    
    @validator('address_type')
    def validate_address_type(cls, v):
        allowed_types = {'home', 'work', 'other', 'business'}
        if v.lower() not in allowed_types:
            raise ValueError(f'Address type must be one of {allowed_types}')
        return v.lower()

class AddressCreate(AddressBase):
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class AddressUpdate(BaseModel):
    address_line1: Optional[str] = Field(None, min_length=1, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, min_length=1, max_length=100)
    postal_code: Optional[str] = Field(None, min_length=1, max_length=20)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    is_default: Optional[bool] = None
    address_type: Optional[str] = Field(None, description="Type of address ('home', 'work', 'other', 'business')")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    @validator('address_type')
    def validate_address_type(cls, v):
        if v is None:
            return v
        allowed_types = {'home', 'work', 'other', 'business'}
        if v.lower() not in allowed_types:
            raise ValueError(f'Address type must be one of {allowed_types}')
        return v.lower()

class AddressResponse(AddressBase):
    id: str
    user_id: str
    location: LocationSchema
    created_at: datetime
    updated_at: datetime
    
class AddressWithDistance(AddressResponse):
    distance_km: float

class NearbyAddressesResponse(BaseModel):
    addresses: List[AddressWithDistance]
    total: int

class MapResponse(BaseModel):
    html: str
    estimated_delivery_time: int  # minutes
    
class DeliveryTimeEstimateResponse(BaseModel):
    preparation_time_minutes: int
    travel_time_minutes: int
    total_time_minutes: int
    distance_km: float
    is_traffic_considered: bool