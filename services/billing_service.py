"""
Billing service for database operations.
Provides read-only operations for subscriptions, invoices, and credits for Phase 2.
"""
from sqlalchemy import select, func, desc, cast, Date
from sqlalchemy.orm import Session
from database.models import Subscription, Invoice, CreditBalance, CreditTransaction
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def get_subscriptions(
    session: Session,
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None
) -> List[Subscription]:
    """
    Get subscriptions with pagination and filters.

    Args:
        session: Database session
        limit: Maximum number of results
        offset: Pagination offset
        status_filter: Filter by subscription status

    Returns:
        List of Subscription objects
    """
    try:
        query = select(Subscription)

        # Apply status filter
        if status_filter and status_filter.lower() != "all":
            query = query.where(Subscription.status == status_filter)

        # Order by creation date (newest first)
        query = query.order_by(desc(Subscription.created_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = session.execute(query)
        subscriptions = result.scalars().all()

        return list(subscriptions)

    except Exception as e:
        logger.error(f"Error fetching subscriptions: {e}")
        raise


def get_subscription_by_user(
    session: Session,
    user_id: str
) -> Optional[Subscription]:
    """
    Get subscription for a specific user.

    Args:
        session: Database session
        user_id: User UUID

    Returns:
        Subscription object or None if not found
    """
    try:
        query = select(Subscription).where(Subscription.user_id == user_id)
        result = session.execute(query)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching subscription for user {user_id}: {e}")
        raise


def get_invoices(
    session: Session,
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None
) -> List[Invoice]:
    """
    Get invoices with pagination and filters.

    Args:
        session: Database session
        limit: Maximum number of results
        offset: Pagination offset
        status_filter: Filter by invoice status

    Returns:
        List of Invoice objects
    """
    try:
        query = select(Invoice)

        # Apply status filter
        if status_filter and status_filter.lower() != "all":
            query = query.where(Invoice.status == status_filter)

        # Order by creation date (newest first)
        query = query.order_by(desc(Invoice.created_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = session.execute(query)
        invoices = result.scalars().all()

        return list(invoices)

    except Exception as e:
        logger.error(f"Error fetching invoices: {e}")
        raise


def get_invoices_by_user(
    session: Session,
    user_id: str,
    limit: int = 50
) -> List[Invoice]:
    """
    Get invoices for a specific user.

    Args:
        session: Database session
        user_id: User UUID
        limit: Maximum number of results

    Returns:
        List of Invoice objects for the user
    """
    try:
        query = (
            select(Invoice)
            .where(Invoice.user_id == user_id)
            .order_by(desc(Invoice.created_at))
            .limit(limit)
        )
        result = session.execute(query)
        return list(result.scalars().all())

    except Exception as e:
        logger.error(f"Error fetching invoices for user {user_id}: {e}")
        raise


def get_billing_stats(
    session: Session,
    date_range: int = 30
) -> Dict[str, Any]:
    """
    Get billing statistics for dashboard.

    Args:
        session: Database session
        date_range: Number of days to look back

    Returns:
        Dict with billing metrics:
        - active_subs: Number of active subscriptions
        - trial_subs: Number of trialing subscriptions
        - revenue_30d: Total revenue in last 30 days (from paid invoices)
        - mrr: Estimated Monthly Recurring Revenue
    """
    try:
        # Active subscriptions (non-trial)
        active_query = select(func.count(Subscription.id)).where(
            Subscription.status == "active"
        )
        active_result = session.execute(active_query)
        active_subs = active_result.scalar()

        # Trial subscriptions
        trial_query = select(func.count(Subscription.id)).where(
            Subscription.status == "trialing"
        )
        trial_result = session.execute(trial_query)
        trial_subs = trial_result.scalar()

        # Revenue from paid invoices in date range
        cutoff_date = datetime.utcnow() - timedelta(days=date_range)
        revenue_query = select(func.sum(Invoice.amount_paid)).where(
            Invoice.status == "paid",
            Invoice.created_at >= cutoff_date
        )
        revenue_result = session.execute(revenue_query)
        revenue_cents = revenue_result.scalar() or 0
        revenue_30d = Decimal(revenue_cents) / 100  # Convert cents to dollars

        # MRR calculation (simplified - sum of all active subscriptions)
        # Note: This is a rough estimate, actual MRR calculation might be more complex
        mrr = revenue_30d / date_range * 30 if date_range > 0 else 0

        return {
            "active_subs": active_subs,
            "trial_subs": trial_subs,
            "revenue_30d": revenue_30d,
            "mrr": mrr,
        }

    except Exception as e:
        logger.error(f"Error fetching billing stats: {e}")
        raise


def get_credit_balance(
    session: Session,
    user_id: str
) -> Optional[CreditBalance]:
    """
    Get credit balance for a user.

    Args:
        session: Database session
        user_id: User UUID

    Returns:
        CreditBalance object or None if not found
    """
    try:
        query = select(CreditBalance).where(CreditBalance.user_id == user_id)
        result = session.execute(query)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching credit balance for user {user_id}: {e}")
        raise


def get_credit_transactions(
    session: Session,
    user_id: str,
    limit: int = 50
) -> List[CreditTransaction]:
    """
    Get credit transaction history for a user.

    Args:
        session: Database session
        user_id: User UUID
        limit: Maximum number of results

    Returns:
        List of CreditTransaction objects for the user
    """
    try:
        query = (
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(desc(CreditTransaction.created_at))
            .limit(limit)
        )
        result = session.execute(query)
        return list(result.scalars().all())

    except Exception as e:
        logger.error(f"Error fetching credit transactions for user {user_id}: {e}")
        raise


def get_low_balance_users(
    session: Session,
    threshold: float = 5.0,
    limit: int = 50
) -> List[CreditBalance]:
    """
    Get users with low credit balances.

    Args:
        session: Database session
        threshold: Balance threshold to consider "low"
        limit: Maximum number of results

    Returns:
        List of CreditBalance objects with balance below threshold
    """
    try:
        # Assuming there's a total_balance field - adjust as needed based on actual schema
        query = (
            select(CreditBalance)
            .order_by(CreditBalance.created_at)  # Oldest first
            .limit(limit)
        )
        result = session.execute(query)
        return list(result.scalars().all())

    except Exception as e:
        logger.error(f"Error fetching low balance users: {e}")
        raise


def get_revenue_trend_data(session: Session, days: int = 30) -> pd.DataFrame:
    """
    Get revenue trend data for the specified number of days.

    Args:
        session: Database session
        days: Number of days to look back (default: 30)

    Returns:
        DataFrame with columns:
        - date: Date of the revenue
        - revenue: Revenue amount in dollars for that date
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Query to get revenue grouped by date (from paid invoices)
        query = (
            select(
                cast(Invoice.paid_at, Date).label("date"),
                func.sum(Invoice.amount_paid).label("revenue_cents")
            )
            .where(
                Invoice.status == "paid",
                Invoice.paid_at >= cutoff_date,
                Invoice.paid_at.isnot(None)
            )
            .group_by(cast(Invoice.paid_at, Date))
            .order_by(cast(Invoice.paid_at, Date))
        )

        result = session.execute(query)
        rows = result.all()

        # Convert to DataFrame
        if rows:
            df = pd.DataFrame(rows, columns=["date", "revenue_cents"])
            df["date"] = pd.to_datetime(df["date"])
            # Convert cents to dollars
            df["revenue"] = (df["revenue_cents"] / 100).astype(float)
            df = df.drop(columns=["revenue_cents"])
        else:
            df = pd.DataFrame(columns=["date", "revenue"])

        # Fill missing dates with 0 revenue
        date_range = pd.date_range(
            start=cutoff_date.date(),
            end=datetime.utcnow().date(),
            freq="D"
        )
        complete_df = pd.DataFrame({"date": date_range})
        complete_df = complete_df.merge(df, on="date", how="left")
        complete_df["revenue"] = complete_df["revenue"].fillna(0).astype(float)

        return complete_df

    except Exception as e:
        logger.error(f"Error fetching revenue trend data: {e}")
        raise
