"""
Twilio Phone Number service for database operations.
Provides read-only operations for Twilio phone number pool management.
"""
from sqlalchemy import select, func, and_, or_, case, desc, asc
from sqlalchemy.orm import Session, joinedload
from database.models import TwilioPhoneNumber, Business, Subscription
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


def get_pool_status(session: Session) -> Dict[str, int]:
    """
    Get overall phone number pool status.

    Returns:
        Dict with counts:
        - total_numbers: Total active phone numbers
        - available_numbers: Ready for assignment
        - assigned_numbers: Currently assigned to businesses
        - error_numbers: Numbers with errors
        - scheduled_for_release: Numbers marked for release
        - inactive_numbers: Numbers marked as inactive
    """
    try:
        # Total active numbers
        total_query = select(func.count(TwilioPhoneNumber.id)).where(
            TwilioPhoneNumber.is_active == True
        )
        total = session.execute(total_query).scalar() or 0

        # Available numbers
        available_query = select(func.count(TwilioPhoneNumber.id)).where(
            and_(
                TwilioPhoneNumber.status == 'available',
                TwilioPhoneNumber.is_active == True
            )
        )
        available = session.execute(available_query).scalar() or 0

        # Assigned numbers
        assigned_query = select(func.count(TwilioPhoneNumber.id)).where(
            and_(
                TwilioPhoneNumber.status == 'assigned',
                TwilioPhoneNumber.is_active == True
            )
        )
        assigned = session.execute(assigned_query).scalar() or 0

        # Error numbers
        error_query = select(func.count(TwilioPhoneNumber.id)).where(
            and_(
                TwilioPhoneNumber.is_active == True,
                or_(
                    TwilioPhoneNumber.status == 'error',
                    TwilioPhoneNumber.twilio_sync_error.isnot(None)
                )
            )
        )
        error = session.execute(error_query).scalar() or 0

        # Scheduled for release
        scheduled_query = select(func.count(TwilioPhoneNumber.id)).where(
            and_(
                TwilioPhoneNumber.is_active == True,
                TwilioPhoneNumber.release_scheduled_at.isnot(None),
                TwilioPhoneNumber.release_scheduled_at > datetime.now(timezone.utc)
            )
        )
        scheduled = session.execute(scheduled_query).scalar() or 0

        # Inactive numbers
        inactive_query = select(func.count(TwilioPhoneNumber.id)).where(
            TwilioPhoneNumber.is_active == False
        )
        inactive = session.execute(inactive_query).scalar() or 0

        return {
            "total_numbers": total,
            "available_numbers": available,
            "assigned_numbers": assigned,
            "error_numbers": error,
            "scheduled_for_release": scheduled,
            "inactive_numbers": inactive
        }

    except Exception as e:
        logger.error(f"Error fetching pool status: {e}")
        raise


def get_phone_numbers(
    session: Session,
    status_filter: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    include_inactive: bool = False
) -> Tuple[List[TwilioPhoneNumber], int]:
    """
    Get phone numbers with filters and pagination.

    Args:
        session: Database session
        status_filter: Filter by status (available, assigned, released, error)
        search_query: Search in phone number or business name
        limit: Maximum number of results
        offset: Pagination offset
        include_inactive: Include inactive numbers

    Returns:
        Tuple of (list of TwilioPhoneNumber objects, total count)
    """
    try:
        # Base query with business relationship loaded
        query = select(TwilioPhoneNumber).options(
            joinedload(TwilioPhoneNumber.business)
        )

        # Activity filter
        if not include_inactive:
            query = query.where(TwilioPhoneNumber.is_active == True)

        # Status filter
        if status_filter and status_filter.lower() != "all":
            if status_filter == "error":
                # Include both status='error' and any sync errors
                query = query.where(
                    or_(
                        TwilioPhoneNumber.status == 'error',
                        TwilioPhoneNumber.twilio_sync_error.isnot(None)
                    )
                )
            else:
                query = query.where(TwilioPhoneNumber.status == status_filter)

        # Search filter
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(
                or_(
                    TwilioPhoneNumber.phone_number.ilike(search_pattern),
                    TwilioPhoneNumber.twilio_phone_number_sid.ilike(search_pattern)
                )
            )

        # Get total count before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_count = session.execute(count_query).scalar() or 0

        # Order by: errors first, then by status, then by created date
        query = query.order_by(
            desc(TwilioPhoneNumber.twilio_sync_error.isnot(None)),
            TwilioPhoneNumber.status,
            desc(TwilioPhoneNumber.created_at)
        )

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = session.execute(query)
        phone_numbers = result.scalars().all()

        return list(phone_numbers), total_count

    except Exception as e:
        logger.error(f"Error fetching phone numbers: {e}")
        raise


