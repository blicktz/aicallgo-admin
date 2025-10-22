# Query Optimization Guide

## Overview

This document provides guidelines for optimizing database queries in the Admin Board application. Following these patterns ensures efficient database access and good application performance.

## General Principles

### 1. Always Use Pagination

All queries that return lists should use `LIMIT` and `OFFSET` for pagination:

```python
def get_items(session: Session, limit: int = 50, offset: int = 0):
    query = select(Model).limit(limit).offset(offset)
    return query.all()
```

**Default Limits:**
- Dashboard metrics: No limit (aggregate queries)
- List views: 50 items default, 100 max for regular views
- Search results: 20 items for autocomplete
- CSV exports: 1000 items max with warning

### 2. Use Eager Loading to Avoid N+1 Queries

When accessing related data, use `joinedload()` to load relationships in a single query:

```python
# Bad (N+1 query):
users = session.query(User).all()
for user in users:
    business = user.business  # Triggers a query each time!

# Good (eager loading):
from sqlalchemy.orm import joinedload
users = session.query(User).options(joinedload(User.business)).all()
```

**Applied in:**
- `promotion_service.py`: Eager loads users and usage records
- `appointment_service.py`: Eager loads user, business, end_user, call_log
- All detail views: Load related data in advance

### 3. Use Proper Indexing

#### Recommended Indexes

Based on query patterns, these columns should be indexed:

**Users Table:**
- `email` (unique) - Used for login and search
- `stripe_customer_id` - Used for Stripe lookups
- `is_active` - Used for filtering
- `created_at` - Used for recent signups and growth metrics

**Business Table:**
- `user_id` - Foreign key for user lookups
- `industry` - Used for filtering
- `created_at` - Used for growth metrics

**CallLog Table:**
- `user_id` - Foreign key
- `business_id` - Foreign key
- `created_at` - Used for date range filtering
- `status` - Used for filtering by call status
- `caller_phone_number` - Used for search

**Appointment Table:**
- `user_id` - Foreign key
- `start_time` - Used for date range filtering and sorting
- `status` - Used for filtering
- `booking_source` - Used for filtering
- `created_at` - Used for growth metrics

**CreditTransaction Table:**
- `user_id` - Foreign key
- `created_at` - Used for transaction history

**PromotionCodeUsage Table:**
- `user_id` - Foreign key
- `promotion_code_id` - Foreign key
- `created_at` - Used for usage history
- `action` - Used for filtering

**Subscription Table:**
- `user_id` - Foreign key
- `status` - Used for active subscription queries

### 4. Use COUNT Queries Efficiently

Never load all records just to count them:

```python
# Bad:
users = session.query(User).all()
count = len(users)

# Good:
from sqlalchemy import func
count = session.query(func.count(User.id)).scalar()
```

### 5. Selective Column Loading

When you only need specific columns, load only those:

```python
# If you only need email and name:
users = session.query(User.id, User.email, User.full_name).all()
```

However, in our admin board, we typically need full objects for detail views, so this is less commonly used.

### 6. Query Result Caching

Use Streamlit's caching effectively:

```python
@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_dashboard_data():
    with get_session() as session:
        return get_stats(session)
```

**Cache TTL Guidelines:**
- Dashboard metrics: 60 seconds (frequent updates needed)
- User lists: 60 seconds (moderate update frequency)
- System stats: 300 seconds (5 minutes, relatively static)

### 7. Limit Search Results

For search and autocomplete, always limit results:

```python
def search_users(session: Session, query: str, limit: int = 20):
    # Only return first 20 matches for autocomplete
    return session.query(User).filter(
        User.email.ilike(f"%{query}%")
    ).limit(limit).all()
```

## Query Patterns by Service

### User Service

**Pattern: Get users with filters**
```python
query = select(User).where(User.is_active == True).limit(50)
```

**Optimization:**
- Index on `is_active` and `created_at`
- Use LIMIT to prevent loading all users
- Order by `created_at DESC` for recent first

### Promotion Service

**Pattern: Get promotion codes with usage stats**
```python
query = select(PromotionCode).options(
    joinedload(PromotionCode.users),
    joinedload(PromotionCode.usage_records)
).limit(50)
```

**Optimization:**
- Eager load relationships to avoid N+1
- Use `unique()` on results when using joinedload
- Index on `code` for search

### Appointment Service

