# Database Schema Documentation

This directory contains comprehensive documentation of the database schemas used in the Nibble platform. Understanding these schemas is essential for developers working with the system's data model.

## Schema Organization

The Nibble platform uses a "database per service" pattern with schema separation. Each microservice owns its data and has a dedicated schema within the PostgreSQL database:

- `user_service` - User accounts, profiles, addresses, and preferences
- `restaurant_service` - Restaurant details, menus, and operating hours
- `order_service` - Orders, order items, and payments
- `driver_service` - Driver profiles and delivery information
- `admin_service` - Administrative functions including support tickets and promotions

## Core Schemas

1. [User Schema](./user-schema.md)
2. [Restaurant Schema](./restaurant-schema.md)
3. [Order Schema](./order-schema.md)
4. [Driver Schema](./driver-schema.md)
5. [Admin Schema](./admin-schema.md)
6. [Analytics Schema](./analytics-schema.md)

## Database Technology

### PostgreSQL with PostGIS

The primary relational database is PostgreSQL with the PostGIS extension for geospatial capabilities. Key features used:

- **JSONB Data Type**: For flexible schema portions (e.g., customization options, dietary preferences)
- **Geospatial Indexes**: For location-based queries (restaurant proximity, driver locations)
- **Array Types**: For multi-value attributes (e.g., cuisine types, allergens)
- **Triggers**: For automated timestamp updates and event generation
- **Constraints**: For data integrity (unique constraints, foreign keys)

### Redis

Redis is used alongside PostgreSQL for:

- Caching frequently accessed data
- Session management
- Rate limiting
- Temporary data storage (shopping carts)

### Apache Pinot

Apache Pinot serves as our analytics database, providing:

- Real-time analytics processing
- Complex OLAP queries
- Time-series data analysis
- High-throughput ingestion from Kafka

## Key Schema Design Principles

1. **Service Ownership**: Each microservice exclusively owns its schema(s)
2. **Denormalization Where Appropriate**: Some data is denormalized for query performance and service independence
3. **Audit Trails**: History tables track changes to critical data
4. **Soft Deletes**: Flagging records as inactive rather than physically removing them
5. **UUID Primary Keys**: Using UUIDs for flexibility across environments

## Example: Support Ticket Schema

The support ticket system uses two main tables in the Admin Service schema:

### support_tickets

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

### ticket_comments

```sql
CREATE TABLE IF NOT EXISTS admin_service.ticket_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID REFERENCES admin_service.support_tickets(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    comment TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ticket_comments_ticket_id_idx ON admin_service.ticket_comments(ticket_id);
```

## Data Migration Strategy

For schema evolution, we follow these principles:

1. **Backward Compatible Changes**: Adding columns, tables, or non-restrictive constraints
2. **Versioned Migrations**: Numbered migration files in each service's repository
3. **Testing Migrations**: Validating migrations in test environments before production
4. **Rollback Plans**: Documenting how to roll back migrations if issues occur

## Database Access Patterns

Each service connects to the database through:

1. **Database Connection Pools**: Managing connection lifecycles efficiently
2. **Repository Pattern**: Abstracting database operations behind service-specific repositories
3. **Parameterized Queries**: Using prepared statements for all database interactions
4. **Transaction Management**: Ensuring ACID properties for critical operations

## Performance Considerations

1. **Indexing Strategy**: Indexes on frequently queried columns and join conditions
2. **Query Optimization**: Regular review and optimization of slow queries
3. **Connection Pooling**: Efficient connection management through asyncpg
4. **Data Partitioning**: Partitioning large tables (e.g., orders) by date ranges

## Security Considerations

1. **Schema Isolation**: Each service only has access to its own schema
2. **Least Privilege Principle**: Database users have minimal required permissions
3. **Data Encryption**: Sensitive fields encrypted at rest
4. **Audit Logging**: Critical data changes are logged with user context

## Further Reading

- [Database Migration Guide](../operations/database-migrations.md)
- [Query Optimization Best Practices](../performance/query-optimization.md)
- [Data Privacy Implementation](../security/data-privacy.md)