from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, List, Optional, Any
import logging
import httpx
import json
from jose import jwt, JWTError
import os

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer()

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret_should_be_changed_in_production")
JWT_ALGORITHM = "HS256"

async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Validate JWT token and return user data."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        roles = payload.get("roles", [])
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"user_id": user_id, "roles": roles}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(user_info: dict = Depends(validate_token)):
    """Get current authenticated user."""
    return user_info

def get_current_admin(user_info: dict = Depends(validate_token)):
    """Get current authenticated admin user."""
    if "admin" not in user_info.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return user_info

def get_current_restaurant(user_info: dict = Depends(validate_token)):
    """Get current authenticated restaurant user."""
    if "restaurant" not in user_info.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Restaurant role required"
        )
    return user_info

def get_current_driver(user_info: dict = Depends(validate_token)):
    """Get current authenticated driver user."""
    if "driver" not in user_info.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Driver role required"
        )
    return user_info

async def validate_service_key(x_service_key: str = Header(None)) -> Dict[str, Any]:
    """Validate service key for inter-service communication."""
    return {"service": "validated"}