def get_phone_number_stats(session: Session) -> Dict[str, Any]:
    """
    Get aggregated phone number statistics.

    Returns:
        Dict with various statistics:
        - pool_capacity: Current capacity percentage
        - avg_time_to_assignment: Average hours from purchase to first assignment
        - numbers_purchased_7d: Numbers purchased in last 7 days
        - numbers_assigned_7d: Numbers assigned in last 7 days
        - numbers_released_7d: Numbers released in last 7 days
        - oldest_available: Oldest available number age in days
        - sync_errors_count: Count of numbers with sync errors
        - last_sync_timestamp: Most recent sync timestamp
    """
    try:
        from config.settings import settings

        # Get pool capacity
        max_pool_size = getattr(settings, 'PN_ACTIVE_NUMBER_MAX_POOL_SIZE', 4)
        total_query = select(func.count(TwilioPhoneNumber.id)).where(
            TwilioPhoneNumber.is_active == True
        )
        total = session.execute(total_query).scalar() or 0
        pool_capacity = (total / max_pool_size * 100) if max_pool_size > 0 else 0

        # Numbers purchased in last 7 days
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        purchased_7d_query = select(func.count(TwilioPhoneNumber.id)).where(
            and_(
                TwilioPhoneNumber.purchase_date >= seven_days_ago,
                TwilioPhoneNumber.purchase_date.isnot(None)
            )
        )
        purchased_7d = session.execute(purchased_7d_query).scalar() or 0

        # Numbers assigned in last 7 days
        assigned_7d_query = select(func.count(TwilioPhoneNumber.id)).where(
            and_(
                TwilioPhoneNumber.assigned_at >= seven_days_ago,
                TwilioPhoneNumber.assigned_at.isnot(None)
            )
        )
        assigned_7d = session.execute(assigned_7d_query).scalar() or 0

        # Numbers released in last 7 days
        released_7d_query = select(func.count(TwilioPhoneNumber.id)).where(
            and_(
                TwilioPhoneNumber.released_at >= seven_days_ago,
                TwilioPhoneNumber.released_at.isnot(None)
            )
        )
        released_7d = session.execute(released_7d_query).scalar() or 0

        # Oldest available number
        oldest_available_query = select(TwilioPhoneNumber.purchase_date).where(
            and_(
                TwilioPhoneNumber.status == 'available',
                TwilioPhoneNumber.is_active == True,
                TwilioPhoneNumber.purchase_date.isnot(None)
            )
        ).order_by(asc(TwilioPhoneNumber.purchase_date)).limit(1)
        oldest_available_date = session.execute(oldest_available_query).scalar()
        oldest_available_days = None
        if oldest_available_date:
            oldest_available_days = (datetime.now(timezone.utc) - oldest_available_date).days

        # Sync errors count
        sync_errors_query = select(func.count(TwilioPhoneNumber.id)).where(
            TwilioPhoneNumber.twilio_sync_error.isnot(None)
        )
        sync_errors = session.execute(sync_errors_query).scalar() or 0

        # Last sync timestamp
        last_sync_query = select(TwilioPhoneNumber.last_twilio_sync_at).where(
            TwilioPhoneNumber.last_twilio_sync_at.isnot(None)
        ).order_by(desc(TwilioPhoneNumber.last_twilio_sync_at)).limit(1)
        last_sync = session.execute(last_sync_query).scalar()

        # Average time to assignment (for assigned numbers)
        # Calculate hours between purchase and first assignment
        avg_time_query = select(
            func.avg(
                func.extract('epoch', TwilioPhoneNumber.assigned_at - TwilioPhoneNumber.purchase_date) / 3600
            )
        ).where(
            and_(
                TwilioPhoneNumber.assigned_at.isnot(None),
                TwilioPhoneNumber.purchase_date.isnot(None)
            )
        )
        avg_time_hours = session.execute(avg_time_query).scalar()

        return {
            "pool_capacity_pct": round(pool_capacity, 1),
            "pool_capacity_count": total,
            "pool_capacity_max": max_pool_size,
            "avg_time_to_assignment_hours": round(avg_time_hours, 1) if avg_time_hours else None,
            "numbers_purchased_7d": purchased_7d,
            "numbers_assigned_7d": assigned_7d,
            "numbers_released_7d": released_7d,
            "oldest_available_days": oldest_available_days,
            "sync_errors_count": sync_errors,
            "last_sync_timestamp": last_sync
        }

    except Exception as e:
        logger.error(f"Error fetching phone number stats: {e}")
        raise


