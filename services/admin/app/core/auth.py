import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Security scheme for JWT authentication
security = HTTPBearer()

async def get_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get the JWT token from the request."""
    return credentials.credentials

async def decode_token(token: str = Depends(get_token)) -> Dict[str, Any]:
    """Decode and verify the JWT token."""
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.PyJWTError as e:
        logger.error(f"JWT token error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(payload: Dict[str, Any] = Depends(decode_token)) -> Dict[str, Any]:
    """Get the current user from the JWT token."""
    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Return user details from token payload
    user = {
        "id": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role", "customer"),
    }
    
    return user

async def get_current_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Check if the current user is an admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required.",
        )
    return current_user