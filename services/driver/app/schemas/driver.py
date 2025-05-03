from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import re

class VehicleType(str):
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    BICYCLE = "bicycle"
    SCOOTER = "scooter"

class DriverProfileBase(BaseModel):
    vehicle_type: str = Field(..., description="Type of vehicle used for deliveries")
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = Field(None, ge=1990, le=datetime.now().year + 1)
    license_plate: Optional[str] = None
    driver_license_number: Optional[str] = None
    driver_license_expiry: Optional[date] = None
    insurance_number: Optional[str] = None
    insurance_expiry: Optional[date] = None
    banking_info: Optional[Dict[str, Any]] = None

    @validator('vehicle_type')
    def validate_vehicle_type(cls, v):
        valid_types = ['car', 'motorcycle', 'bicycle', 'scooter']
        if v.lower() not in valid_types:
            raise ValueError(f'Vehicle type must be one of: {", ".join(valid_types)}')
        return v.lower()
    
    @validator('license_plate')
    def validate_license_plate(cls, v, values):
        if v is None:
            return v
        if values.get('vehicle_type') in ['car', 'motorcycle', 'scooter'] and not v:
            raise ValueError('License plate is required for motorized vehicles')
        return v
    
    @validator('driver_license_expiry', 'insurance_expiry')
    def validate_date_not_expired(cls, v):
        if v is None:
            return v
        if v < datetime.now().date():
            raise ValueError('Date has already expired')
        return v

class DriverProfileCreate(DriverProfileBase):
    pass

class DriverProfileUpdate(BaseModel):
    vehicle_type: Optional[str] = Field(None, description="Type of vehicle used for deliveries")
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = Field(None, ge=1990, le=datetime.now().year + 1)
    license_plate: Optional[str] = None
    driver_license_number: Optional[str] = None
    driver_license_expiry: Optional[date] = None
    insurance_number: Optional[str] = None
    insurance_expiry: Optional[date] = None
    banking_info: Optional[Dict[str, Any]] = None
    is_available: Optional[bool] = None

    @validator('vehicle_type')
    def validate_vehicle_type(cls, v):
        if v is None:
            return v
        valid_types = ['car', 'motorcycle', 'bicycle', 'scooter']
        if v.lower() not in valid_types:
            raise ValueError(f'Vehicle type must be one of: {", ".join(valid_types)}')
        return v.lower()
    
    @validator('driver_license_expiry', 'insurance_expiry')
    def validate_date_not_expired(cls, v):
        if v is None:
            return v
        if v < datetime.now().date():
            raise ValueError('Date has already expired')
        return v

class DriverProfileResponse(DriverProfileBase):
    user_id: str
    is_available: bool
    background_check_status: str
    average_rating: Optional[float] = None
    total_deliveries: int
    current_location: Optional[Dict[str, float]] = None
    created_at: datetime
    updated_at: datetime

class DriverLocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    is_available: Optional[bool] = None

class DriverAvailabilityUpdate(BaseModel):
    is_available: bool

class DriverStatisticsResponse(BaseModel):
    total_deliveries: int
    average_rating: float
    total_earnings: float
    total_tips: float
    completion_rate: float
    average_delivery_time: float  # in minutes

class DriverEarningsResponse(BaseModel):
    day: datetime
    deliveries: int
    earnings: float
    tips: float

class NearbyDriversResponse(BaseModel):
    drivers: List[Dict[str, Any]]
    count: int