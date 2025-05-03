from pydantic import BaseModel, EmailStr, Field, validator, UUID4
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
import re

class TokenPayload(BaseModel):
    sub: str
    exp: int
    roles: List[str]

class UserBase(BaseModel):
    id: Union[UUID4, str]
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: str
    roles: List[str]

class UserResponse(UserBase):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    message: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: Dict[str, Any]

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class AddressData(BaseModel):
    address_line1: str = Field(..., min_length=1, max_length=255)
    address_line2: Optional[str] = None
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field("Казахстан", min_length=1, max_length=100)
    address_type: str = Field("home", pattern="^(home|work|other)$")
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class RegistrationRequest(BaseModel):
    email: EmailStr
    phone_number: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    address: AddressData  # Mandatory address for all customer registrations
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        # Improve phone validation
        pattern = r'^\+?[0-9]{10,15}$'
        if not re.match(pattern, v):
            raise ValueError('Phone number must be in a valid format (10-15 digits, can start with +)')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        # Password validation
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
            
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one number
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        
        return v

class RestaurantRegistrationRequest(RegistrationRequest):
    restaurant_name: str = Field(..., min_length=1, max_length=255)
    restaurant_description: str = Field(..., min_length=1)
    cuisine_type: List[str] = Field(..., min_items=1)
    price_range: int = Field(..., ge=1, le=4)
    
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

class DriverRegistrationRequest(RegistrationRequest):
    vehicle_type: str = Field(..., pattern="^(car|motorcycle|bicycle|scooter)$")
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = Field(None, ge=1900, le=datetime.now().year + 1)
    license_plate: Optional[str] = None
    driver_license_number: str = Field(..., min_length=1)
    driver_license_expiry: date = Field(...)
    insurance_number: Optional[str] = None
    insurance_expiry: Optional[date] = None
    
    @validator('driver_license_expiry')
    def validate_license_expiry(cls, v):
        if v < datetime.now().date():
            raise ValueError('Driver license must not be expired')
        return v
    
    @validator('insurance_expiry')
    def validate_insurance_expiry(cls, v):
        if v is not None and v < datetime.now().date():
            raise ValueError('Insurance must not be expired')
        return v