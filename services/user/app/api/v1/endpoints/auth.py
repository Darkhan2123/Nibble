from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import Dict, Any, List, Optional, Union
import logging
from uuid import UUID
from asyncpg.pool import PoolConnectionProxy

from app.core.auth import (
    verify_password, create_access_token, create_refresh_token,
    validate_token, validate_refresh_token, revoke_token,
    get_password_hash
)
from app.core.database import get_db, create_transaction
from app.models.user import UserRepository
from app.models.address import AddressRepository
from app.models.profile import ProfileRepository
from app.schemas.auth import (
    LoginResponse, RefreshTokenRequest, RefreshTokenResponse,
    RegistrationRequest, RestaurantRegistrationRequest, DriverRegistrationRequest,
    TokenPayload, UserResponse
)
from app.core.kafka import publish_user_created
from app.core.maps import geocode_address

logger = logging.getLogger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

@router.post("/login", response_model=LoginResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible login endpoint.
    """
    user_repo = UserRepository()
    
    # First try to find the user by email
    user = await user_repo.get_user_by_email(form_data.username)
    
    # If not found by email, try phone number
    if not user:
        user = await user_repo.get_user_by_phone(form_data.username)
    
    if not user:
        logger.warning(f"Login attempt with non-existent credentials: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user["password_hash"]):
        logger.warning(f"Failed login attempt for user: {user['id']}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user["is_active"]:
        logger.warning(f"Login attempt for inactive user: {user['id']}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    
    # Get user roles
    roles = await user_repo.get_user_roles(user["id"])
    role_names = [role["name"] for role in roles]
    
    # Create tokens
    access_token = await create_access_token(user["id"], role_names)
    refresh_token = await create_refresh_token(user["id"])
    
    logger.info(f"User logged in: {user['id']}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "phone_number": user["phone_number"],
            "roles": role_names
        }
    }

@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh an access token using a valid refresh token.
    """
    user_id = await validate_refresh_token(request.refresh_token)
    
    if not user_id:
        logger.warning("Invalid refresh token attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user details
    user_repo = UserRepository()
    user = await user_repo.get_user_by_id(user_id)
    
    if not user:
        logger.warning(f"Refresh token for deleted user: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if not user["is_active"]:
        logger.warning(f"Refresh token for inactive user: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    
    # Get user roles
    roles = await user_repo.get_user_roles(user_id)
    role_names = [role["name"] for role in roles]
    
    # Create new tokens
    access_token = await create_access_token(user_id, role_names)
    new_refresh_token = await create_refresh_token(user_id)
    
    # Optionally revoke the old refresh token
    await revoke_token(request.refresh_token)
    
    logger.info(f"Tokens refreshed for user: {user_id}")
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }

@router.post("/logout")
async def logout(token: Dict[str, Any] = Depends(validate_token)):
    """
    Logout a user by revoking their token.
    """
    success = await revoke_token(token["jti"])
    
    if not success:
        logger.warning(f"Failed to revoke token for user: {token['user_id']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout",
        )
    
    logger.info(f"User logged out: {token['user_id']}")
    
    return {"message": "Successfully logged out"}

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegistrationRequest):
    """
    Register a new customer user.
    """
    user_repo = UserRepository()
    address_repo = AddressRepository()
    profile_repo = ProfileRepository()
    
    # Check if email already exists
    existing_email = await user_repo.get_user_by_email(request.email)
    if existing_email:
        logger.warning(f"Registration attempt with existing email: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    
    # Check if phone already exists
    existing_phone = await user_repo.get_user_by_phone(request.phone_number)
    if existing_phone:
        logger.warning(f"Registration attempt with existing phone: {request.phone_number}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered",
        )
    
    try:
        async with create_transaction() as conn:
            # Create the user with the customer role
            user = await user_repo.create_user(
                password=request.password,
                email=request.email,
                phone_number=request.phone_number,
                first_name=request.first_name,
                last_name=request.last_name,
                date_of_birth=request.date_of_birth,
                profile_picture_url=None,
            )
            
            # Create an address for the user
            address = await address_repo.create_address(
                user_id=user["id"],
                address_line1=request.address.address_line1,
                address_line2=request.address.address_line2,
                city=request.address.city,
                state=request.address.state,
                postal_code=request.address.postal_code,
                country=request.address.country,
                address_type=request.address.address_type,
                is_default=True,
                latitude=request.address.latitude,
                longitude=request.address.longitude,
            )
            
            # Create or get customer profile
            profile = await profile_repo.get_customer_profile(user["id"])
            
            # Get user roles
            roles = await user_repo.get_user_roles(user["id"])
            role_names = [role["name"] for role in roles]
            
            # Publish user created event
            await publish_user_created({
                "user_id": str(user["id"]),
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "roles": role_names
            })
            
            logger.info(f"New customer user registered: {user['id']}")
            
            # Create token for immediate login
            access_token = await create_access_token(user["id"], role_names)
            refresh_token = await create_refresh_token(user["id"])
            
            return {
                "id": str(user["id"]),
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "phone_number": user["phone_number"],
                "roles": role_names,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "message": "User registered successfully"
            }
    except ValueError as e:
        logger.error(f"Error registering user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error registering user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )

@router.post("/register/restaurant", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_restaurant(request: RestaurantRegistrationRequest):
    """
    Register a new restaurant user.
    """
    user_repo = UserRepository()
    address_repo = AddressRepository()
    
    # Check if email already exists
    existing_email = await user_repo.get_user_by_email(request.email)
    if existing_email:
        logger.warning(f"Registration attempt with existing email: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    
    # Check if phone already exists
    existing_phone = await user_repo.get_user_by_phone(request.phone_number)
    if existing_phone:
        logger.warning(f"Registration attempt with existing phone: {request.phone_number}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered",
        )
    
    try:
        async with create_transaction() as conn:
            # Create the user
            user = await user_repo.create_user(
                password=request.password,
                email=request.email,
                phone_number=request.phone_number,
                first_name=request.first_name,
                last_name=request.last_name,
                date_of_birth=request.date_of_birth,
                profile_picture_url=None,
            )
            
            # Create an address for the restaurant
            address = await address_repo.create_address(
                user_id=user["id"],
                address_line1=request.address.address_line1,
                address_line2=request.address.address_line2,
                city=request.address.city,
                state=request.address.state,
                postal_code=request.address.postal_code,
                country=request.address.country,
                address_type="business",
                is_default=True,
                latitude=request.address.latitude,
                longitude=request.address.longitude,
            )
            
            # Add restaurant role
            await user_repo.add_user_role(user["id"], "restaurant")
            
            # Get user roles
            roles = await user_repo.get_user_roles(user["id"])
            role_names = [role["name"] for role in roles]
            
            # Create restaurant profile in restaurant service via Kafka
            restaurant_data = {
                "user_id": str(user["id"]),
                "name": request.restaurant_name,
                "description": request.restaurant_description,
                "cuisine_type": request.cuisine_type,
                "price_range": request.price_range,
                "phone_number": request.phone_number,
                "email": request.email,
                "address_id": address["id"],
            }
            
            # Publish restaurant created event
            await publish_user_created({
                "user_id": str(user["id"]),
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "roles": role_names,
                "restaurant_data": restaurant_data
            })
            
            logger.info(f"New restaurant user registered: {user['id']}")
            
            # Create token for immediate login
            access_token = await create_access_token(user["id"], role_names)
            refresh_token = await create_refresh_token(user["id"])
            
            return {
                "id": str(user["id"]),
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "phone_number": user["phone_number"],
                "roles": role_names,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "message": "Restaurant user registered successfully"
            }
    except ValueError as e:
        logger.error(f"Error registering restaurant user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error registering restaurant user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )

@router.post("/register/driver", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_driver(request: DriverRegistrationRequest):
    """
    Register a new driver user.
    """
    user_repo = UserRepository()
    address_repo = AddressRepository()
    
    # Check if email already exists
    existing_email = await user_repo.get_user_by_email(request.email)
    if existing_email:
        logger.warning(f"Registration attempt with existing email: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    
    # Check if phone already exists
    existing_phone = await user_repo.get_user_by_phone(request.phone_number)
    if existing_phone:
        logger.warning(f"Registration attempt with existing phone: {request.phone_number}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered",
        )
    
    try:
        async with create_transaction() as conn:
            # Create the user
            user = await user_repo.create_user(
                password=request.password,
                email=request.email,
                phone_number=request.phone_number,
                first_name=request.first_name,
                last_name=request.last_name,
                date_of_birth=request.date_of_birth,
                profile_picture_url=None,
            )
            
            # Create an address for the driver
            address = await address_repo.create_address(
                user_id=user["id"],
                address_line1=request.address.address_line1,
                address_line2=request.address.address_line2,
                city=request.address.city,
                state=request.address.state,
                postal_code=request.address.postal_code,
                country=request.address.country,
                address_type=request.address.address_type,
                is_default=True,
                latitude=request.address.latitude,
                longitude=request.address.longitude,
            )
            
            # Add driver role
            await user_repo.add_user_role(user["id"], "driver")
            
            # Get user roles
            roles = await user_repo.get_user_roles(user["id"])
            role_names = [role["name"] for role in roles]
            
            # Create driver profile in driver service via Kafka
            driver_data = {
                "user_id": str(user["id"]),
                "vehicle_type": request.vehicle_type,
                "vehicle_make": request.vehicle_make,
                "vehicle_model": request.vehicle_model,
                "vehicle_year": request.vehicle_year,
                "license_plate": request.license_plate,
                "driver_license_number": request.driver_license_number,
                "driver_license_expiry": request.driver_license_expiry.isoformat(),
                "insurance_number": request.insurance_number,
                "insurance_expiry": request.insurance_expiry.isoformat() if request.insurance_expiry else None,
            }
            
            # Publish driver created event
            await publish_user_created({
                "user_id": str(user["id"]),
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "roles": role_names,
                "driver_data": driver_data
            })
            
            logger.info(f"New driver user registered: {user['id']}")
            
            # Create token for immediate login
            access_token = await create_access_token(user["id"], role_names)
            refresh_token = await create_refresh_token(user["id"])
            
            return {
                "id": str(user["id"]),
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "phone_number": user["phone_number"],
                "roles": role_names,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "message": "Driver user registered successfully"
            }
    except ValueError as e:
        logger.error(f"Error registering driver user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error registering driver user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user(token: Dict[str, Any] = Depends(validate_token)):
    """
    Get current authenticated user info.
    """
    user_repo = UserRepository()
    user = await user_repo.get_user_by_id(token["user_id"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Get user roles
    roles = await user_repo.get_user_roles(user["id"])
    role_names = [role["name"] for role in roles]
    
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "phone_number": user["phone_number"],
        "roles": role_names
    }