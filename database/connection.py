"""
Database connection module using async SQLAlchemy.
Matches pattern from web-backend but uses async engine.
"""
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from sqlalchemy import text
from contextlib import asynccontextmanager
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Create async engine
# Configuration matches web-backend connection pooling strategy
engine = create_async_engine(
    settings.async_database_url,
    pool_size=5,              # Smaller pool for admin tool
    max_overflow=10,          # Total connections: 15
    pool_pre_ping=True,       # Check connections before use
    pool_recycle=300,         # Recycle after 5 minutes
    echo=settings.DEBUG       # Log SQL in debug mode
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@asynccontextmanager
async def get_async_session():
    """
    Get async database session.

    Usage:
        async with get_async_session() as session:
            result = await session.execute(query)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def check_db_health() -> tuple[bool, str]:
    """
    Check database connection health.

    Returns:
        tuple: (is_healthy: bool, message: str)
    """
    try:
        async with get_async_session() as session:
            # Simple query to test connection
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()

            # Also check critical tables exist
            tables_query = text("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('users', 'businesses', 'call_log', 'subscriptions')
            """)
            table_count = await session.execute(tables_query)
            tables_exist = table_count.scalar()

            if tables_exist < 4:
                return False, f"Missing critical tables (found {tables_exist}/4)"

            return True, f"✅ Connected - {count} users, all critical tables present"

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False, f"❌ Connection failed: {str(e)[:100]}"


async def get_db_info() -> dict:
    """
    Get database information for system info display.

    Returns:
        dict: Database statistics
    """
    try:
        async with get_async_session() as session:
            queries = {
                "users": "SELECT COUNT(*) FROM users",
                "businesses": "SELECT COUNT(*) FROM businesses",
                "call_logs": "SELECT COUNT(*) FROM call_log",
                "subscriptions": "SELECT COUNT(*) FROM subscriptions WHERE status = 'active'"
            }

            info = {}
            for key, query in queries.items():
                result = await session.execute(text(query))
                info[key] = result.scalar()

            return info
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {}