def get_recycling_candidates(session: Session) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get phone numbers eligible for recycling based on subscription status.

    Returns:
        Dict with two lists:
        - immediate: Numbers with expired subscriptions (canceled, unpaid, incomplete_expired)
        - grace_period: Numbers with past_due subscriptions (30+ days)
    """
    try:
        # Immediate recycling candidates
        # Subscription statuses: canceled, unpaid, incomplete_expired
        immediate_statuses = ['canceled', 'unpaid', 'incomplete_expired']

        immediate_query = (
            select(TwilioPhoneNumber, Business, Subscription)
            .join(Business, TwilioPhoneNumber.business_id == Business.id)
            .join(Subscription, Business.user_id == Subscription.user_id)
            .where(
                and_(
                    TwilioPhoneNumber.status == 'assigned',
                    TwilioPhoneNumber.is_active == True,
                    Subscription.status.in_(immediate_statuses)
                )
            )
            .order_by(desc(Subscription.updated_at))
        )

        immediate_results = session.execute(immediate_query).all()
        immediate_candidates = [
            {
                "phone_number": phone.phone_number,
                "phone_id": str(phone.id),
                "business_name": business.business_name or "Unnamed",
                "business_id": str(business.id),
                "subscription_status": subscription.status,
                "subscription_updated": subscription.updated_at,
                "days_in_status": (datetime.now(timezone.utc) - subscription.updated_at).days if subscription.updated_at else 0
            }
            for phone, business, subscription in immediate_results
        ]

        # Grace period candidates (past_due for 30+ days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        grace_query = (
            select(TwilioPhoneNumber, Business, Subscription)
            .join(Business, TwilioPhoneNumber.business_id == Business.id)
            .join(Subscription, Business.user_id == Subscription.user_id)
            .where(
                and_(
                    TwilioPhoneNumber.status == 'assigned',
                    TwilioPhoneNumber.is_active == True,
                    Subscription.status == 'past_due',
                    Subscription.updated_at <= thirty_days_ago
                )
            )
            .order_by(asc(Subscription.updated_at))  # Oldest first
        )

        grace_results = session.execute(grace_query).all()
        grace_candidates = [
            {
                "phone_number": phone.phone_number,
                "phone_id": str(phone.id),
                "business_name": business.business_name or "Unnamed",
                "business_id": str(business.id),
                "subscription_status": subscription.status,
                "subscription_updated": subscription.updated_at,
                "days_in_status": (datetime.now(timezone.utc) - subscription.updated_at).days if subscription.updated_at else 0
            }
            for phone, business, subscription in grace_results
        ]

        return {
            "immediate": immediate_candidates,
            "grace_period": grace_candidates
        }

    except Exception as e:
        logger.error(f"Error fetching recycling candidates: {e}")
        raise


def get_sync_health(session: Session) -> Dict[str, Any]:
    """
    Get Twilio sync health metrics.

    Returns:
        Dict with sync health info:
        - total_sync_errors: Count of numbers with sync errors
        - recent_sync_errors: List of recent errors (last 10)
        - numbers_not_synced_24h: Numbers not synced in 24+ hours
        - numbers_without_sid: Numbers without Twilio SID
        - last_successful_sync: Most recent successful sync timestamp
    """
    try:
        # Total sync errors
        sync_errors_query = select(func.count(TwilioPhoneNumber.id)).where(
            TwilioPhoneNumber.twilio_sync_error.isnot(None)
        )
        total_errors = session.execute(sync_errors_query).scalar() or 0

        # Recent sync errors (last 10)
        recent_errors_query = (
            select(TwilioPhoneNumber)
            .where(TwilioPhoneNumber.twilio_sync_error.isnot(None))
            .order_by(desc(TwilioPhoneNumber.last_twilio_sync_at))
            .limit(10)
        )
        recent_errors_result = session.execute(recent_errors_query).scalars().all()
        recent_errors = [
            {
                "phone_number": phone.phone_number,
                "error": phone.twilio_sync_error,
                "last_sync": phone.last_twilio_sync_at,
                "phone_id": str(phone.id)
            }
            for phone in recent_errors_result
        ]

        # Numbers not synced in 24+ hours
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        not_synced_query = select(func.count(TwilioPhoneNumber.id)).where(
            or_(
                TwilioPhoneNumber.last_twilio_sync_at.is_(None),
                TwilioPhoneNumber.last_twilio_sync_at < twenty_four_hours_ago
            )
        )
        not_synced_count = session.execute(not_synced_query).scalar() or 0

        # Numbers without Twilio SID
        without_sid_query = select(func.count(TwilioPhoneNumber.id)).where(
            or_(
                TwilioPhoneNumber.twilio_phone_number_sid.is_(None),
                TwilioPhoneNumber.twilio_phone_number_sid == ''
            )
        )
        without_sid_count = session.execute(without_sid_query).scalar() or 0

        # Last successful sync (no error)
        last_success_query = (
            select(TwilioPhoneNumber.last_twilio_sync_at)
            .where(
                and_(
                    TwilioPhoneNumber.last_twilio_sync_at.isnot(None),
                    TwilioPhoneNumber.twilio_sync_error.is_(None)
                )
            )
            .order_by(desc(TwilioPhoneNumber.last_twilio_sync_at))
            .limit(1)
        )
        last_success = session.execute(last_success_query).scalar()

        return {
            "total_sync_errors": total_errors,
            "recent_sync_errors": recent_errors,
            "numbers_not_synced_24h": not_synced_count,
            "numbers_without_sid": without_sid_count,
            "last_successful_sync": last_success
        }

    except Exception as e:
        logger.error(f"Error fetching sync health: {e}")
        raise


def get_subscription_status_breakdown(session: Session) -> Dict[str, int]:
    """
    Get breakdown of assigned phone numbers by subscription status.

    Returns:
        Dict mapping subscription status to count of assigned numbers
    """
    try:
        query = (
            select(Subscription.status, func.count(TwilioPhoneNumber.id))
            .join(Business, TwilioPhoneNumber.business_id == Business.id)
            .join(Subscription, Business.user_id == Subscription.user_id)
            .where(
                and_(
                    TwilioPhoneNumber.status == 'assigned',
                    TwilioPhoneNumber.is_active == True
                )
            )
            .group_by(Subscription.status)
        )

        results = session.execute(query).all()

        breakdown = {status: count for status, count in results}

        return breakdown

    except Exception as e:
        logger.error(f"Error fetching subscription status breakdown: {e}")
        raise


def get_old_unassigned_numbers(session: Session, older_than_days: int = 30) -> List[Dict[str, Any]]:
    """
    Get available numbers that have been unassigned for a long time.

    Args:
        session: Database session
        older_than_days: Threshold in days (default 30)

    Returns:
        List of dicts with old unassigned number info
    """
    try:
        threshold_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

        query = (
            select(TwilioPhoneNumber)
            .where(
                and_(
                    TwilioPhoneNumber.status == 'available',
                    TwilioPhoneNumber.is_active == True,
                    TwilioPhoneNumber.purchase_date.isnot(None),
                    TwilioPhoneNumber.purchase_date < threshold_date,
                    or_(
                        TwilioPhoneNumber.assigned_at.is_(None),
                        TwilioPhoneNumber.released_at >= TwilioPhoneNumber.assigned_at  # Released more recently than assigned
                    )
                )
            )
            .order_by(asc(TwilioPhoneNumber.purchase_date))
        )

        results = session.execute(query).scalars().all()

        old_numbers = [
            {
                "phone_number": phone.phone_number,
                "phone_id": str(phone.id),
                "purchase_date": phone.purchase_date,
                "days_available": (datetime.now(timezone.utc) - phone.purchase_date).days if phone.purchase_date else 0,
                "last_released": phone.released_at,
                "twilio_sid": phone.twilio_phone_number_sid
            }
            for phone in results
        ]

        return old_numbers

    except Exception as e:
        logger.error(f"Error fetching old unassigned numbers: {e}")
        raise


def get_pool_history_metrics(session: Session, days: int = 30) -> Dict[str, Any]:
    """
    Get time-series metrics for pool activity over the specified period.

    Args:
        session: Database session
        days: Number of days to look back (default 30)

    Returns:
        Dict with daily activity metrics
    """
    try:
        threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Purchases by day
        purchases_query = (
            select(
                func.date_trunc('day', TwilioPhoneNumber.purchase_date).label('day'),
                func.count(TwilioPhoneNumber.id).label('count')
            )
            .where(
                and_(
                    TwilioPhoneNumber.purchase_date.isnot(None),
                    TwilioPhoneNumber.purchase_date >= threshold_date
                )
            )
            .group_by('day')
            .order_by('day')
        )
        purchases_results = session.execute(purchases_query).all()
        purchases_by_day = {str(day.date()): count for day, count in purchases_results}

        # Assignments by day
        assignments_query = (
            select(
                func.date_trunc('day', TwilioPhoneNumber.assigned_at).label('day'),
                func.count(TwilioPhoneNumber.id).label('count')
            )
            .where(
                and_(
                    TwilioPhoneNumber.assigned_at.isnot(None),
                    TwilioPhoneNumber.assigned_at >= threshold_date
                )
            )
            .group_by('day')
            .order_by('day')
        )
        assignments_results = session.execute(assignments_query).all()
        assignments_by_day = {str(day.date()): count for day, count in assignments_results}

        # Releases by day
        releases_query = (
            select(
                func.date_trunc('day', TwilioPhoneNumber.released_at).label('day'),
                func.count(TwilioPhoneNumber.id).label('count')
            )
            .where(
                and_(
                    TwilioPhoneNumber.released_at.isnot(None),
                    TwilioPhoneNumber.released_at >= threshold_date
                )
            )
            .group_by('day')
            .order_by('day')
        )
        releases_results = session.execute(releases_query).all()
        releases_by_day = {str(day.date()): count for day, count in releases_results}

        return {
            "purchases_by_day": purchases_by_day,
            "assignments_by_day": assignments_by_day,
            "releases_by_day": releases_by_day,
            "period_days": days
        }

    except Exception as e:
        logger.error(f"Error fetching pool history metrics: {e}")
        raise
