from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class TicketBase(BaseModel):
    """Base model for support ticket data."""
    subject: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    order_id: Optional[str] = None
    priority: str = Field("medium", description="Priority: low, medium, high, urgent")

class TicketCreate(TicketBase):
    """Model for creating a new support ticket."""
    pass

class TicketStatusUpdate(BaseModel):
    """Model for updating a ticket's status."""
    status: str = Field(..., description="Status: open, in_progress, resolved, closed")
    resolution_notes: Optional[str] = None

class TicketAssign(BaseModel):
    """Model for assigning a ticket to an admin."""
    admin_id: str

class TicketComment(BaseModel):
    """Model for adding a comment to a ticket."""
    comment: str = Field(..., min_length=1)
    is_internal: bool = False

class TicketCommentResponse(TicketComment):
    """Model for ticket comment response."""
    id: str
    ticket_id: str
    user_id: str
    created_at: datetime
    
    class Config:
        orm_mode = True

class TicketResponse(TicketBase):
    """Model for support ticket response."""
    id: str
    user_id: str
    status: str
    assigned_to: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class TicketListResponse(BaseModel):
    """Model for list of support tickets."""
    tickets: List[TicketResponse]
    total: int
    limit: int
    offset: int

class TicketDetailResponse(TicketResponse):
    """Model for detailed support ticket response."""
    comments: List[TicketCommentResponse] = []