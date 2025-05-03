from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, List, Optional, Any
import logging
import httpx
import json
from jose import jwt, JWTError

from app.core.config import settings
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer()

async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Validate JWT token and return user data.
    This is a simplified version that validates the token locally.
    In a real-world scenario, you might want to call the User service to validate the token.
    """
    token = credentials.credentials
    
    # Try to get user info from Redis cache
    redis_client = await get_redis_client()
    cached_user_info = await redis_client.get(f"auth:token:{token}")
    
    if cached_user_info:
        return json.loads(cached_user_info)
    
    # If not in cache, validate the token
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id = payload.get("sub")
        roles = payload.get("roles", [])
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Create user info
        user_info = {
            "user_id": user_id,
            "roles": roles
        }
        
        # Cache the user info in Redis
        await redis_client.setex(
            f"auth:token:{token}",
            3600,  # 1 hour TTL
            json.dumps(user_info)
        )
        
        return user_info
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def has_role(required_role: str):
    """Check if user has a specific role."""
    async def check_role(user_info: Dict[str, Any] = Depends(validate_token)):
        if required_role not in user_info.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {required_role} required",
            )
        return user_info
    return check_role

def has_any_role(required_roles: List[str]):
    """Check if user has any of the specified roles."""
    async def check_roles(user_info: Dict[str, Any] = Depends(validate_token)):
        user_roles = set(user_info.get("roles", []))
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles is required: {', '.join(required_roles)}",
            )
        return user_info
    return check_roles

async def is_restaurant_owner(restaurant_id: str, user_id: str) -> bool:
    """Check if a user is the owner of a restaurant."""
    from app.models.restaurant import RestaurantRepository
    
    restaurant_repo = RestaurantRepository()
    restaurant = await restaurant_repo.get_restaurant_by_id(restaurant_id)
    
    if not restaurant:
        return False
        
    return restaurant.get("user_id") == user_id

def restaurant_owner_or_admin(restaurant_id_param: str = "restaurant_id"):
    """Check if user is restaurant owner or admin."""
    async def check_ownership(
        user_info: Dict[str, Any] = Depends(validate_token),
        restaurant_id: str = Depends(lambda: restaurant_id_param)
    ):
        # If user is admin, allow access
        if "admin" in user_info.get("roles", []):
            return user_info
            
        # If user is restaurant owner, check if they own this restaurant
        if "restaurant" in user_info.get("roles", []):
            is_owner = await is_restaurant_owner(restaurant_id, user_info.get("user_id"))
            if is_owner:
                return user_info
                
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this restaurant",
        )
    return check_ownership