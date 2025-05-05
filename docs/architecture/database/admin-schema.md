# Admin Service Database Schema

This document details the database schema for the Admin Service in the Nibble platform. The Admin Service manages administrative functions including support tickets, promotions, and system-wide configurations.

## Schema Overview

The Admin Service uses the `admin_service` schema in the shared PostgreSQL database. This schema contains tables related to administrative functions, system management, and customer support.

## Entity Relationship Diagram

```
+----------------------+       +------------------------+       +------------------------+
|                      |       |                        |       |                        |
| support_tickets      |       | ticket_comments        |       | promotions             |
|                      |       |                        |       |                        |
+----------------------+       +------------------------+       +------------------------+
| id (PK)              |       | id (PK)                |       | id (PK)                |
| user_id              |----+  | ticket_id (FK)      ---+--+    | name                   |
| order_id             |    |  | user_id                |  |    | description            |
| subject              |    |  | comment                |  |    | promo_code             |
| description          |    |  | is_internal            |  |    | discount_type          |
| status               |    |  | created_at             |  |    | discount_value         |
| priority             |    |  +------------------------+  |    | min_order_amount       |
| assigned_to          |    |                              |    | max_discount_amount    |
| resolved_at          |    +------------------------------+    | start_date             |
| resolution_notes     |                                        | end_date               |
| created_at           |                                        | is_active              |
| updated_at           |                                        | usage_limit            |
+----------------------+                                        | current_usage          |
                                                                | applies_to             |
+----------------------+                                        | applies_to_ids         |
|                      |                                        | created_by             |
| user_promotions      |                                        | created_at             |
|                      |                                        | updated_at             |
+----------------------+                                        +------------------------+
| id (PK)              |                                        |
| user_id              |                                        |
| promotion_id (FK) ---|----------------------------------------+
| usage_count          |
| first_used_at        |
| last_used_at         |
+----------------------+
```

## Table Definitions

### support_tickets

The `support_tickets` table stores customer support requests and their current status.

```sql
CREATE TABLE IF NOT EXISTS admin_service.support_tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    order_id UUID,
    subject VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'open', -- 'open', 'in_progress', 'resolved', 'closed'
    priority VARCHAR(50) DEFAULT 'medium', -- 'low', 'medium', 'high', 'urgent'
    assigned_to UUID,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### Indexes
```sql
CREATE INDEX IF NOT EXISTS support_tickets_user_id_idx ON admin_service.support_tickets(user_id);
CREATE INDEX IF NOT EXISTS support_tickets_assigned_to_idx ON admin_service.support_tickets(assigned_to);
CREATE INDEX IF NOT EXISTS support_tickets_status_idx ON admin_service.support_tickets(status);
CREATE INDEX IF NOT EXISTS support_tickets_priority_idx ON admin_service.support_tickets(priority);
CREATE INDEX IF NOT EXISTS support_tickets_created_at_idx ON admin_service.support_tickets(created_at);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key, unique identifier for the ticket |
| user_id | UUID | ID of the user who created the ticket |
| order_id | UUID | Optional reference to a specific order (NULL if not order-related) |
| subject | VARCHAR(255) | Short summary of the ticket issue |
| description | TEXT | Detailed description of the issue |
| status | VARCHAR(50) | Current status of the ticket ('open', 'in_progress', 'resolved', 'closed') |
| priority | VARCHAR(50) | Priority level ('low', 'medium', 'high', 'urgent') |
| assigned_to | UUID | ID of the admin user assigned to handle the ticket (NULL if unassigned) |
| resolved_at | TIMESTAMP | When the ticket was resolved (NULL if not resolved) |
| resolution_notes | TEXT | Notes explaining how the issue was resolved (NULL if not resolved) |
| created_at | TIMESTAMP | When the ticket was created |
| updated_at | TIMESTAMP | When the ticket was last updated |

### ticket_comments

The `ticket_comments` table stores the communication thread for support tickets, including both customer and admin responses.

```sql
CREATE TABLE IF NOT EXISTS admin_service.ticket_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID REFERENCES admin_service.support_tickets(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    comment TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### Indexes
```sql
CREATE INDEX IF NOT EXISTS ticket_comments_ticket_id_idx ON admin_service.ticket_comments(ticket_id);
CREATE INDEX IF NOT EXISTS ticket_comments_user_id_idx ON admin_service.ticket_comments(user_id);
CREATE INDEX IF NOT EXISTS ticket_comments_created_at_idx ON admin_service.ticket_comments(created_at);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key, unique identifier for the comment |
| ticket_id | UUID | Foreign key reference to the support ticket |
| user_id | UUID | ID of the user who added the comment (customer or admin) |
| comment | TEXT | The comment text |
| is_internal | BOOLEAN | If true, the comment is only visible to admins (for internal notes) |
| created_at | TIMESTAMP | When the comment was created |

