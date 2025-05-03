from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional
from datetime import datetime, date

class UserBase(BaseModel):
    email: EmailStr
    phone_number: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    profile_picture_url: Optional[str] = None
    is_active: bool = True

class UserResponse(UserBase):
    id: str
    roles: List[str]
    created_at: datetime
    updated_at: datetime

class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    profile_picture_url: Optional[str] = None
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v is None:
            return v
        # Simple validation, could be improved
        if not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValueError('Phone number must contain only digits, +, -, and spaces')
        return v

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_password(cls, v):
        # Password validation
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserRoleUpdateRequest(BaseModel):
    roles: List[str]

class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    skip: int
    limit: int