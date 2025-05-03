from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from typing import Dict, List, Any, Optional

from app.core.auth import get_current_user
from app.core.redis import get_user_notifications, mark_notification_as_read, mark_all_notifications_as_read

router = APIRouter()

@router.get("")
async def get_notifications(
    limit: int = Query(20, ge=1, le=100, description="Number of notifications to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the current user's notifications.
    
    Returns a list of the user's notifications, with the most recent first.
    """
    notifications = await get_user_notifications(
        user_id=current_user["id"],
        limit=limit,
        offset=offset
    )
    
    return {
        "notifications": notifications,
        "count": len(notifications),
        "limit": limit,
        "offset": offset
    }

@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: str = Path(..., description="The ID of the notification to mark as read"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Mark a notification as read.
    
    The current user must be the owner of the notification.
    """
    success = await mark_notification_as_read(
        notification_id=notification_id,
        user_id=current_user["id"]
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or not owned by current user"
        )
    
    return {"success": True}

@router.put("/read-all")
async def mark_all_read(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Mark all of the current user's notifications as read.
    """
    count = await mark_all_notifications_as_read(
        user_id=current_user["id"]
    )
    
    return {
        "success": True,
        "count": count
    }