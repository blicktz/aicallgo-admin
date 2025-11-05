"""
User service for database operations.
Provides read-only operations for Phase 2.
Phase 3: Added email update functionality for admin operations.
"""
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import Session
from database.models import User
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging
import re
import secrets

logger = logging.getLogger(__name__)


def get_users(
    session: Session,
    limit: int = 50,
    offset: int = 0,
    search_query: Optional[str] = None,
    plan_filter: Optional[str] = None,
    status_filter: Optional[str] = None
) -> List[User]:
    """
    Get users with pagination and filters.

    Args:
        session: Database session
        limit: Maximum number of results
        offset: Pagination offset
        search_query: Search in email/name
        plan_filter: Filter by subscription plan
        status_filter: Filter by is_active status

    Returns:
        List of User objects with relationships loaded
    """
    try:
        query = select(User)

        # Apply search filter
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(
                or_(
                    User.email.ilike(search_pattern),
                    User.full_name.ilike(search_pattern)
                )
            )

        # Apply status filter
        if status_filter and status_filter.lower() != "all":
            is_active = status_filter.lower() == "active"
            query = query.where(User.is_active == is_active)

        # TODO: Add plan filter after joining with subscriptions
        # This requires more complex query with join

        # Order by creation date (newest first)
        query = query.order_by(desc(User.created_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = session.execute(query)
        users = result.scalars().all()

        return list(users)

    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise


def get_user_by_id(session: Session, user_id: str) -> Optional[User]:
    """
    Get user by ID with all relationships loaded.

    Args:
        session: Database session
        user_id: User UUID

    Returns:
        User object or None if not found
    """
    try:
        query = select(User).where(User.id == user_id)
        result = session.execute(query)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        raise


def get_user_by_email(session: Session, email: str) -> Optional[User]:
    """
    Get user by email address.

    Args:
        session: Database session
        email: User email

    Returns:
        User object or None if not found
    """
    try:
        query = select(User).where(User.email == email)
        result = session.execute(query)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching user by email {email}: {e}")
        raise


def get_user_stats(session: Session) -> Dict[str, Any]:
    """
    Get user statistics for dashboard.

    Returns:
        Dict with user metrics:
        - total_users: Total user count
        - active_users: Users with is_active=True
        - new_users_7d: Users created in last 7 days
        - new_users_30d: Users created in last 30 days
    """
    try:
        # Total users
        total_query = select(func.count(User.id))
        total_result = session.execute(total_query)
        total_users = total_result.scalar()

        # Active users
        active_query = select(func.count(User.id)).where(User.is_active == True)
        active_result = session.execute(active_query)
        active_users = active_result.scalar()

        # New users in last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_7d_query = select(func.count(User.id)).where(User.created_at >= week_ago)
        new_7d_result = session.execute(new_7d_query)
        new_users_7d = new_7d_result.scalar()

        # New users in last 30 days
        month_ago = datetime.utcnow() - timedelta(days=30)
        new_30d_query = select(func.count(User.id)).where(User.created_at >= month_ago)
        new_30d_result = session.execute(new_30d_query)
        new_users_30d = new_30d_result.scalar()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "new_users_7d": new_users_7d,
            "new_users_30d": new_users_30d,
        }

    except Exception as e:
        logger.error(f"Error fetching user stats: {e}")
        raise


def get_recent_signups(session: Session, limit: int = 10) -> List[User]:
    """
    Get most recent user signups.

    Args:
        session: Database session
        limit: Number of recent users to fetch

    Returns:
        List of recently created User objects
    """
    try:
        query = select(User).order_by(desc(User.created_at)).limit(limit)
        result = session.execute(query)
        return list(result.scalars().all())

    except Exception as e:
        logger.error(f"Error fetching recent signups: {e}")
        raise


def validate_email_format(email: str) -> bool:
    """
    Validate email format using regex.

    Args:
        email: Email address to validate

    Returns:
        True if email format is valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def generate_deleted_email(original_email: str) -> str:
    """
    Generate a "deleted" email address format.

    Converts user@example.com to user_deleted_abc12345@example.com

    Args:
        original_email: Original email address

    Returns:
        Modified email with _deleted_{random} suffix before @
    """
    if '@' not in original_email:
        raise ValueError("Invalid email format")

    username, domain = original_email.split('@', 1)
    random_suffix = secrets.token_hex(4)  # 8 character hex string
    return f"{username}_deleted_{random_suffix}@{domain}"


def update_user_email(
    session: Session,
    user_id: str,
    new_email: str
) -> Tuple[bool, str]:
    """
    Update user's email address.

    Phase 3 admin functionality to change user email.
    Use case: Soft delete user by changing email to _deleted_ format,
    freeing up the original email for a new account.

    Args:
        session: Database session
        user_id: User UUID
        new_email: New email address (must be valid format and unique)

    Returns:
        Tuple of (success: bool, message: str)
        - (True, "Success message") if updated
        - (False, "Error message") if failed
    """
    try:
        # Validate email format
        if not validate_email_format(new_email):
            return (False, f"Invalid email format: {new_email}")

        # Get the user
        user = get_user_by_id(session, user_id)
        if not user:
            return (False, f"User not found with ID: {user_id}")

        original_email = user.email

        # Check if new email is the same as current
        if new_email == original_email:
            return (False, "New email is the same as current email")

        # Check if new email already exists (excluding current user)
        existing_user = get_user_by_email(session, new_email)
        if existing_user and existing_user.id != user_id:
            return (False, f"Email already in use: {new_email}")

        # Update email
        user.email = new_email
        session.commit()

        logger.info(f"Admin updated user email: {user_id} from {original_email} to {new_email}")
        return (True, f"Email updated successfully from {original_email} to {new_email}")

    except Exception as e:
        session.rollback()
        error_msg = f"Error updating user email: {str(e)}"
        logger.error(error_msg)
        return (False, error_msg)
