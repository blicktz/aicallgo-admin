"""
Database connection module using sync SQLAlchemy.
Streamlit works better with synchronous code due to event loop management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import text
from contextlib import contextmanager
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Create sync engine
# Configuration matches web-backend connection pooling strategy
engine = create_engine(
    settings.sync_database_url,
    pool_size=5,              # Smaller pool for admin tool
    max_overflow=10,          # Total connections: 15
    pool_pre_ping=True,       # Check connections before use
    pool_recycle=300,         # Recycle after 5 minutes
    echo=settings.DEBUG       # Log SQL in debug mode
)

# Create session factory
SessionLocal = sessionmaker(
    engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@contextmanager
def get_session():
    """
    Get database session.

    Usage:
        with get_session() as session:
            result = session.execute(query)
    """
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def check_db_health() -> tuple[bool, str]:
    """
    Check database connection health.

    Returns:
        tuple: (is_healthy: bool, message: str)
    """
    try:
        with get_session() as session:
            # Simple query to test connection
            result = session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()

            # Also check critical tables exist
            tables_query = text("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('users', 'businesses', 'call_log', 'subscriptions')
            """)
            table_count = session.execute(tables_query)
            tables_exist = table_count.scalar()

            if tables_exist < 4:
                return False, f"Missing critical tables (found {tables_exist}/4)"

            return True, f"✅ Connected - {count} users, all critical tables present"

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False, f"❌ Connection failed: {str(e)[:100]}"


def get_db_info() -> dict:
    """
    Get database information for system info display.

    Returns:
        dict: Database statistics
    """
    try:
        with get_session() as session:
            queries = {
                "users": "SELECT COUNT(*) FROM users",
                "businesses": "SELECT COUNT(*) FROM businesses",
                "call_logs": "SELECT COUNT(*) FROM call_log",
                "subscriptions": "SELECT COUNT(*) FROM subscriptions WHERE status = 'active'"
            }

            info = {}
            for key, query in queries.items():
                result = session.execute(text(query))
                info[key] = result.scalar()

            return info
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {}
