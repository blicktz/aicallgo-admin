"""
Promotion code service for database operations.
Provides read-only operations for Phase 4.
"""
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import Session, joinedload
from database.models import PromotionCode, PromotionCodeUsage, User
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_promotion_codes(
    session: Session,
    limit: int = 50,
    offset: int = 0,
    search_query: Optional[str] = None
) -> List[PromotionCode]:
    """
    Get promotion codes with pagination and search.

    Args:
        session: Database session
        limit: Maximum number of results
        offset: Pagination offset
        search_query: Search in code or stripe_promotion_id

    Returns:
        List of PromotionCode objects
    """
    try:
        query = select(PromotionCode)

        # Apply search filter
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(
                or_(
                    PromotionCode.code.ilike(search_pattern),
                    PromotionCode.stripe_promotion_id.ilike(search_pattern)
                )
            )

        # Order by creation date (newest first)
        query = query.order_by(desc(PromotionCode.created_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = session.execute(query)
        promo_codes = result.scalars().all()

        return list(promo_codes)

    except Exception as e:
        logger.error(f"Error fetching promotion codes: {e}")
        raise


def get_promotion_code_by_id(session: Session, promo_id: str) -> Optional[PromotionCode]:
    """
    Get promotion code by ID with all relationships loaded.

    Args:
        session: Database session
        promo_id: PromotionCode UUID

    Returns:
        PromotionCode object or None if not found
    """
    try:
        query = select(PromotionCode).where(PromotionCode.id == promo_id)
        # Eager load relationships
        query = query.options(
            joinedload(PromotionCode.users),
            joinedload(PromotionCode.usage_records)
        )
        result = session.execute(query)
        return result.unique().scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching promotion code {promo_id}: {e}")
        raise


def get_users_by_promotion_code(
    session: Session,
    promo_code_id: str
) -> List[User]:
    """
    Get all users currently using this promotion code.

    Args:
        session: Database session
        promo_code_id: PromotionCode UUID

    Returns:
        List of User objects
    """
    try:
        query = select(User).where(User.promotion_code_id == promo_code_id)
        result = session.execute(query)
        return list(result.scalars().all())

    except Exception as e:
        logger.error(f"Error fetching users for promotion code {promo_code_id}: {e}")
        raise


def get_usage_history(
    session: Session,
    promo_code_id: Optional[str] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0
) -> List[PromotionCodeUsage]:
    """
    Get promotion code usage history with filters.

    Args:
        session: Database session
        promo_code_id: Filter by promotion code ID
        user_id: Filter by user ID
        action: Filter by action (validated/applied/cleared/failed)
        start_date: Filter by created_at >= start_date
        end_date: Filter by created_at <= end_date
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        List of PromotionCodeUsage objects with relationships loaded
    """
    try:
        query = select(PromotionCodeUsage)

        # Eager load relationships
        query = query.options(
            joinedload(PromotionCodeUsage.user),
            joinedload(PromotionCodeUsage.promotion_code)
        )

        # Apply filters
        if promo_code_id:
            query = query.where(PromotionCodeUsage.promotion_code_id == promo_code_id)

        if user_id:
            query = query.where(PromotionCodeUsage.user_id == user_id)

        if action:
            query = query.where(PromotionCodeUsage.action == action)

        if start_date:
            query = query.where(PromotionCodeUsage.created_at >= start_date)

        if end_date:
            query = query.where(PromotionCodeUsage.created_at <= end_date)

        # Order by creation date (newest first)
        query = query.order_by(desc(PromotionCodeUsage.created_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = session.execute(query)
        usage_records = result.unique().scalars().all()

        return list(usage_records)

    except Exception as e:
        logger.error(f"Error fetching promotion code usage history: {e}")
        raise


def get_promotion_code_stats(
    session: Session,
    promo_code_id: str
) -> Dict[str, Any]:
    """
    Get statistics for a specific promotion code.

    Args:
        session: Database session
        promo_code_id: PromotionCode UUID

    Returns:
        Dict with metrics:
        - user_count: Number of users currently using this code
        - total_usage_count: Total number of usage records
        - usage_by_action: Breakdown by action type
    """
    try:
        # Count users currently using this code
        user_count_query = select(func.count(User.id)).where(
            User.promotion_code_id == promo_code_id
        )
        user_count_result = session.execute(user_count_query)
        user_count = user_count_result.scalar()

        # Total usage records
        total_usage_query = select(func.count(PromotionCodeUsage.id)).where(
            PromotionCodeUsage.promotion_code_id == promo_code_id
        )
        total_usage_result = session.execute(total_usage_query)
        total_usage_count = total_usage_result.scalar()

        # Usage breakdown by action
        usage_by_action_query = select(
            PromotionCodeUsage.action,
            func.count(PromotionCodeUsage.id).label('count')
        ).where(
            PromotionCodeUsage.promotion_code_id == promo_code_id
        ).group_by(PromotionCodeUsage.action)

        usage_by_action_result = session.execute(usage_by_action_query)
        usage_by_action = {row.action: row.count for row in usage_by_action_result}

        return {
            "user_count": user_count,
            "total_usage_count": total_usage_count,
            "usage_by_action": usage_by_action,
        }

    except Exception as e:
        logger.error(f"Error fetching promotion code stats for {promo_code_id}: {e}")
        raise


def get_all_promotion_code_stats(session: Session) -> Dict[str, Any]:
    """
    Get overall promotion code statistics.

    Returns:
        Dict with system-wide metrics:
        - total_codes: Total promotion codes
        - active_codes: Codes currently in use
        - total_usage_records: All usage records
    """
    try:
        # Total promotion codes
        total_codes_query = select(func.count(PromotionCode.id))
        total_codes_result = session.execute(total_codes_query)
        total_codes = total_codes_result.scalar()

        # Active codes (codes with users)
        active_codes_query = select(func.count(func.distinct(User.promotion_code_id))).where(
            User.promotion_code_id.isnot(None)
        )
        active_codes_result = session.execute(active_codes_query)
        active_codes = active_codes_result.scalar()

        # Total usage records
        total_usage_query = select(func.count(PromotionCodeUsage.id))
        total_usage_result = session.execute(total_usage_query)
        total_usage = total_usage_result.scalar()

        return {
            "total_codes": total_codes,
            "active_codes": active_codes,
            "total_usage_records": total_usage,
        }

    except Exception as e:
        logger.error(f"Error fetching overall promotion code stats: {e}")
        raise
