# ADR-004: Database Per Service

## Status

Accepted

## Context

In our microservices architecture for the Nibble platform, we need to determine the appropriate data management strategy. A critical decision is whether to use a shared database for all services or implement database isolation between services.

Key considerations include:
- Data ownership and autonomy
- Service independence
- Schema evolution
- Consistency vs. availability tradeoffs
- Operational complexity
- Query performance
- Development velocity

We considered several approaches:
1. Shared database for all services
2. Database per service (with schema separation)
3. Database per service (with separate database instances)
4. Hybrid approach

## Decision

We have decided to implement the **Database Per Service pattern with schema separation** as our primary data architecture approach.

Specifically:

1. **Single PostgreSQL Instance with Schema Separation**:
   - Each microservice will have its own dedicated schema within a shared PostgreSQL instance
   - Services will access only their own schema, treating others as private
   - Schema names will match service names (e.g., `user_service`, `restaurant_service`)
   - Cross-schema references will be minimized and carefully managed

2. **Data Ownership Principles**:
   - Each service exclusively owns and manages its data
   - No direct database access from other services
   - Data sharing occurs through APIs or events
   - Each service is responsible for its schema evolution

3. **Implementation Details**:
   - PostgreSQL with PostGIS extension for geospatial capabilities
   - Clear schema boundaries in database scripts
   - Service-specific database users with restricted permissions
   - UUID primary keys for easier data portability

4. **Evolution Path**:
   - Current implementation uses schema separation
   - Future scale may require physical database separation
   - Design decisions should anticipate this potential evolution

## Consequences

### Positive

- **Service Autonomy**: Services can modify their schema independently without impacting other services.
- **Clear Ownership Boundaries**: Explicit ownership of data reduces development conflicts and confusion.
- **Independent Development**: Teams can evolve their data model at their own pace.
- **Simplified Schema Evolution**: Changes to one service's schema don't affect other services.
- **Operational Simplicity**: Single database instance is simpler to manage than multiple databases.
- **Resource Efficiency**: Shared database instance uses resources more efficiently than multiple instances.
- **Security Isolation**: Schema-level permissions prevent unauthorized access to other services' data.
- **Future Flexibility**: Design supports potential migration to physically separate databases.

### Negative

- **Distributed Transactions**: Transactions across service boundaries become more complex.
- **Data Duplication**: Some data may need to be duplicated across services.
- **Join Limitations**: No direct joins between data in different services.
- **Consistency Challenges**: Maintaining consistency across service boundaries requires careful design.
- **Operational Coupling**: Database maintenance affects all services simultaneously.
- **Potential Resource Contention**: Services share the same database resources.
- **Monitoring Complexity**: Need to monitor resource usage at the schema level.
- **Potential for Schema Leakage**: Risk of services accessing data from other schemas.

## Mitigation Strategies

To address the negative consequences:

1. **Event-Driven Updates**: Use events for propagating changes across service boundaries.
2. **Data Denormalization**: Strategic denormalization to avoid cross-service joins.
3. **Duplicate Data Responsibly**: Clear documentation of which service owns the source of truth.
4. **Consistency Patterns**: Implement patterns like Saga for multi-service operations.
5. **Resource Monitoring**: Monitor database performance by schema to identify contention.
6. **Clear Access Controls**: Strict database permissions to prevent schema leakage.
7. **Schema Naming Conventions**: Consistent prefixing to clearly indicate ownership.
8. **Database Upgrade Windows**: Coordinate database maintenance to minimize impact.

## Implementation Details

### Schema Structure

Each service has its own schema with a naming convention that clearly indicates ownership:

```sql
-- Create schema for each service
CREATE SCHEMA IF NOT EXISTS user_service;
CREATE SCHEMA IF NOT EXISTS restaurant_service;
CREATE SCHEMA IF NOT EXISTS driver_service;
CREATE SCHEMA IF NOT EXISTS order_service;
CREATE SCHEMA IF NOT EXISTS admin_service;
```

### Access Controls

Service-specific database users with restricted permissions:

```sql
-- Example of restricted permissions
CREATE USER user_service_app WITH PASSWORD 'password';
GRANT USAGE ON SCHEMA user_service TO user_service_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA user_service TO user_service_app;
```

### Data Synchronization

For data needed across services, we implement event-based synchronization:

1. Source service publishes events when data changes
2. Consumer services maintain read-only copies as needed
3. Clear documentation of the source of truth

### Query Examples

**Within a service (typical case):**
```sql
-- Order service querying its own data
SELECT * FROM order_service.orders WHERE id = $1;
```

**Cross-service data access (avoided when possible):**
```sql
-- Instead of direct cross-schema queries, use:
-- 1. API calls to the owning service
-- 2. Event-driven data synchronization
-- 3. Carefully managed read-only views (rare cases)
```

## Alternatives Considered

### 1. Shared Database with Shared Schema

**Advantages**:
- Simplest implementation
- Easy joins across all data
- No duplication
- Simpler transactions

**Disadvantages**:
- No service autonomy
- Schema changes affect all services
- Tight coupling between services
- No clear data ownership
- Difficult to scale or evolve independently

We rejected this approach because it undermines key microservice principles of autonomy and independent evolution.

### 2. Database Per Service (Separate Instances)

**Advantages**:
- Maximum service autonomy
- Complete isolation of resources
- Independent scaling of database resources
- Independent backup and maintenance

**Disadvantages**:
- Higher operational complexity
- More resource intensive
- More complex deployment
- Higher infrastructure costs
- More complex data synchronization

We determined this approach would introduce unnecessary operational complexity in the initial stage but remains an option for future scaling.

### 3. Hybrid Approach (Mixed Strategy)

**Advantages**:
- Flexibility to choose best approach per service
- Can optimize for specific service needs
- Gradual migration path

**Disadvantages**:
- Inconsistent architecture
- More cognitive load for developers
- More complex documentation and onboarding

We preferred a consistent approach for initial implementation but may adopt hybrid elements as the system evolves.

## Evolution Path

Our current decision allows for future evolution:

1. **Current State**: Schema-separated database
2. **Medium-Term**: Potential movement of high-volume services to dedicated instances
3. **Long-Term**: Possible migration to fully separate databases as needed

This evolution path allows us to start with operational simplicity while maintaining the option to scale out if needed.

## References

- [Pattern: Database per Service](https://microservices.io/patterns/data/database-per-service.html)
- [Building Microservices by Sam Newman](https://samnewman.io/books/building_microservices/) - Chapter 4
- [PostgreSQL Schema Documentation](https://www.postgresql.org/docs/current/ddl-schemas.html)
- [Saga Pattern](https://microservices.io/patterns/data/saga.html)
- [Designing Data-Intensive Applications by Martin Kleppmann](https://dataintensive.net/)