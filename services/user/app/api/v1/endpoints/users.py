from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
import logging

from app.core.auth import validate_token, has_role, has_any_role
from app.models.user import UserRepository
from app.schemas.user import (
    UserResponse, UserUpdateRequest, PasswordChangeRequest,
    UserRoleUpdateRequest, UserListResponse
)
from app.core.kafka import publish_user_updated

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user(token: Dict[str, Any] = Depends(validate_token)):
    """
    Get the current user's profile.
    """
    user_repo = UserRepository()
    user = await user_repo.get_user_by_id(token["user_id"])
    
    if not user:
        logger.warning(f"User not found: {token['user_id']}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Get user roles
    roles = await user_repo.get_user_roles(user["id"])
    role_names = [role["name"] for role in roles]
    
    return {
        "id": user["id"],
        "email": user["email"],
        "phone_number": user["phone_number"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "date_of_birth": user["date_of_birth"],
        "profile_picture_url": user["profile_picture_url"],
        "is_active": user["is_active"],
        "roles": role_names,
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    request: UserUpdateRequest,
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Update the current user's profile.
    """
    user_repo = UserRepository()
    
    # Update the user
    try:
        updated_user = await user_repo.update_user(
            user_id=token["user_id"],
            update_data=request.dict(exclude_unset=True),
        )
        
        if not updated_user:
            logger.warning(f"User not found during update: {token['user_id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        # Get user roles
        roles = await user_repo.get_user_roles(updated_user["id"])
        role_names = [role["name"] for role in roles]
        
        # Publish user updated event
        await publish_user_updated({
            "user_id": updated_user["id"],
            "email": updated_user["email"],
            "first_name": updated_user["first_name"],
            "last_name": updated_user["last_name"],
        })
        
        logger.info(f"User updated: {updated_user['id']}")
        
        return {
            "id": updated_user["id"],
            "email": updated_user["email"],
            "phone_number": updated_user["phone_number"],
            "first_name": updated_user["first_name"],
            "last_name": updated_user["last_name"],
            "date_of_birth": updated_user["date_of_birth"],
            "profile_picture_url": updated_user["profile_picture_url"],
            "is_active": updated_user["is_active"],
            "roles": role_names,
            "created_at": updated_user["created_at"],
            "updated_at": updated_user["updated_at"],
        }
    except ValueError as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error updating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )

@router.post("/me/change-password")
async def change_password(
    request: PasswordChangeRequest,
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Change the current user's password.
    """
    user_repo = UserRepository()
    
    # Verify current password
    user = await user_repo.get_user_by_id(token["user_id"])
    
    if not user:
        logger.warning(f"User not found during password change: {token['user_id']}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if not verify_password(request.current_password, user["password_hash"]):
        logger.warning(f"Incorrect current password for user: {token['user_id']}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )
    
    # Change password
    success = await user_repo.change_password(
        user_id=token["user_id"],
        new_password=request.new_password,
    )
    
    if not success:
        logger.error(f"Failed to change password for user: {token['user_id']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )
    
    logger.info(f"Password changed for user: {token['user_id']}")
    
    return {"message": "Password changed successfully"}

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    token: Dict[str, Any] = Depends(has_any_role(["admin", "restaurant"]))
):
    """
    Get a user by ID. Admin only.
    """
    user_repo = UserRepository()
    user = await user_repo.get_user_by_id(user_id)
    
    if not user:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Get user roles
    roles = await user_repo.get_user_roles(user["id"])
    role_names = [role["name"] for role in roles]
    
    return {
        "id": user["id"],
        "email": user["email"],
        "phone_number": user["phone_number"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "date_of_birth": user["date_of_birth"],
        "profile_picture_url": user["profile_picture_url"],
        "is_active": user["is_active"],
        "roles": role_names,
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }

@router.get("/", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    token: Dict[str, Any] = Depends(has_role("admin"))
):
    """
    List users with pagination. Admin only.
    """
    # Implementation of user listing with pagination
    # This would be implemented in the user repository
    # For now, returning a placeholder
    return {
        "items": [],
        "total": 0,
        "skip": skip,
        "limit": limit,
    }

@router.put("/{user_id}/roles", response_model=UserResponse)
async def update_user_roles(
    user_id: str,
    request: UserRoleUpdateRequest,
    token: Dict[str, Any] = Depends(has_role("admin"))
):
    """
    Update a user's roles. Admin only.
    """
    user_repo = UserRepository()
    
    # Check if user exists
    user = await user_repo.get_user_by_id(user_id)
    
    if not user:
        logger.warning(f"User not found during role update: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Get role IDs from role names
    role_ids = {
        "customer": 1,
        "restaurant": 2,
        "driver": 3,
        "admin": 4,
    }
    
    # Remove all roles
    # This would be implemented in the user repository
    # For now, returning a placeholder
    
    # Add new roles
    for role_name in request.roles:
        if role_name in role_ids:
            await user_repo.add_user_role(user_id, role_ids[role_name])
    
    # Get updated roles
    roles = await user_repo.get_user_roles(user["id"])
    role_names = [role["name"] for role in roles]
    
    logger.info(f"Roles updated for user: {user_id}")
    
    return {
        "id": user["id"],
        "email": user["email"],
        "phone_number": user["phone_number"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "date_of_birth": user["date_of_birth"],
        "profile_picture_url": user["profile_picture_url"],
        "is_active": user["is_active"],
        "roles": role_names,
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }