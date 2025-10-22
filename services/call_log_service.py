"""
Call log service for database operations.
Provides read-only operations for Phase 2.
"""
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import CallLog
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


async def get_call_logs(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    phone_search: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> List[CallLog]:
    """
    Get call logs with pagination and filters.

    Args:
        session: Database session
        limit: Maximum number of results
        offset: Pagination offset
        status_filter: Filter by call status
        phone_search: Search by phone number
        date_from: Start date filter
        date_to: End date filter

    Returns:
        List of CallLog objects
    """
    try:
        query = select(CallLog)

        # Apply status filter
        if status_filter and status_filter.lower() != "all":
            query = query.where(CallLog.call_status == status_filter)

        # Apply phone search
        if phone_search:
            search_pattern = f"%{phone_search}%"
            query = query.where(CallLog.caller_phone_number.ilike(search_pattern))

        # Apply date range filters
        if date_from:
            query = query.where(CallLog.call_start_time >= date_from)
        if date_to:
            query = query.where(CallLog.call_start_time <= date_to)

        # Order by call start time (newest first)
        query = query.order_by(desc(CallLog.call_start_time))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        call_logs = result.scalars().all()

        return list(call_logs)

    except Exception as e:
        logger.error(f"Error fetching call logs: {e}")
        raise


async def get_call_log_by_id(session: AsyncSession, call_id: str) -> Optional[CallLog]:
    """
    Get call log by ID.

    Args:
        session: Database session
        call_id: CallLog UUID

    Returns:
        CallLog object or None if not found
    """
    try:
        query = select(CallLog).where(CallLog.id == call_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching call log {call_id}: {e}")
        raise


async def get_calls_by_business(
    session: AsyncSession,
    business_id: str,
    limit: int = 50
) -> List[CallLog]:
    """
    Get call logs for a specific business.

    Args:
        session: Database session
        business_id: Business UUID
        limit: Maximum number of results

    Returns:
        List of CallLog objects for the business
    """
    try:
        query = (
            select(CallLog)
            .where(CallLog.business_id == business_id)
            .order_by(desc(CallLog.call_start_time))
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    except Exception as e:
        logger.error(f"Error fetching calls for business {business_id}: {e}")
        raise


async def get_call_stats(
    session: AsyncSession,
    date_range: int = 30
) -> Dict[str, Any]:
    """
    Get call statistics for dashboard.

    Args:
        session: Database session
        date_range: Number of days to look back

    Returns:
        Dict with call metrics:
        - total_calls: Total call count in date range
        - answered_by_ai: Calls answered by AI
        - forwarded: Calls forwarded to human
        - missed: Missed calls
        - average_duration: Average call duration in seconds
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=date_range)

        # Total calls
        total_query = select(func.count(CallLog.id)).where(
            CallLog.call_start_time >= cutoff_date
        )
        total_result = await session.execute(total_query)
        total_calls = total_result.scalar()

        # Calls by status
        answered_query = select(func.count(CallLog.id)).where(
            CallLog.call_start_time >= cutoff_date,
            CallLog.call_status == "answered_by_ai"
        )
        answered_result = await session.execute(answered_query)
        answered_by_ai = answered_result.scalar()

        forwarded_query = select(func.count(CallLog.id)).where(
            CallLog.call_start_time >= cutoff_date,
            CallLog.call_status == "forwarded"
        )
        forwarded_result = await session.execute(forwarded_query)
        forwarded = forwarded_result.scalar()

        missed_query = select(func.count(CallLog.id)).where(
            CallLog.call_start_time >= cutoff_date,
            CallLog.call_status == "missed"
        )
        missed_result = await session.execute(missed_query)
        missed = missed_result.scalar()

        # Average call duration
        avg_duration_query = select(func.avg(CallLog.call_duration_seconds)).where(
            CallLog.call_start_time >= cutoff_date,
            CallLog.call_duration_seconds.isnot(None)
        )
        avg_duration_result = await session.execute(avg_duration_query)
        average_duration = avg_duration_result.scalar() or 0

        return {
            "total_calls": total_calls,
            "answered_by_ai": answered_by_ai,
            "forwarded": forwarded,
            "missed": missed,
            "average_duration": round(average_duration, 2),
        }

    except Exception as e:
        logger.error(f"Error fetching call stats: {e}")
        raise


async def get_recent_calls(session: AsyncSession, limit: int = 10) -> List[CallLog]:
    """
    Get most recent calls.

    Args:
        session: Database session
        limit: Number of recent calls to fetch

    Returns:
        List of recently created CallLog objects
    """
    try:
        query = select(CallLog).order_by(desc(CallLog.call_start_time)).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    except Exception as e:
        logger.error(f"Error fetching recent calls: {e}")
        raise
