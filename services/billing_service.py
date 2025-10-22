"""
Billing service for database operations.
Provides read-only operations for subscriptions, invoices, and credits for Phase 2.
"""
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Subscription, Invoice, CreditBalance, CreditTransaction
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


async def get_subscriptions(
    session: AsyncSession,
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

        result = await session.execute(query)
        subscriptions = result.scalars().all()

        return list(subscriptions)

    except Exception as e:
        logger.error(f"Error fetching subscriptions: {e}")
        raise


async def get_subscription_by_user(
    session: AsyncSession,
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
        result = await session.execute(query)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching subscription for user {user_id}: {e}")
        raise


async def get_invoices(
    session: AsyncSession,
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

        result = await session.execute(query)
        invoices = result.scalars().all()

        return list(invoices)

    except Exception as e:
        logger.error(f"Error fetching invoices: {e}")
        raise


async def get_invoices_by_user(
    session: AsyncSession,
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
        result = await session.execute(query)
        return list(result.scalars().all())

    except Exception as e:
        logger.error(f"Error fetching invoices for user {user_id}: {e}")
        raise


async def get_billing_stats(
    session: AsyncSession,
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
        active_result = await session.execute(active_query)
        active_subs = active_result.scalar()

        # Trial subscriptions
        trial_query = select(func.count(Subscription.id)).where(
            Subscription.status == "trialing"
        )
        trial_result = await session.execute(trial_query)
        trial_subs = trial_result.scalar()

        # Revenue from paid invoices in date range
        cutoff_date = datetime.utcnow() - timedelta(days=date_range)
        revenue_query = select(func.sum(Invoice.amount_paid)).where(
            Invoice.status == "paid",
            Invoice.created_at >= cutoff_date
        )
        revenue_result = await session.execute(revenue_query)
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


async def get_credit_balance(
    session: AsyncSession,
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
        result = await session.execute(query)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching credit balance for user {user_id}: {e}")
        raise


async def get_credit_transactions(
    session: AsyncSession,
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
        result = await session.execute(query)
        return list(result.scalars().all())

    except Exception as e:
        logger.error(f"Error fetching credit transactions for user {user_id}: {e}")
        raise


async def get_low_balance_users(
    session: AsyncSession,
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
        result = await session.execute(query)
        return list(result.scalars().all())

    except Exception as e:
        logger.error(f"Error fetching low balance users: {e}")
        raise