### promotions

The `promotions` table stores promotional campaigns and discount codes.

```sql
CREATE TABLE IF NOT EXISTS admin_service.promotions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    promo_code VARCHAR(50) UNIQUE,
    discount_type VARCHAR(20) NOT NULL, -- 'percentage', 'fixed_amount', 'free_item', 'free_delivery'
    discount_value DECIMAL(10, 2),
    min_order_amount DECIMAL(10, 2),
    max_discount_amount DECIMAL(10, 2),
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    usage_limit INTEGER,
    current_usage INTEGER DEFAULT 0,
    applies_to VARCHAR(50)[], -- 'all', 'restaurant_id', 'menu_item_id', 'cuisine_type', etc.
    applies_to_ids UUID[],
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### Indexes
```sql
CREATE INDEX IF NOT EXISTS promotions_promo_code_idx ON admin_service.promotions(promo_code);
CREATE INDEX IF NOT EXISTS promotions_is_active_idx ON admin_service.promotions(is_active);
CREATE INDEX IF NOT EXISTS promotions_date_range_idx ON admin_service.promotions(start_date, end_date);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key, unique identifier for the promotion |
| name | VARCHAR(100) | Name of the promotion |
| description | TEXT | Detailed description of the promotion |
| promo_code | VARCHAR(50) | Unique code that customers can enter to apply the promotion |
| discount_type | VARCHAR(20) | Type of discount ('percentage', 'fixed_amount', 'free_item', 'free_delivery') |
| discount_value | DECIMAL(10,2) | Value of the discount (percentage or amount) |
| min_order_amount | DECIMAL(10,2) | Minimum order amount required to use the promotion |
| max_discount_amount | DECIMAL(10,2) | Maximum discount amount applied (for percentage discounts) |
| start_date | TIMESTAMP | When the promotion becomes active |
| end_date | TIMESTAMP | When the promotion expires |
| is_active | BOOLEAN | Whether the promotion is currently active |
| usage_limit | INTEGER | Maximum number of times the promotion can be used |
| current_usage | INTEGER | Current number of times the promotion has been used |
| applies_to | VARCHAR(50)[] | Array of entity types the promotion applies to |
| applies_to_ids | UUID[] | Array of specific entity IDs the promotion applies to |
| created_by | UUID | ID of the admin who created the promotion |
| created_at | TIMESTAMP | When the promotion was created |
| updated_at | TIMESTAMP | When the promotion was last updated |

### user_promotions

The `user_promotions` table tracks which users have used which promotions and how many times.

```sql
CREATE TABLE IF NOT EXISTS admin_service.user_promotions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    promotion_id UUID REFERENCES admin_service.promotions(id) ON DELETE CASCADE,
    usage_count INTEGER DEFAULT 0,
    first_used_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE
);
```

