"""
Appointment service for database operations.
Provides read-only operations for Phase 4.
"""
from sqlalchemy import select, func, or_, desc, and_
from sqlalchemy.orm import Session, joinedload
from database.models import Appointment, AppointmentEndUser, User, Business, CallLog
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_appointments(
    session: Session,
    limit: int = 50,
    offset: int = 0,
    search_query: Optional[str] = None,
    status: Optional[str] = None,
    booking_source: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Appointment]:
    """
    Get appointments with pagination and filters.

    Args:
        session: Database session
        limit: Maximum number of results
        offset: Pagination offset
        search_query: Search in user email, end user name/email, or title
        status: Filter by status (confirmed/cancelled/completed/no_show)
        booking_source: Filter by booking source (ai_call/manual)
        start_date: Filter by start_time >= start_date
        end_date: Filter by start_time <= end_date

    Returns:
        List of Appointment objects with relationships loaded
    """
    try:
        query = select(Appointment)

        # Eager load relationships
        query = query.options(
            joinedload(Appointment.user),
            joinedload(Appointment.business),
            joinedload(Appointment.end_user),
            joinedload(Appointment.call_log)
        )

        # Apply search filter (requires joins)
        if search_query:
            search_pattern = f"%{search_query}%"
            # Join with user and end_user for search
            query = query.join(Appointment.user, isouter=True)
            query = query.join(Appointment.end_user, isouter=True)
            query = query.where(
                or_(
                    User.email.ilike(search_pattern),
                    AppointmentEndUser.full_name.ilike(search_pattern),
                    AppointmentEndUser.email.ilike(search_pattern),
                    Appointment.title.ilike(search_pattern)
                )
            )

        # Apply status filter
        if status and status.lower() != "all":
            query = query.where(Appointment.status == status)

        # Apply booking source filter
        if booking_source and booking_source.lower() != "all":
            query = query.where(Appointment.booking_source == booking_source)

        # Apply date range filters
        if start_date:
            query = query.where(Appointment.start_time >= start_date)

        if end_date:
            query = query.where(Appointment.start_time <= end_date)

        # Order by start time (newest first)
        query = query.order_by(desc(Appointment.start_time))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = session.execute(query)
        appointments = result.unique().scalars().all()

        return list(appointments)

    except Exception as e:
        logger.error(f"Error fetching appointments: {e}")
        raise


def get_appointment_by_id(session: Session, appointment_id: str) -> Optional[Appointment]:
    """
    Get appointment by ID with all relationships loaded.

    Args:
        session: Database session
        appointment_id: Appointment UUID

    Returns:
        Appointment object or None if not found
    """
    try:
        query = select(Appointment).where(Appointment.id == appointment_id)
        # Eager load relationships
        query = query.options(
            joinedload(Appointment.user),
            joinedload(Appointment.business),
            joinedload(Appointment.end_user),
            joinedload(Appointment.call_log)
        )
        result = session.execute(query)
        return result.unique().scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching appointment {appointment_id}: {e}")
        raise


def get_appointment_stats(
    session: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Get appointment statistics.

    Args:
        session: Database session
        start_date: Filter by start_time >= start_date
        end_date: Filter by start_time <= end_date

    Returns:
        Dict with metrics:
        - total_appointments: Total count
        - by_status: Breakdown by status (confirmed, cancelled, completed, no_show)
        - by_booking_source: Breakdown by booking source (ai_call, manual)
    """
    try:
        # Base query
        base_query = select(Appointment)

        # Apply date filters
        if start_date:
            base_query = base_query.where(Appointment.start_time >= start_date)
        if end_date:
            base_query = base_query.where(Appointment.start_time <= end_date)

        # Total appointments
        total_query = select(func.count(Appointment.id))
        if start_date:
            total_query = total_query.where(Appointment.start_time >= start_date)
        if end_date:
            total_query = total_query.where(Appointment.start_time <= end_date)

        total_result = session.execute(total_query)
        total_appointments = total_result.scalar()

        # By status
        status_query = select(
            Appointment.status,
            func.count(Appointment.id).label('count')
        )
        if start_date:
            status_query = status_query.where(Appointment.start_time >= start_date)
        if end_date:
            status_query = status_query.where(Appointment.start_time <= end_date)
        status_query = status_query.group_by(Appointment.status)

        status_result = session.execute(status_query)
        by_status = {row.status: row.count for row in status_result}

        # By booking source
        source_query = select(
            Appointment.booking_source,
            func.count(Appointment.id).label('count')
        )
        if start_date:
            source_query = source_query.where(Appointment.start_time >= start_date)
        if end_date:
            source_query = source_query.where(Appointment.start_time <= end_date)
        source_query = source_query.group_by(Appointment.booking_source)

        source_result = session.execute(source_query)
        by_booking_source = {row.booking_source: row.count for row in source_result}

        return {
            "total_appointments": total_appointments,
            "by_status": by_status,
            "by_booking_source": by_booking_source,
        }

    except Exception as e:
        logger.error(f"Error fetching appointment stats: {e}")
        raise


def get_end_user_by_id(session: Session, end_user_id: str) -> Optional[AppointmentEndUser]:
    """
    Get appointment end user by ID.

    Args:
        session: Database session
        end_user_id: AppointmentEndUser UUID

    Returns:
        AppointmentEndUser object or None if not found
    """
    try:
        query = select(AppointmentEndUser).where(AppointmentEndUser.id == end_user_id)
        result = session.execute(query)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching end user {end_user_id}: {e}")
        raise


def get_upcoming_appointments(
    session: Session,
    user_id: Optional[str] = None,
    limit: int = 10
) -> List[Appointment]:
    """
    Get upcoming appointments (future, confirmed status).

    Args:
        session: Database session
        user_id: Optional filter by user ID
        limit: Maximum number of results

    Returns:
        List of Appointment objects
    """
    try:
        now = datetime.utcnow()

        query = select(Appointment).where(
            and_(
                Appointment.start_time >= now,
                Appointment.status == "confirmed"
            )
        )

        # Eager load relationships
        query = query.options(
            joinedload(Appointment.user),
            joinedload(Appointment.end_user)
        )

        if user_id:
            query = query.where(Appointment.user_id == user_id)

        # Order by start time (soonest first)
        query = query.order_by(Appointment.start_time)

        # Apply limit
        query = query.limit(limit)

        result = session.execute(query)
        appointments = result.unique().scalars().all()

        return list(appointments)

    except Exception as e:
        logger.error(f"Error fetching upcoming appointments: {e}")
        raise


def get_past_appointments(
    session: Session,
    user_id: Optional[str] = None,
    limit: int = 10
) -> List[Appointment]:
    """
    Get past appointments (past start time).

    Args:
        session: Database session
        user_id: Optional filter by user ID
        limit: Maximum number of results

    Returns:
        List of Appointment objects
    """
    try:
        now = datetime.utcnow()

        query = select(Appointment).where(Appointment.start_time < now)

        # Eager load relationships
        query = query.options(
            joinedload(Appointment.user),
            joinedload(Appointment.end_user)
        )

        if user_id:
            query = query.where(Appointment.user_id == user_id)

        # Order by start time (most recent first)
        query = query.order_by(desc(Appointment.start_time))

        # Apply limit
        query = query.limit(limit)

        result = session.execute(query)
        appointments = result.unique().scalars().all()

        return list(appointments)

    except Exception as e:
        logger.error(f"Error fetching past appointments: {e}")
        raise
