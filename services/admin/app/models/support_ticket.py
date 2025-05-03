import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncpg

from app.core.database import get_connection, transaction, fetch_one, fetch_all, execute

logger = logging.getLogger(__name__)

class SupportTicketRepository:
    """Repository for support ticket-related database operations."""
    
    async def create_ticket(
        self,
        user_id: str,
        subject: str,
        description: str,
        order_id: Optional[str] = None,
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """Create a new support ticket."""
        async with transaction() as tx:
            ticket_id = str(uuid.uuid4())
            
            query = """
            INSERT INTO admin_service.support_tickets (
                id, user_id, order_id, subject, description,
                status, priority, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            RETURNING *
            """
            
            try:
                async with get_connection() as conn:
                    ticket = await conn.fetchrow(
                        query,
                        ticket_id,
                        user_id,
                        order_id,
                        subject,
                        description,
                        "open",  # Initial status is open
                        priority
                    )
                    
                    return dict(ticket)
                    
            except Exception as e:
                logger.error(f"Error creating support ticket: {e}")
                raise
    
    async def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get a support ticket by ID."""
        query = """
        SELECT * FROM admin_service.support_tickets WHERE id = $1
        """
        
        return await fetch_one(query, ticket_id)
    
    async def get_user_tickets(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get support tickets for a user."""
        conditions = ["user_id = $1"]
        params = [user_id]
        param_index = 2
        
        if status:
            conditions.append(f"status = ${param_index}")
            params.append(status)
            param_index += 1
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
        SELECT * FROM admin_service.support_tickets
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_index}
        OFFSET ${param_index + 1}
        """
        
        params.extend([limit, offset])
        
        return await fetch_all(query, *params)
    
    async def get_tickets(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all support tickets, with optional filters."""
        conditions = []
        params = []
        param_index = 1
        
        if status:
            conditions.append(f"status = ${param_index}")
            params.append(status)
            param_index += 1
            
        if priority:
            conditions.append(f"priority = ${param_index}")
            params.append(priority)
            param_index += 1
            
        if assigned_to:
            conditions.append(f"assigned_to = ${param_index}")
            params.append(assigned_to)
            param_index += 1
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
        SELECT * FROM admin_service.support_tickets
        {where_clause}
        ORDER BY 
            CASE 
                WHEN priority = 'urgent' THEN 1
                WHEN priority = 'high' THEN 2
                WHEN priority = 'medium' THEN 3
                WHEN priority = 'low' THEN 4
                ELSE 5
            END,
            created_at ASC
        LIMIT ${param_index}
        OFFSET ${param_index + 1}
        """
        
        params.extend([limit, offset])
        
        return await fetch_all(query, *params)
    
    async def update_ticket_status(
        self,
        ticket_id: str,
        status: str,
        admin_id: Optional[str] = None,
        resolution_notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a ticket's status."""
        # Check if ticket exists
        existing_ticket = await self.get_ticket_by_id(ticket_id)
        
        if not existing_ticket:
            logger.error(f"Ticket {ticket_id} not found")
            return None
        
        # Valid status transitions
        valid_status = ["open", "in_progress", "resolved", "closed"]
        
        if status not in valid_status:
            logger.error(f"Invalid status: {status}")
            raise ValueError(f"Invalid status: {status}")
        
        # Build update query
        update_fields = ["status = $1", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]
        param_index = 2
        
        if status in ["resolved", "closed"] and resolution_notes:
            update_fields.append(f"resolution_notes = ${param_index}")
            params.append(resolution_notes)
            param_index += 1
            
            # Also set resolved_at for resolved/closed status
            update_fields.append("resolved_at = CURRENT_TIMESTAMP")
        
        if admin_id and status == "in_progress":
            # Assign the ticket to the admin
            update_fields.append(f"assigned_to = ${param_index}")
            params.append(admin_id)
            param_index += 1
        
        # Build and execute the query
        update_clause = ", ".join(update_fields)
        params.append(ticket_id)
        
        query = f"""
        UPDATE admin_service.support_tickets
        SET {update_clause}
        WHERE id = ${param_index}
        RETURNING *
        """
        
        return await fetch_one(query, *params)
    
    async def assign_ticket(
        self,
        ticket_id: str,
        admin_id: str
    ) -> Optional[Dict[str, Any]]:
        """Assign a ticket to an admin."""
        # Check if ticket exists
        existing_ticket = await self.get_ticket_by_id(ticket_id)
        
        if not existing_ticket:
            logger.error(f"Ticket {ticket_id} not found")
            return None
        
        # Update the ticket
        query = """
        UPDATE admin_service.support_tickets
        SET 
            assigned_to = $1,
            status = CASE WHEN status = 'open' THEN 'in_progress' ELSE status END,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $2
        RETURNING *
        """
        
        return await fetch_one(query, admin_id, ticket_id)
    
    async def add_comment(
        self,
        ticket_id: str,
        user_id: str,
        comment: str,
        is_internal: bool = False
    ) -> Dict[str, Any]:
        """Add a comment to a support ticket."""
        # Check if ticket exists
        existing_ticket = await self.get_ticket_by_id(ticket_id)
        
        if not existing_ticket:
            logger.error(f"Ticket {ticket_id} not found")
            raise ValueError(f"Ticket {ticket_id} not found")
        
        # Create the comment
        comment_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO admin_service.ticket_comments (
            id, ticket_id, user_id, comment, is_internal, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, CURRENT_TIMESTAMP
        )
        RETURNING *
        """
        
        try:
            async with get_connection() as conn:
                comment_row = await conn.fetchrow(
                    query,
                    comment_id,
                    ticket_id,
                    user_id,
                    comment,
                    is_internal
                )
                
                # Update ticket updated_at time
                await conn.execute(
                    """
                    UPDATE admin_service.support_tickets
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                    """,
                    ticket_id
                )
                
                return dict(comment_row)
                
        except Exception as e:
            logger.error(f"Error adding comment to ticket: {e}")
            raise
    
    async def get_ticket_comments(
        self,
        ticket_id: str,
        include_internal: bool = False
    ) -> List[Dict[str, Any]]:
        """Get comments for a support ticket."""
        # Build the query based on whether to include internal comments
        where_clause = "WHERE ticket_id = $1"
        if not include_internal:
            where_clause += " AND is_internal = FALSE"
        
        query = f"""
        SELECT * FROM admin_service.ticket_comments
        {where_clause}
        ORDER BY created_at
        """
        
        return await fetch_all(query, ticket_id)