#### Indexes
```sql
CREATE INDEX IF NOT EXISTS user_promotions_user_id_idx ON admin_service.user_promotions(user_id);
CREATE INDEX IF NOT EXISTS user_promotions_promotion_id_idx ON admin_service.user_promotions(promotion_id);
CREATE UNIQUE INDEX IF NOT EXISTS user_promotions_user_promotion_idx ON admin_service.user_promotions(user_id, promotion_id);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key, unique identifier |
| user_id | UUID | ID of the user |
| promotion_id | UUID | ID of the promotion |
| usage_count | INTEGER | Number of times the user has used this promotion |
| first_used_at | TIMESTAMP | When the user first used this promotion |
| last_used_at | TIMESTAMP | When the user last used this promotion |

## Data Access Patterns

### Support Ticket Access Patterns

1. **Create Ticket**:
   ```sql
   INSERT INTO admin_service.support_tickets (user_id, subject, description, priority) 
   VALUES ($1, $2, $3, $4) RETURNING *;
   ```

2. **Get Ticket by ID**:
   ```sql
   SELECT * FROM admin_service.support_tickets WHERE id = $1;
   ```

3. **Get User's Tickets**:
   ```sql
   SELECT * FROM admin_service.support_tickets 
   WHERE user_id = $1 
   ORDER BY created_at DESC 
   LIMIT $2 OFFSET $3;
   ```

4. **Get Tickets by Status and Priority**:
   ```sql
   SELECT * FROM admin_service.support_tickets 
   WHERE status = $1 AND priority = $2
   ORDER BY 
      CASE 
          WHEN priority = 'urgent' THEN 1
          WHEN priority = 'high' THEN 2
          WHEN priority = 'medium' THEN 3
          WHEN priority = 'low' THEN 4
          ELSE 5
      END,
      created_at ASC
   LIMIT $3 OFFSET $4;
   ```

5. **Assign Ticket**:
   ```sql
   UPDATE admin_service.support_tickets
   SET 
       assigned_to = $1,
       status = CASE WHEN status = 'open' THEN 'in_progress' ELSE status END,
       updated_at = CURRENT_TIMESTAMP
   WHERE id = $2
   RETURNING *;
   ```

6. **Add Comment**:
   ```sql
   INSERT INTO admin_service.ticket_comments (ticket_id, user_id, comment, is_internal) 
   VALUES ($1, $2, $3, $4) RETURNING *;
   ```

7. **Get Ticket Comments**:
   ```sql
   SELECT * FROM admin_service.ticket_comments
   WHERE ticket_id = $1
   ORDER BY created_at;
   ```

### Promotion Access Patterns

1. **Create Promotion**:
   ```sql
   INSERT INTO admin_service.promotions (
       name, description, promo_code, discount_type, discount_value,
       min_order_amount, max_discount_amount, start_date, end_date,
       is_active, usage_limit, applies_to, applies_to_ids, created_by
   ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
   RETURNING *;
   ```

2. **Get Active Promotions**:
   ```sql
   SELECT * FROM admin_service.promotions
   WHERE is_active = TRUE
   AND CURRENT_TIMESTAMP BETWEEN start_date AND end_date
   AND (usage_limit IS NULL OR current_usage < usage_limit)
   ORDER BY start_date DESC;
   ```

3. **Apply Promotion**:
   ```sql
   -- Update promotion usage
   UPDATE admin_service.promotions
   SET current_usage = current_usage + 1
   WHERE id = $1 
   AND is_active = TRUE
   AND CURRENT_TIMESTAMP BETWEEN start_date AND end_date
   AND (usage_limit IS NULL OR current_usage < usage_limit)
   RETURNING *;
   
   -- Update user promotion usage
   INSERT INTO admin_service.user_promotions (user_id, promotion_id, usage_count, first_used_at, last_used_at)
   VALUES ($2, $1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
   ON CONFLICT (user_id, promotion_id) DO UPDATE 
   SET usage_count = user_promotions.usage_count + 1,
       last_used_at = CURRENT_TIMESTAMP;
   ```

## Data Integrity Constraints

1. **Foreign Key Constraints**:
   - `ticket_comments.ticket_id` references `support_tickets.id`
   - `user_promotions.promotion_id` references `promotions.id`

2. **Unique Constraints**:
   - `promotions.promo_code` must be unique
   - `user_promotions(user_id, promotion_id)` must be unique

3. **Data Validation Rules**:
   - Promotion dates: `end_date` must be after `start_date`
   - Support ticket status must be one of: 'open', 'in_progress', 'resolved', 'closed'
   - Support ticket priority must be one of: 'low', 'medium', 'high', 'urgent'
   - Promotion discount_type must be one of: 'percentage', 'fixed_amount', 'free_item', 'free_delivery'

## Data Lifecycle Management

1. **Support Tickets**:
   - Open tickets that remain inactive for 30 days are automatically closed
   - Resolved tickets are automatically closed after 7 days if no further activity
   - Closed tickets are archived after 90 days

2. **Promotions**:
   - Expired promotions are automatically marked as inactive
   - Promotions that have reached their usage limit are automatically marked as inactive
   - Historical promotion data is retained for analytics purposes

## Security Considerations

1. **Access Control**:
   - Regular users can only see their own tickets and comments
   - Internal comments are only visible to admin users
   - Only admin users can create and manage promotions

2. **Data Privacy**:
   - Personal information in ticket descriptions should be minimized
   - Support agents are trained on data privacy practices
   - Tickets containing sensitive information are flagged for special handling

## Monitoring Recommendations

1. **Key Metrics**:
   - Number of open tickets by priority
   - Average ticket resolution time
   - Tickets approaching SLA breach
   - Promotion usage patterns
   - Inactive assigned tickets

2. **Performance Monitoring**:
   - Query performance for ticket listing operations
   - Index usage statistics
   - Table growth rates

## Related Services

The Admin Service interacts with these other services:
- **User Service**: For user information and authentication
- **Order Service**: For order details related to tickets
- **Notification Service**: For sending notifications about ticket updates
- **Analytics Service**: For reporting on support performance and promotion effectiveness

## Schema Evolution

Future schema evolution plans include:
1. Adding ticket categories for better organization
2. Enhanced promotion targeting capabilities
3. Support for ticket attachments
4. Knowledge base integration for common issues