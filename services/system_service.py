"""
System service for health checks and statistics.
Provides system monitoring and database metrics for Phase 4.
"""
from sqlalchemy import select, func, text, join
from sqlalchemy.orm import Session
from database.models import (
    User, Business, AIAgentConfiguration, CallLog, Appointment,
    Subscription, CreditTransaction, PromotionCode
)
from typing import Dict, Any
from datetime import datetime, timedelta
import sys
import platform
import logging

logger = logging.getLogger(__name__)


def check_database_health(session: Session) -> Dict[str, Any]:
    """
    Check database connection and health.

    Args:
        session: Database session

    Returns:
        Dict with health status:
        - status: "connected" or "error"
        - response_time_ms: Query response time in milliseconds
        - error: Error message if failed
    """
    try:
        start_time = datetime.now()

        # Simple query to test connection
        result = session.execute(text("SELECT 1"))
        result.scalar()

        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000

        return {
            "status": "connected",
            "response_time_ms": round(response_time, 2),
            "error": None
        }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "error",
            "response_time_ms": None,
            "error": str(e)
        }


def get_table_row_counts(session: Session) -> Dict[str, Any]:
    """
    Get row counts for all major tables.

    Args:
        session: Database session

    Returns:
        Dict with counts for each table
    """
    try:
        counts = {}

        # Users
        total_users = session.execute(select(func.count(User.id))).scalar()
        active_users = session.execute(
            select(func.count(User.id)).where(User.is_active == True)
        ).scalar()
        counts["users_total"] = total_users
        counts["users_active"] = active_users

        # Businesses
        counts["businesses"] = session.execute(
            select(func.count(Business.id))
        ).scalar()

        # AI Agents
        counts["ai_agents"] = session.execute(
            select(func.count(AIAgentConfiguration.id))
        ).scalar()

        # Call Logs
        counts["call_logs_total"] = session.execute(
            select(func.count(CallLog.id))
        ).scalar()

        # Call logs in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        counts["call_logs_30d"] = session.execute(
            select(func.count(CallLog.id)).where(CallLog.created_at >= thirty_days_ago)
        ).scalar()

        # Appointments
        now = datetime.utcnow()
        counts["appointments_total"] = session.execute(
            select(func.count(Appointment.id))
        ).scalar()

        counts["appointments_upcoming"] = session.execute(
            select(func.count(Appointment.id)).where(
                Appointment.start_time >= now,
                Appointment.status == "confirmed"
            )
        ).scalar()

        counts["appointments_past"] = session.execute(
            select(func.count(Appointment.id)).where(Appointment.start_time < now)
        ).scalar()

        # Subscriptions
        counts["subscriptions_active"] = session.execute(
            select(func.count(Subscription.id)).where(Subscription.status == "active")
        ).scalar()

        counts["subscriptions_trial"] = session.execute(
            select(func.count(Subscription.id)).where(Subscription.status == "trialing")
        ).scalar()

        counts["subscriptions_cancelled"] = session.execute(
            select(func.count(Subscription.id)).where(Subscription.status == "canceled")
        ).scalar()

        # Credit Transactions
        counts["credit_transactions"] = session.execute(
            select(func.count(CreditTransaction.id))
        ).scalar()

        # Promotion Codes
        counts["promotion_codes"] = session.execute(
            select(func.count(PromotionCode.id))
        ).scalar()

        return counts

    except Exception as e:
        logger.error(f"Error getting table row counts: {e}")
        raise


