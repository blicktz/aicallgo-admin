"""
Business service for database operations.
Provides read-only operations for Phase 2.
"""
from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Business
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


async def get_businesses(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    search_query: Optional[str] = None,
    industry_filter: Optional[str] = None
) -> List[Business]:
    """
    Get businesses with pagination and filters.

    Args:
        session: Database session
        limit: Maximum number of results
        offset: Pagination offset
        search_query: Search in business name
        industry_filter: Filter by industry

    Returns:
        List of Business objects
    """
    try:
        query = select(Business)

        # Apply search filter
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(Business.business_name.ilike(search_pattern))

        # Apply industry filter
        if industry_filter and industry_filter.lower() != "all":
            query = query.where(Business.industry.ilike(f"%{industry_filter}%"))

        # Order by creation date (newest first)
        query = query.order_by(desc(Business.created_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        businesses = result.scalars().all()

        return list(businesses)

    except Exception as e:
        logger.error(f"Error fetching businesses: {e}")
        raise


async def get_business_by_id(session: AsyncSession, business_id: str) -> Optional[Business]:
    """
    Get business by ID with relationships loaded.

    Args:
        session: Database session
        business_id: Business UUID

    Returns:
        Business object or None if not found
    """
    try:
        query = select(Business).where(Business.id == business_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching business {business_id}: {e}")
        raise


async def get_businesses_by_user(
    session: AsyncSession,
    user_id: str,
    limit: int = 50
) -> List[Business]:
    """
    Get all businesses for a specific user.

    Args:
        session: Database session
        user_id: User UUID
        limit: Maximum number of results

    Returns:
        List of Business objects owned by the user
    """
    try:
        query = (
            select(Business)
            .where(Business.user_id == user_id)
            .order_by(desc(Business.created_at))
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    except Exception as e:
        logger.error(f"Error fetching businesses for user {user_id}: {e}")
        raise


async def get_business_stats(session: AsyncSession) -> Dict[str, Any]:
    """
    Get business statistics for dashboard.

    Returns:
        Dict with business metrics:
        - total_businesses: Total business count
        - businesses_with_phone: Businesses with phone numbers configured
    """
    try:
        # Total businesses
        total_query = select(func.count(Business.id))
        total_result = await session.execute(total_query)
        total_businesses = total_result.scalar()

        # Businesses with phone numbers
        with_phone_query = select(func.count(Business.id)).where(
            Business.primary_business_phone_number.isnot(None)
        )
        with_phone_result = await session.execute(with_phone_query)
        businesses_with_phone = with_phone_result.scalar()

        return {
            "total_businesses": total_businesses,
            "businesses_with_phone": businesses_with_phone,
        }

    except Exception as e:
        logger.error(f"Error fetching business stats: {e}")
        raise


async def get_industries(session: AsyncSession) -> List[str]:
    """
    Get list of unique industries.

    Args:
        session: Database session

    Returns:
        List of industry names
    """
    try:
        query = (
            select(Business.industry)
            .where(Business.industry.isnot(None))
            .distinct()
            .order_by(Business.industry)
        )
        result = await session.execute(query)
        industries = result.scalars().all()
        return list(industries)

    except Exception as e:
        logger.error(f"Error fetching industries: {e}")
        raise
