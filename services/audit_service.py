"""
Audit service for tracking admin actions.

For Phase 3, we use existing transaction metadata fields.
For Phase 4+, we'll create a dedicated admin_audit_log table.
"""
import json
from datetime import datetime, UTC
from typing import Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


def log_entitlement_action(
    session: Session,
    action_type: str,  # "grant", "revoke", "delete"
    admin_username: str,
    user_id: str,
    feature_key: str,
    has_access: Optional[bool],
    notes: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log entitlement action.

    For Phase 3: Store in UserFeatureOverride.notes field with structured format
    Format: "[ADMIN: {username} @ {timestamp}] {notes}"

    For Phase 4+: Write to dedicated admin_audit_log table
    """
    audit_prefix = f"[ADMIN: {admin_username} @ {datetime.now(UTC).isoformat()}]"
    structured_notes = f"{audit_prefix} {notes}"

    # Update the notes field with audit trail
    # This is handled in the entitlement_service.create_feature_override()

    logger.info(
        "Entitlement action logged",
        extra={
            "action": action_type,
            "admin": admin_username,
            "user_id": user_id,
            "feature_key": feature_key,
            "has_access": has_access
        }
    )


def log_credit_action(
    session: Session,
    action_type: str,  # "adjustment", "refund"
    admin_username: str,
    user_id: str,
    amount: Decimal,
    reason: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create audit metadata for credit transaction.

    Returns JSON metadata to be stored in CreditTransaction.transaction_metadata
    """
    audit_metadata = {
        "admin_username": admin_username,
        "admin_reason": reason,
        "adjustment_type": "manual_admin",
        "source": "admin_board",
        "timestamp": datetime.now(UTC).isoformat(),
        **(metadata or {})
    }

    logger.info(
        "Credit action logged",
        extra={
            "action": action_type,
            "admin": admin_username,
            "user_id": user_id,
            "amount": str(amount)
        }
    )

    return audit_metadata


def format_audit_trail(notes: str, admin_username: str) -> str:
    """
    Format notes with audit trail prefix.

    Usage:
        notes = format_audit_trail(user_notes, admin_username)
    """
    timestamp = datetime.now(UTC).isoformat()
    return f"[ADMIN: {admin_username} @ {timestamp}] {notes}"
