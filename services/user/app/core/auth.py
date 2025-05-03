from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import redis.asyncio as redis
import json
import uuid
import logging
from passlib.context import CryptContext

from app.core.config import settings
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 password bearer scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that the plain password matches the hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)

async def create_access_token(user_id: str, roles: List[str]) -> str:
    """Create a new JWT access token."""
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    
    # Ensure user_id is a string
    user_id_str = str(user_id) if user_id else None
    
    to_encode = {
        "sub": user_id_str,
        "exp": expire,
        "iat": datetime.utcnow(),
        "roles": roles,
        "jti": str(uuid.uuid4())
    }
    
    token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    
    # Store token in Redis
    redis_client = await get_redis_client()
    token_data = json.dumps({
        "user_id": user_id_str,
        "roles": roles,
        "exp": expire.timestamp()
    })
    
    await redis_client.setex(
        f"auth:token:{to_encode['jti']}", 
        int(expires_delta.total_seconds()), 
        token_data
    )
    
    return token

async def create_refresh_token(user_id: str) -> str:
    """Create a new JWT refresh token."""
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expire = datetime.utcnow() + expires_delta
    
    # Ensure user_id is a string
    user_id_str = str(user_id) if user_id else None
    
    jti = str(uuid.uuid4())
    to_encode = {
        "sub": user_id_str,
        "exp": expire,
        "iat": datetime.utcnow(),
        "token_type": "refresh",
        "jti": jti
    }
    
    token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    
    # Store refresh token in Redis
    redis_client = await get_redis_client()
    token_data = json.dumps({
        "user_id": user_id_str,
        "exp": expire.timestamp()
    })
    
    await redis_client.setex(
        f"auth:refresh_token:{jti}", 
        int(expires_delta.total_seconds()), 
        token_data
    )
    
    return token

async def validate_token(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Validate a JWT token and return the user data."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id: str = payload.get("sub")
        roles: List[str] = payload.get("roles", [])
        jti: str = payload.get("jti")
        
        if user_id is None or jti is None:
            raise credentials_exception
        
        # Check if token is in Redis
        redis_client = await get_redis_client()
        token_key = f"auth:token:{jti}"
        token_data = await redis_client.get(token_key)
        
        if not token_data:
            logger.warning(f"Token not found in Redis: {jti}")
            raise credentials_exception
        
        return {
            "user_id": user_id,
            "roles": roles,
            "jti": jti
        }
        
    except JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise credentials_exception

async def validate_refresh_token(refresh_token: str) -> Optional[str]:
    """Validate a refresh token and return the user_id if valid."""
    try:
        # Decode JWT token
        payload = jwt.decode(
            refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id: str = payload.get("sub")
        token_type: str = payload.get("token_type")
        jti: str = payload.get("jti")
        
        if user_id is None or token_type != "refresh" or jti is None:
            return None
        
        # Check if token is in Redis
        redis_client = await get_redis_client()
        token_key = f"auth:refresh_token:{jti}"
        token_data = await redis_client.get(token_key)
        
        if not token_data:
            logger.warning(f"Refresh token not found in Redis: {jti}")
            return None
        
        return user_id
        
    except JWTError as e:
        logger.error(f"Refresh token validation error: {str(e)}")
        return None

async def revoke_token(token: str) -> bool:
    """Revoke a JWT token."""
    try:
        # Decode JWT token
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        
        jti: str = payload.get("jti")
        
        if jti is None:
            return False
        
        # Delete token from Redis
        redis_client = await get_redis_client()
        token_key = f"auth:token:{jti}"
        deleted = await redis_client.delete(token_key)
        
        return deleted > 0
        
    except JWTError as e:
        logger.error(f"Revoke token error: {str(e)}")
        return False

async def revoke_refresh_token(refresh_token: str) -> bool:
    """Revoke a refresh token."""
    try:
        # Decode JWT token
        payload = jwt.decode(
            refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        
        jti: str = payload.get("jti")
        
        if jti is None:
            return False
        
        # Delete token from Redis
        redis_client = await get_redis_client()
        token_key = f"auth:refresh_token:{jti}"
        deleted = await redis_client.delete(token_key)
        
        return deleted > 0
        
    except JWTError as e:
        logger.error(f"Revoke refresh token error: {str(e)}")
        return False

async def get_user_roles(user_id: str) -> List[str]:
    """Get the roles for a user."""
    from app.models.user import UserRepository
    
    user_repo = UserRepository()
    roles = await user_repo.get_user_roles(user_id)
    return [role["name"] for role in roles]

# Check if a user has a specific role
def has_role(required_role: str):
    """Dependency to check if a user has a specific role."""
    async def check_role(user: Dict[str, Any] = Depends(validate_token)):
        if required_role not in user["roles"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required role: {required_role}"
            )
        return user
    return check_role

# Check if a user has any of the specified roles
def has_any_role(required_roles: List[str]):
    """Dependency to check if a user has any of the specified roles."""
    async def check_roles(user: Dict[str, Any] = Depends(validate_token)):
        if not any(role in user["roles"] for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have any of the required roles: {required_roles}"
            )
        return user
    return check_roles