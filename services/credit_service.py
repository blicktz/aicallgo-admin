"""
Credit service for credit operations.

Provides data access layer for credit operations with validation
and atomic transactions.
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
import logging

# Add web-backend to path for CRUD imports
backend_path = Path(__file__).parent.parent.parent / "web-backend"
sys.path.insert(0, str(backend_path))

from app.crud.crud_credit_sync import credit_transaction_sync, credit_balance_sync
from app.models import CreditTransaction, CreditBalance
from app.models.credit_models import CreditTransactionType

from services.audit_service import log_credit_action

logger = logging.getLogger(__name__)


def get_credit_balance(session: Session, user_id: str) -> Optional[CreditBalance]:
    """
    Get user's current credit balance with breakdown.
    Uses: crud_credit_sync.credit_balance_sync.get_by_user_id()
    """
    try:
        balance = credit_balance_sync.get_by_user_id(session, user_id=user_id)
        return balance
    except Exception as e:
        logger.error(f"Error fetching credit balance for {user_id}: {e}")
        raise


def get_credit_transactions(
    session: Session,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    transaction_type: Optional[CreditTransactionType] = None
) -> List[CreditTransaction]:
    """
    Get user's transaction history with pagination.
    Uses: crud_credit_sync.credit_transaction_sync.get_user_transactions()
    """
    try:
        transactions = credit_transaction_sync.get_user_transactions(
            session,
            user_id=user_id,
            limit=limit,
            offset=offset,
            transaction_type=transaction_type
        )
        return transactions
    except Exception as e:
        logger.error(f"Error fetching credit transactions for {user_id}: {e}")
        raise


def validate_adjustment(amount: Decimal, reason: str) -> tuple[bool, str]:
    """
    Validate credit adjustment parameters.

    Rules:
    - Amount must be non-zero
    - Reason must be >= 10 characters

    Returns:
        (is_valid, error_message)
    """
    if amount == 0:
        return False, "Adjustment amount must be non-zero"

    if abs(amount) > 10000:
        return False, "Adjustment amount exceeds maximum allowed (10,000 min)"

    if not reason or len(reason.strip()) < 10:
        return False, "Reason must be at least 10 characters"

    return True, ""


def adjust_credits(
    session: Session,
    user_id: str,
    amount: Decimal,
    reason: str,
    admin_username: str,
    transaction_type: CreditTransactionType = CreditTransactionType.ADJUSTMENT
) -> CreditTransaction:
    """
    Adjust user's credits with full audit trail.

    Steps:
    1. Validate inputs
    2. Get/create credit balance
    3. Create transaction with metadata
    4. Update balance atomically
    5. Log audit trail
    6. Return transaction

    Transaction metadata includes:
    {
        "admin_username": str,
        "admin_reason": str,
        "adjustment_type": "manual_admin",
        "ip_address": "admin_board"
    }

    Uses:
    - crud_credit_sync.credit_transaction_sync.create_transaction()
    """
    try:
        # Validate inputs
        is_valid, error_message = validate_adjustment(amount, reason)
        if not is_valid:
            raise ValueError(error_message)

        # Generate audit metadata
        metadata = log_credit_action(
            session=session,
            action_type=transaction_type.value,
            admin_username=admin_username,
            user_id=str(user_id),
            amount=amount,
            reason=reason
        )

        # Create transaction with metadata
        # The create_transaction method automatically updates the balance
        transaction = credit_transaction_sync.create_transaction(
            db=session,
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            description=f"Admin adjustment by {admin_username}: {reason}",
            metadata=metadata
        )

        return transaction

    except Exception as e:
        logger.error(f"Error adjusting credits for {user_id}: {e}")
        raise


def calculate_adjustment_preview(
    session: Session,
    user_id: str,
    amount: Decimal
) -> Dict[str, Decimal]:
    """
    Preview credit adjustment without committing.

    Returns:
        {
            "current_balance": Decimal,
            "adjustment_amount": Decimal,
            "new_balance": Decimal
        }
    """
    try:
        # Get current balance
        balance = credit_balance_sync.get_by_user_id(session, user_id=user_id)

        current_balance = balance.total_balance if balance else Decimal("0.0")
        new_balance = current_balance + amount

        return {
            "current_balance": current_balance,
            "adjustment_amount": amount,
            "new_balance": new_balance
        }

    except Exception as e:
        logger.error(f"Error calculating adjustment preview for {user_id}: {e}")
        raise
