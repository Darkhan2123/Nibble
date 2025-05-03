from fastapi import APIRouter, Depends, Path, Query, HTTPException, status
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.auth import get_current_user, get_current_admin
from app.models.support_ticket import SupportTicketRepository
from app.schemas.support_ticket import (
    TicketCreate, TicketStatusUpdate, TicketAssign, TicketComment,
    TicketResponse, TicketDetailResponse, TicketListResponse, TicketCommentResponse
)

router = APIRouter()
ticket_repository = SupportTicketRepository()

@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: TicketCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new support ticket.
    
    This endpoint allows a user to create a new support ticket.
    """
    ticket = await ticket_repository.create_ticket(
        user_id=current_user["id"],
        subject=ticket_data.subject,
        description=ticket_data.description,
        order_id=ticket_data.order_id,
        priority=ticket_data.priority
    )
    
    return ticket

@router.get("", response_model=TicketListResponse)
async def get_tickets(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    limit: int = Query(50, ge=1, le=100, description="Number of tickets to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get a list of support tickets.
    
    This endpoint allows an admin to retrieve a list of support tickets.
    """
    tickets = await ticket_repository.get_tickets(
        status=status,
        priority=priority,
        limit=limit,
        offset=offset
    )
    
    return {
        "tickets": tickets,
        "total": len(tickets),  # In a real app, you'd get the total count from the database
        "limit": limit,
        "offset": offset
    }

@router.get("/my", response_model=TicketListResponse)
async def get_my_tickets(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Number of tickets to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a list of the current user's support tickets.
    
    This endpoint allows a user to retrieve a list of their own support tickets.
    """
    tickets = await ticket_repository.get_user_tickets(
        user_id=current_user["id"],
        status=status,
        limit=limit,
        offset=offset
    )
    
    return {
        "tickets": tickets,
        "total": len(tickets),  # In a real app, you'd get the total count from the database
        "limit": limit,
        "offset": offset
    }

@router.get("/assigned", response_model=TicketListResponse)
async def get_assigned_tickets(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Number of tickets to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Get a list of support tickets assigned to the current admin.
    
    This endpoint allows an admin to retrieve a list of support tickets assigned to them.
    """
    tickets = await ticket_repository.get_tickets(
        status=status,
        assigned_to=current_admin["id"],
        limit=limit,
        offset=offset
    )
    
    return {
        "tickets": tickets,
        "total": len(tickets),  # In a real app, you'd get the total count from the database
        "limit": limit,
        "offset": offset
    }

@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_id: str = Path(..., description="The ID of the ticket"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a support ticket by ID.
    
    This endpoint allows a user to retrieve a support ticket by its ID.
    Users can only get their own tickets, while admins can get any ticket.
    """
    ticket = await ticket_repository.get_ticket_by_id(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Check permissions
    is_admin = current_user.get("role") == "admin"
    is_owner = current_user["id"] == ticket["user_id"]
    
    if not (is_admin or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this ticket"
        )
    
    # Get comments
    include_internal = is_admin  # Only admins can see internal comments
    comments = await ticket_repository.get_ticket_comments(
        ticket_id=ticket_id,
        include_internal=include_internal
    )
    
    # Add comments to response
    ticket_response = {**ticket, "comments": comments}
    
    return ticket_response

@router.put("/{ticket_id}/status", response_model=TicketResponse)
async def update_ticket_status(
    status_data: TicketStatusUpdate,
    ticket_id: str = Path(..., description="The ID of the ticket to update"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Update a ticket's status.
    
    This endpoint allows an admin to update a ticket's status.
    """
    updated_ticket = await ticket_repository.update_ticket_status(
        ticket_id=ticket_id,
        status=status_data.status,
        admin_id=current_admin["id"],
        resolution_notes=status_data.resolution_notes
    )
    
    if not updated_ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    return updated_ticket

@router.put("/{ticket_id}/assign", response_model=TicketResponse)
async def assign_ticket(
    assign_data: TicketAssign,
    ticket_id: str = Path(..., description="The ID of the ticket to assign"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Assign a ticket to an admin.
    
    This endpoint allows an admin to assign a ticket to another admin.
    """
    updated_ticket = await ticket_repository.assign_ticket(
        ticket_id=ticket_id,
        admin_id=assign_data.admin_id
    )
    
    if not updated_ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    return updated_ticket

@router.post("/{ticket_id}/comments", response_model=TicketCommentResponse)
async def add_comment(
    comment_data: TicketComment,
    ticket_id: str = Path(..., description="The ID of the ticket"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Add a comment to a ticket.
    
    This endpoint allows a user to add a comment to a support ticket.
    Only admins can add internal comments.
    """
    # Check if ticket exists
    ticket = await ticket_repository.get_ticket_by_id(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Check permissions
    is_admin = current_user.get("role") == "admin"
    is_owner = current_user["id"] == ticket["user_id"]
    
    if not (is_admin or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to comment on this ticket"
        )
    
    # Only admins can add internal comments
    if comment_data.is_internal and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can add internal comments"
        )
    
    try:
        comment = await ticket_repository.add_comment(
            ticket_id=ticket_id,
            user_id=current_user["id"],
            comment=comment_data.comment,
            is_internal=comment_data.is_internal
        )
        
        return comment
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{ticket_id}/comments", response_model=List[TicketCommentResponse])
async def get_comments(
    ticket_id: str = Path(..., description="The ID of the ticket"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get comments for a ticket.
    
    This endpoint allows a user to retrieve comments for a support ticket.
    Only admins can see internal comments.
    """
    # Check if ticket exists
    ticket = await ticket_repository.get_ticket_by_id(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Check permissions
    is_admin = current_user.get("role") == "admin"
    is_owner = current_user["id"] == ticket["user_id"]
    
    if not (is_admin or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view comments on this ticket"
        )
    
    # Only admins can see internal comments
    include_internal = is_admin
    
    comments = await ticket_repository.get_ticket_comments(
        ticket_id=ticket_id,
        include_internal=include_internal
    )
    
    return comments