**Pattern: Get appointments with date range**
```python
query = select(Appointment).where(
    Appointment.start_time >= start_date,
    Appointment.start_time <= end_date
).options(
    joinedload(Appointment.user),
    joinedload(Appointment.end_user)
).order_by(desc(Appointment.start_time)).limit(50)
```

**Optimization:**
- Index on `start_time` for efficient date range queries
- Eager load user and end_user to avoid N+1
- Use `desc()` for newest first ordering

### System Service

**Pattern: Table row counts**
```python
# Use func.count() for each table
count = session.execute(select(func.count(User.id))).scalar()
```

**Optimization:**
- Avoid loading data, only count
- Cache results for 5 minutes (relatively static)
- Run multiple counts in parallel when possible

## Performance Benchmarks

Target response times for typical operations:

| Operation | Target Time | Notes |
|-----------|-------------|-------|
| Dashboard load | < 2s | All metrics combined |
| List view (50 items) | < 500ms | With pagination |
| Detail view | < 500ms | With eager loading |
| Search query | < 1s | Limited to 20 results |
| CSV export (1000 items) | < 5s | Background processing |
| Count queries | < 100ms | Index required |

## Common Pitfalls

### 1. N+1 Query Problem

**Problem:**
```python
# Loads users, then queries for each user's business
for user in get_users(session):
    business = user.business  # N+1 query!
```

**Solution:**
```python
# Load all at once with joinedload
users = session.query(User).options(joinedload(User.business)).all()
```

### 2. Loading Too Much Data

**Problem:**
```python
# Loads all users into memory
all_users = session.query(User).all()
```

**Solution:**
```python
# Use pagination
users = session.query(User).limit(50).offset(page * 50).all()
```

### 3. Inefficient Counting

**Problem:**
```python
# Loads all records to count
count = len(session.query(User).all())
```

**Solution:**
```python
# Use COUNT query
count = session.query(func.count(User.id)).scalar()
```

### 4. Missing Indexes

**Problem:**
```python
# Slow query without index on created_at
recent_users = session.query(User).filter(
    User.created_at >= week_ago
).all()
```

**Solution:**
- Add index on `created_at` column
- Document required indexes in migration

## Database Connection Management

### Connection Pooling

The admin board uses SQLAlchemy's connection pooling. Default settings:

```python
# In database/connection.py
engine = create_engine(
    DATABASE_URL,
    pool_size=5,           # 5 connections in pool
    max_overflow=10,       # 10 additional connections if needed
    pool_pre_ping=True,    # Verify connections before use
    pool_recycle=3600      # Recycle connections after 1 hour
)
```

### Session Management

Always use context managers for sessions:

```python
with get_session() as session:
    # Query here
    data = session.query(User).all()
# Session automatically closed
```

## Monitoring and Debugging

### Enable Query Logging

To debug slow queries, enable SQLAlchemy logging:

```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Identify Slow Queries

Look for these patterns in logs:
- Multiple queries in loops (N+1 problem)
- Queries without WHERE clauses
- Large result sets without LIMIT
- Missing indexes (full table scans)

## Migration Recommendations

When creating new migrations with Alembic, add indexes for:

1. All foreign key columns
2. Columns used in WHERE clauses
3. Columns used in ORDER BY
4. Columns used in JOIN conditions

Example migration:

```python
def upgrade():
    # Add index on created_at for efficient date queries
    op.create_index(
        'ix_call_log_created_at',
        'call_log',
        ['created_at'],
        postgresql_ops={'created_at': 'DESC'}  # For DESC ordering
    )
```

## Future Optimizations

### Considered for Future Phases:

1. **Read Replicas**: Separate read/write databases for scale
2. **Query Caching**: Redis-based query result caching
3. **Materialized Views**: Pre-computed aggregates for dashboard
4. **Partial Indexes**: Indexes on filtered subsets (e.g., active users only)
5. **Database Sharding**: If data volume exceeds single DB capacity

## Resources

- [SQLAlchemy Performance Tips](https://docs.sqlalchemy.org/en/14/faq/performance.html)
- [PostgreSQL Indexing Best Practices](https://www.postgresql.org/docs/current/indexes.html)
- [Understanding N+1 Queries](https://stackoverflow.com/questions/97197/what-is-the-n1-selects-problem)

## Conclusion

Following these patterns ensures:
- Fast page load times (< 2s for dashboard, < 500ms for lists)
- Efficient database resource usage
- Scalability to thousands of users
- Good user experience

All new services should follow these patterns from the start. Regular performance testing should be conducted as data volume grows.