def get_growth_stats(session: Session) -> Dict[str, Any]:
    """
    Get growth statistics for recent periods.

    Args:
        session: Database session

    Returns:
        Dict with growth metrics
    """
    try:
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        stats = {}

        # New users
        stats["new_users_today"] = session.execute(
            select(func.count(User.id)).where(User.created_at >= today)
        ).scalar()

        stats["new_users_7d"] = session.execute(
            select(func.count(User.id)).where(User.created_at >= seven_days_ago)
        ).scalar()

        stats["new_users_30d"] = session.execute(
            select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
        ).scalar()

        # New businesses
        stats["new_businesses_today"] = session.execute(
            select(func.count(Business.id)).where(Business.created_at >= today)
        ).scalar()

        stats["new_businesses_7d"] = session.execute(
            select(func.count(Business.id)).where(Business.created_at >= seven_days_ago)
        ).scalar()

        stats["new_businesses_30d"] = session.execute(
            select(func.count(Business.id)).where(Business.created_at >= thirty_days_ago)
        ).scalar()

        # New calls
        stats["new_calls_today"] = session.execute(
            select(func.count(CallLog.id)).where(CallLog.created_at >= today)
        ).scalar()

        stats["new_calls_7d"] = session.execute(
            select(func.count(CallLog.id)).where(CallLog.created_at >= seven_days_ago)
        ).scalar()

        return stats

    except Exception as e:
        logger.error(f"Error getting growth stats: {e}")
        raise


def get_data_quality_metrics(session: Session) -> Dict[str, Any]:
    """
    Get data quality metrics (completeness).

    Args:
        session: Database session

    Returns:
        Dict with quality metrics
    """
    try:
        metrics = {}

        # Total users
        total_users = session.execute(select(func.count(User.id))).scalar()

        # Users with businesses
        users_with_businesses = session.execute(
            select(func.count(func.distinct(Business.user_id)))
        ).scalar()

        if total_users > 0:
            metrics["users_with_businesses_count"] = users_with_businesses
            metrics["users_with_businesses_pct"] = round(
                (users_with_businesses / total_users) * 100, 1
            )
        else:
            metrics["users_with_businesses_count"] = 0
            metrics["users_with_businesses_pct"] = 0

        # Users with active agents
        # AIAgentConfiguration is linked to Business, not directly to User
        # Need to join through Business to get user_id
        users_with_agents = session.execute(
            select(func.count(func.distinct(Business.user_id)))
            .select_from(
                join(Business, AIAgentConfiguration, Business.id == AIAgentConfiguration.business_id)
            )
        ).scalar()

        if total_users > 0:
            metrics["users_with_agents_count"] = users_with_agents
            metrics["users_with_agents_pct"] = round(
                (users_with_agents / total_users) * 100, 1
            )
        else:
            metrics["users_with_agents_count"] = 0
            metrics["users_with_agents_pct"] = 0

        # Users with subscriptions
        users_with_subscriptions = session.execute(
            select(func.count(func.distinct(Subscription.user_id))).where(
                Subscription.status.in_(["active", "trialing"])
            )
        ).scalar()

        if total_users > 0:
            metrics["users_with_subscriptions_count"] = users_with_subscriptions
            metrics["users_with_subscriptions_pct"] = round(
                (users_with_subscriptions / total_users) * 100, 1
            )
        else:
            metrics["users_with_subscriptions_count"] = 0
            metrics["users_with_subscriptions_pct"] = 0

        return metrics

    except Exception as e:
        logger.error(f"Error getting data quality metrics: {e}")
        raise


def get_system_info() -> Dict[str, Any]:
    """
    Get system information (versions, environment).

    Returns:
        Dict with system info
    """
    try:
        import streamlit as st
        from config.settings import settings

        return {
            "python_version": sys.version.split()[0],
            "platform": platform.system(),
            "platform_version": platform.release(),
            "streamlit_version": st.__version__,
            "database_url": str(settings.DATABASE_URL_SYNC).split("@")[-1] if settings.DATABASE_URL_SYNC else "N/A",  # Hide credentials
            "environment": getattr(settings, "APP_ENV", "unknown"),
            "current_time": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return {
            "error": str(e)
        }


def generate_system_report(session: Session) -> Dict[str, Any]:
    """
    Generate comprehensive system report.

    Args:
        session: Database session

    Returns:
        Dict with all system metrics combined
    """
    try:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "database_health": check_database_health(session),
            "table_counts": get_table_row_counts(session),
            "growth_stats": get_growth_stats(session),
            "data_quality": get_data_quality_metrics(session),
            "system_info": get_system_info()
        }

    except Exception as e:
        logger.error(f"Error generating system report: {e}")
        raise
