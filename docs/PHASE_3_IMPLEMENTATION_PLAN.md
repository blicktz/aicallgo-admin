# Phase 3 Implementation Plan: Priority Features (Data Manipulation)

**Project**: AICallGO Admin Board
**Phase**: 3 of 6
**Duration**: 5-6 days
**Status**: Ready for Implementation

---

## Overview

Phase 3 implements the critical admin capabilities for managing user entitlements and credits with full audit trails and transaction safety. This phase builds on Phase 1/2's read-only foundation to enable data manipulation with proper validation, confirmation dialogs, and comprehensive audit logging.

**Core Deliverables**:
- ✅ Feature entitlement management (grant/revoke access)
- ✅ Credit adjustment with audit trail
- ✅ Transaction safety and rollback
- ✅ Validation and confirmation dialogs

---

## Prerequisites

Before starting Phase 3, ensure:
- ✅ Phase 1 completed (authentication, database connection, project structure)
- ✅ Phase 2 completed (read-only pages, services, components)
- ✅ Access to staging database with port-forward
- ✅ Understanding of web-backend models:
  - `UserFeatureOverride` (app/models/user_feature_override.py)
  - `CreditTransaction` (app/models/credit_models.py)
  - `CreditBalance` (app/models/credit_models.py)
  - `Feature` (app/models/feature.py)

---

## Task Breakdown

### Task 21: Implement Entitlement Service

**File**: `services/entitlement_service.py`

**Purpose**: Provide data access layer for feature entitlement operations, wrapping web-backend's CRUD operations with admin-specific logic.

**Functions to Implement**:

```python
def get_all_features(session: Session) -> List[Feature]:
    """
    Get all available features from the system.
    Uses: crud_feature_sync.get_multi()
    """

def get_user_entitlements(session: Session, user_id: str) -> Dict[str, Any]:
    """
    Get comprehensive entitlement data for a user.

    Returns:
        {
            "plan": Plan object,
            "plan_features": [Feature objects from plan],
            "overrides": [UserFeatureOverride objects],
            "computed_access": {
                "feature_key": bool (final access)
            }
        }

    Logic:
    1. Get user's active subscription and plan
    2. Get plan's default features via plan_features junction
    3. Get user's active overrides
    4. Compute final access (override > plan default)
    """

def create_feature_override(
    session: Session,
    user_id: str,
    feature_key: str,
    has_access: bool,
    expires_at: Optional[datetime],
    notes: str,
    admin_username: str
) -> UserFeatureOverride:
    """
    Create or update a feature override for a user.

    Steps:
    1. Validate user exists and is active
    2. Get feature by feature_key
    3. Check if override exists (get_by_user_and_feature)
    4. If exists: update; if not: create
    5. Log audit trail
    6. Return created/updated override

    Uses:
    - crud_feature_sync.get_by_feature_key()
    - crud_user_feature_override_sync.get_by_user_and_feature()
    - crud_user_feature_override_sync.create() or update()
    """

def delete_feature_override(
    session: Session,
    user_id: str,
    feature_key: str,
    admin_username: str,
    reason: str
) -> bool:
    """
    Remove a feature override (revert to plan default).

    Steps:
    1. Get feature by feature_key
    2. Delete override
    3. Log audit trail
    4. Return success/failure

    Uses:
    - crud_user_feature_override_sync.delete_by_user_and_feature()
    """

def get_override_history(session: Session, user_id: str) -> List[Dict]:
    """
    Get audit history of entitlement changes for a user.

    For Phase 3: Return overrides with created_at/updated_at
    For Phase 4+: Query dedicated audit log table
    """
```

**Key Integration Points**:
- Import from web-backend: `from app.crud.crud_user_feature_override_sync import user_feature_override_sync`
- Import from web-backend: `from app.crud.crud_feature_sync import feature_sync`
- Import from web-backend: `from app.models.feature import Feature`
- Import from web-backend: `from app.models.user_feature_override import UserFeatureOverride`

**Error Handling**:
- Raise `ValueError` for validation errors (caught in UI layer)
- Log all errors with logger
- Return detailed error messages for user feedback

---

### Task 22: Build Entitlements Page

**File**: `pages/6_⚡_Entitlements.py`

**Layout**: 30% user search + 70% entitlement management

**Section 1: User Search (Left Column)**
```python
# Reuse pattern from pages/2_👥_Users.py
- Search input (email/name)
- User list (email, name, plan)
- Click to select → update session_state.selected_user_id
```

**Section 2: Entitlement Management (Right Column)**

**Panel A: Current State Display**
```python
# Show for selected user:
st.markdown("#### Current Plan & Features")
- Plan name and status
- Plan features (from plan_features):
  - Feature name
  - Description
  - Access: "✅ Included" badge

st.markdown("#### Active Overrides")
- Table of UserFeatureOverride records:
  - Feature
  - Access (Grant/Deny)
  - Expires At
  - Notes
  - Created At
  - Action: [Delete Override] button

st.markdown("#### Computed Access")
- Final computed access for each feature:
  - Feature name
  - Plan Default (✅/❌)
  - Override (🔧/blank)
  - Final Access (✅/❌)
```

**Panel B: Create/Update Override Form**
```python
with st.form("override_form"):
    st.markdown("#### Grant/Revoke Feature Access")

    # Feature selection
    feature_options = get_all_features(session)
    selected_feature = st.selectbox(
        "Feature",
        options=feature_options,
        format_func=lambda f: f"{f.feature_key} - {f.description}"
    )

    # Access toggle
    has_access = st.radio(
        "Access",
        options=["Grant", "Deny"],
        horizontal=True
    )

    # Optional expiration
    set_expiration = st.checkbox("Set expiration date")
    expires_at = None
    if set_expiration:
        expires_at = st.date_input(
            "Expires At",
            min_value=datetime.now().date() + timedelta(days=1)
        )

    # Required notes
    notes = st.text_area(
        "Notes (required, min 10 characters)",
        placeholder="Explain why this override is needed...",
        max_chars=500
    )

    # Preview
    if notes and len(notes) >= 10:
        with st.expander("📋 Preview Changes"):
            st.markdown(f"**User**: {selected_user.email}")
            st.markdown(f"**Feature**: {selected_feature.feature_key}")
            st.markdown(f"**Action**: {has_access}")
            st.markdown(f"**Plan Default**: {plan_default_access}")
            st.markdown(f"**New Override**: {has_access}")
            st.markdown(f"**Final Access**: {final_access}")

    submitted = st.form_submit_button("Save Override")

    if submitted:
        # Validation
        if len(notes) < 10:
            st.error("Notes must be at least 10 characters")
            st.stop()

        # Confirmation dialog
        if st.session_state.get("confirm_override") != True:
            st.warning("⚠️ Please confirm this change")
            if st.button("✅ Confirm Override"):
                st.session_state.confirm_override = True
                st.rerun()
            st.stop()

        # Execute
        try:
            with session.begin():
                override = create_feature_override(
                    session=session,
                    user_id=selected_user.id,
                    feature_key=selected_feature.feature_key,
                    has_access=(has_access == "Grant"),
                    expires_at=expires_at,
                    notes=notes,
                    admin_username=st.secrets["ADMIN_USERNAME"]
                )
            st.success(f"✅ Override created: {selected_feature.feature_key}")
            st.session_state.confirm_override = False
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to create override: {str(e)}")
```

**Styling**:
- Match existing pages (Users, Businesses)
- Use status badges from `utils/formatters.py`
- Use card layout from `components/cards.py`
- Green for grant, red for deny, yellow for expired

---

### Task 23: Implement Credit Service

**File**: `services/credit_service.py`

**Purpose**: Provide data access layer for credit operations with validation and atomic transactions.

**Functions to Implement**:

```python
def get_credit_balance(session: Session, user_id: str) -> Optional[CreditBalance]:
    """
    Get user's current credit balance with breakdown.
    Uses: crud_credit_sync.credit_balance_sync.get_by_user_id()
    """

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

def validate_adjustment(amount: Decimal, reason: str) -> tuple[bool, str]:
    """
    Validate credit adjustment parameters.

    Rules:
    - Amount must be non-zero
    - Reason must be >= 10 characters

    Returns:
        (is_valid, error_message)
    """

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
```

**Key Integration Points**:
- Import from web-backend: `from app.crud.crud_credit_sync import credit_transaction_sync, credit_balance_sync`
- Import from web-backend: `from app.models.credit_models import CreditTransaction, CreditBalance, CreditTransactionType`
- Use `Decimal` for all monetary amounts
- Ensure atomic operations with session.begin()

---

### Task 24: Build Credits Page

**File**: `pages/7_💰_Credits.py`

**Layout**: 30% user search + 70% credit management

**Section 1: User Search (Left Column)**
```python
# Same as entitlements page
```

**Section 2: Credit Management (Right Column)**

**Panel A: Balance Display**
```python
st.markdown("#### Credit Balance")

balance = get_credit_balance(session, user_id)

# Main balance card
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    balance_color = "red" if balance.total_balance < 0 else "green"
    st.metric(
        "Total Balance",
        format_currency(balance.total_balance),
        delta=None,
        delta_color=balance_color
    )
with col2:
    st.metric("Last Updated", format_datetime(balance.last_updated))

# Breakdown
st.markdown("**Balance Breakdown**")
breakdown_df = pd.DataFrame([
    {"Source": "Trial Credits", "Amount": format_currency(balance.trial_credits)},
    {"Source": "Subscription Credits", "Amount": format_currency(balance.subscription_credits)},
    {"Source": "Credit Pack Credits", "Amount": format_currency(balance.credit_pack_credits)},
    {"Source": "Adjustments", "Amount": format_currency(balance.adjustment_credits)},
])
st.dataframe(breakdown_df, hide_index=True, use_container_width=True)

# Warning for negative balance
if balance.total_balance < 0:
    st.error(f"⚠️ User has negative balance (overrun): {format_currency(balance.total_balance)}")
```

**Panel B: Transaction History**
```python
st.markdown("#### Transaction History")

# Filters
col1, col2 = st.columns([3, 1])
with col1:
    type_filter = st.selectbox(
        "Transaction Type",
        ["all", "grant_trial", "grant_subscription", "grant_credit_pack",
         "deduct_usage", "adjustment", "refund"]
    )
with col2:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# Load transactions
transactions = get_credit_transactions(
    session,
    user_id,
    limit=50,
    offset=0,
    transaction_type=type_filter if type_filter != "all" else None
)

# Display table
tx_df = pd.DataFrame([
    {
        "Date": format_datetime(tx.created_at),
        "Type": tx.transaction_type,
        "Amount": format_currency(tx.amount, signed=True),
        "Balance After": format_currency(tx.balance_after),
        "Description": tx.description[:50] + "..." if len(tx.description) > 50 else tx.description
    }
    for tx in transactions
])

st.dataframe(
    tx_df,
    hide_index=True,
    use_container_width=True,
    height=400
)

st.caption(f"Showing {len(transactions)} transactions")
```

**Panel C: Adjustment Form**
```python
st.markdown("#### Adjust Credits")

with st.form("credit_adjustment_form"):
    # Amount input
    col1, col2 = st.columns([2, 1])
    with col1:
        amount = st.number_input(
            "Adjustment Amount ($)",
            value=0.0,
            step=0.01,
            format="%.2f",
            help="Positive to add credits, negative to deduct"
        )
    with col2:
        amount_decimal = Decimal(str(amount))

    # Transaction type
    tx_type = st.selectbox(
        "Transaction Type",
        options=[
            CreditTransactionType.ADJUSTMENT,
            CreditTransactionType.REFUND
        ],
        format_func=lambda x: x.value.replace("_", " ").title()
    )

    # Required reason
    reason = st.text_area(
        "Reason (required, min 10 characters)",
        placeholder="Explain why this adjustment is needed...",
        max_chars=500
    )

    # Preview
    if amount != 0 and reason and len(reason) >= 10:
        with st.expander("📋 Preview Adjustment"):
            preview = calculate_adjustment_preview(session, user_id, amount_decimal)

            st.markdown(f"**Current Balance**: {format_currency(preview['current_balance'])}")
            st.markdown(f"**Adjustment**: {format_currency(preview['adjustment_amount'], signed=True)}")
            st.markdown(f"**New Balance**: {format_currency(preview['new_balance'])}")

            # Warnings
            if abs(amount) > 100:
                st.warning(f"⚠️ Large adjustment: ${abs(amount):.2f}")
            if preview['new_balance'] < 0:
                st.error("⚠️ This will result in negative balance (debt)")

    submitted = st.form_submit_button("Apply Adjustment")

    if submitted:
        # Validation
        if amount == 0:
            st.error("Amount must be non-zero")
            st.stop()

        if len(reason) < 10:
            st.error("Reason must be at least 10 characters")
            st.stop()

        # Confirmation for large amounts
        if abs(amount) > 100:
            if st.session_state.get("confirm_large_adjustment") != True:
                st.warning(f"⚠️ Confirm large adjustment: ${abs(amount):.2f}")
                if st.button("✅ Confirm Large Adjustment"):
                    st.session_state.confirm_large_adjustment = True
                    st.rerun()
                st.stop()

        # Confirmation for negative balance
        preview = calculate_adjustment_preview(session, user_id, amount_decimal)
        if preview['new_balance'] < 0:
            if st.session_state.get("confirm_negative") != True:
                st.error(f"⚠️ This will create negative balance: {format_currency(preview['new_balance'])}")
                if st.button("✅ Confirm Negative Balance"):
                    st.session_state.confirm_negative = True
                    st.rerun()
                st.stop()

        # Execute adjustment
        try:
            with session.begin():
                transaction = adjust_credits(
                    session=session,
                    user_id=user_id,
                    amount=amount_decimal,
                    reason=reason,
                    admin_username=st.secrets["ADMIN_USERNAME"],
                    transaction_type=tx_type
                )

            st.success(f"✅ Credit adjustment successful: {format_currency(amount_decimal, signed=True)}")
            st.session_state.confirm_large_adjustment = False
            st.session_state.confirm_negative = False
            st.cache_data.clear()
            st.rerun()

        except Exception as e:
            st.error(f"❌ Failed to adjust credits: {str(e)}")
```

---

### Task 25: Implement Audit Service

**File**: `services/audit_service.py`

**Purpose**: Centralized audit logging for all admin actions.

**Implementation Strategy**:

For Phase 3, we'll use the existing transaction metadata fields instead of creating a new audit table (defer dedicated audit table to Phase 4+).

```python
import json
from datetime import datetime, UTC
from typing import Dict, Any, Optional
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
```

**Integration**:
- Call `format_audit_trail()` in entitlement_service before saving notes
- Call `log_credit_action()` in credit_service to generate metadata
- Both services pass metadata to CRUD operations

---

### Task 26: Add Audit Trail Logging to All Mutations

**Entitlement Operations**:

Update `services/entitlement_service.py`:

```python
from services.audit_service import format_audit_trail, log_entitlement_action

def create_feature_override(...):
    # Format notes with audit trail
    structured_notes = format_audit_trail(notes, admin_username)

    # Create/update override with structured notes
    override = user_feature_override_sync.create(
        db=session,
        obj_in={
            "user_id": user_id,
            "feature_id": feature.id,
            "has_access": has_access,
            "expires_at": expires_at,
            "notes": structured_notes  # Contains audit trail
        }
    )

    # Log action
    log_entitlement_action(
        session=session,
        action_type="grant" if has_access else "revoke",
        admin_username=admin_username,
        user_id=user_id,
        feature_key=feature_key,
        has_access=has_access,
        notes=notes
    )

    return override

def delete_feature_override(...):
    # Get existing override for audit
    feature = feature_sync.get_by_feature_key(session, feature_key)
    override = user_feature_override_sync.get_by_user_and_feature(
        session, user_id=user_id, feature_id=feature.id
    )

    # Delete
    user_feature_override_sync.delete_by_user_and_feature(
        session, user_id=user_id, feature_id=feature.id
    )

    # Log deletion
    log_entitlement_action(
        session=session,
        action_type="delete",
        admin_username=admin_username,
        user_id=user_id,
        feature_key=feature_key,
        has_access=override.has_access if override else None,
        notes=reason
    )
```

**Credit Operations**:

Update `services/credit_service.py`:

```python
from services.audit_service import log_credit_action

def adjust_credits(...):
    # Generate audit metadata
    metadata = log_credit_action(
        session=session,
        action_type=transaction_type.value,
        admin_username=admin_username,
        user_id=user_id,
        amount=amount,
        reason=reason
    )

    # Create transaction with metadata
    transaction = credit_transaction_sync.create_transaction(
        db=session,
        user_id=user_id,
        transaction_type=transaction_type,
        amount=amount,
        description=f"Admin adjustment by {admin_username}: {reason}",
        metadata=metadata  # Contains full audit trail
    )

    return transaction
```

---

### Task 27: Implement Transaction Safety (Rollback on Error)

**Pattern for All Mutations**:

```python
# In Streamlit pages (pages/6_⚡_Entitlements.py, pages/7_💰_Credits.py)

try:
    with session.begin():
        # All database operations in this block
        result = service_function(session, ...)

        # If any operation fails, entire block rolls back automatically

    # Success path (only reached if transaction committed)
    st.success("✅ Operation completed successfully")
    st.cache_data.clear()
    st.rerun()

except ValueError as e:
    # Validation errors (user-friendly)
    st.error(f"❌ Validation error: {str(e)}")

except IntegrityError as e:
    # Database constraint violations
    st.error("❌ Database constraint violation. This operation conflicts with existing data.")
    logger.error(f"IntegrityError: {e}")

except Exception as e:
    # Unexpected errors
    st.error(f"❌ Operation failed: {str(e)}")
    logger.exception("Unexpected error in mutation")
```

**Testing Rollback Scenarios**:

1. **Invalid user_id**: Should roll back without creating partial records
2. **Duplicate constraint**: Should roll back without partial updates
3. **Network error mid-transaction**: Should roll back automatically
4. **Validation error after DB write**: Should roll back everything

**Key Points**:
- Use `session.begin()` context manager for automatic rollback
- Never commit manually - let context manager handle it
- Catch specific exceptions for better error messages
- Log all errors for debugging
- Clear cache only on success

---

### Task 28: Add Comprehensive Validation to All Forms

**Entitlement Form Validation**:

```python
# Client-side validation (Streamlit widgets)
- User selection: required (disabled submit if no user selected)
- Feature selection: required
- Notes: required, min_length=10, max_length=500
- Expiration date: must be future date (if provided)

# Server-side validation (service layer)
def create_feature_override(...):
    # Validate user exists
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    if not user.is_active:
        raise ValueError(f"Cannot modify inactive user {user.email}")

    # Validate feature exists
    feature = feature_sync.get_by_feature_key(session, feature_key)
    if not feature:
        raise ValueError(f"Feature '{feature_key}' not found")

    # Validate notes
    if not notes or len(notes.strip()) < 10:
        raise ValueError("Notes must be at least 10 characters")

    # Validate expiration date
    if expires_at and expires_at <= datetime.now():
        raise ValueError("Expiration date must be in the future")

    # Proceed with operation...
```

**Credit Form Validation**:

```python
# Client-side validation
- User selection: required
- Amount: required, non-zero, numeric
- Reason: required, min_length=10, max_length=500
- Large amount warning: > $100
- Negative balance warning: new_balance < 0

# Server-side validation
def adjust_credits(...):
    # Validate amount
    if amount == 0:
        raise ValueError("Adjustment amount must be non-zero")

    if abs(amount) > 10000:
        raise ValueError("Adjustment amount exceeds maximum allowed ($10,000)")

    # Validate reason
    if not reason or len(reason.strip()) < 10:
        raise ValueError("Reason must be at least 10 characters")

    # Validate user has credit balance record
    balance = credit_balance_sync.get_by_user_id(session, user_id)
    if not balance:
        # This should never happen but validate anyway
        raise ValueError(f"User {user_id} has no credit balance record")

    # Proceed with operation...
```

**Confirmation Dialogs**:

All destructive or significant operations require explicit confirmation:

1. **Entitlement Override**: Always confirm before applying
2. **Large Credit Adjustment**: Confirm if |amount| > $100
3. **Negative Balance**: Confirm if new_balance < 0
4. **Delete Override**: Confirm before removing override

**Implementation Pattern**:
```python
# Use session_state to track confirmation
if not st.session_state.get("confirm_action"):
    st.warning("⚠️ Please confirm this action")
    if st.button("✅ Confirm"):
        st.session_state.confirm_action = True
        st.rerun()
    st.stop()

# Clear confirmation after success
st.session_state.confirm_action = False
```

---

## File Structure

```
services/admin-board/
├── pages/
│   ├── 6_⚡_Entitlements.py         # NEW: Feature entitlement management
│   └── 7_💰_Credits.py              # NEW: Credit adjustment with audit
│
├── services/
│   ├── entitlement_service.py       # NEW: Entitlement operations
│   ├── credit_service.py            # NEW: Credit operations
│   ├── audit_service.py             # NEW: Audit logging
│   ├── user_service.py              # EXISTING (Phase 2)
│   ├── business_service.py          # EXISTING (Phase 2)
│   ├── call_log_service.py          # EXISTING (Phase 2)
│   └── billing_service.py           # EXISTING (Phase 2)
│
├── components/
│   ├── forms.py                     # NEW: Reusable form components
│   ├── cards.py                     # EXISTING (Phase 2)
│   ├── tables.py                    # EXISTING (Phase 2)
│   └── charts.py                    # EXISTING (Phase 2)
│
└── utils/
    └── formatters.py                # EXISTING (Phase 2)
```

---

## Environment Variables

Add to `.streamlit/secrets.toml`:

```toml
[secrets]
ADMIN_USERNAME = "admin"  # Used in audit trails
```

Ensure `config/settings.py` loads this:
```python
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
```

---

## Testing Strategy

### Unit Testing Checklist

**Entitlement Service Tests**:
- [ ] `test_get_all_features()` - returns all features
- [ ] `test_get_user_entitlements()` - returns plan + overrides + computed
- [ ] `test_create_feature_override_new()` - creates new override
- [ ] `test_create_feature_override_update()` - updates existing override
- [ ] `test_delete_feature_override()` - removes override
- [ ] `test_create_override_invalid_user()` - raises ValueError
- [ ] `test_create_override_invalid_feature()` - raises ValueError
- [ ] `test_create_override_inactive_user()` - raises ValueError

**Credit Service Tests**:
- [ ] `test_get_credit_balance()` - returns balance with breakdown
- [ ] `test_get_credit_transactions()` - returns transaction history
- [ ] `test_adjust_credits_positive()` - adds credits
- [ ] `test_adjust_credits_negative()` - deducts credits
- [ ] `test_adjust_credits_zero()` - raises ValueError
- [ ] `test_adjust_credits_no_reason()` - raises ValueError
- [ ] `test_calculate_adjustment_preview()` - returns correct preview

**Audit Service Tests**:
- [ ] `test_format_audit_trail()` - formats notes correctly
- [ ] `test_log_credit_action()` - returns correct metadata
- [ ] `test_log_entitlement_action()` - logs correctly

### Integration Testing Checklist

**Entitlement Operations**:
- [ ] Grant feature access to user
- [ ] Revoke feature access from user
- [ ] Update existing override
- [ ] Delete override (revert to plan default)
- [ ] View override history
- [ ] Verify audit trail in notes field

**Credit Operations**:
- [ ] Add credits to user
- [ ] Deduct credits from user
- [ ] View transaction history
- [ ] Filter transactions by type
- [ ] Verify balance breakdown updates
- [ ] Verify audit metadata in transaction

**Transaction Safety**:
- [ ] Test rollback on validation error
- [ ] Test rollback on database constraint violation
- [ ] Test rollback on network error
- [ ] Verify no partial updates after rollback

**Validation**:
- [ ] Test required field validation
- [ ] Test min/max length validation
- [ ] Test numeric validation
- [ ] Test date validation (future dates only)
- [ ] Test confirmation dialogs for large amounts

### Manual Testing Checklist

**UI/UX**:
- [ ] Search and select user
- [ ] View current entitlements
- [ ] Create feature override
- [ ] Delete feature override
- [ ] View credit balance
- [ ] View transaction history
- [ ] Adjust credits (positive)
- [ ] Adjust credits (negative)
- [ ] Test large amount warning
- [ ] Test negative balance warning
- [ ] Test confirmation dialogs
- [ ] Test error messages
- [ ] Verify audit trails

**Cross-Browser**:
- [ ] Chrome/Edge (primary)
- [ ] Firefox
- [ ] Safari

**Responsiveness**:
- [ ] 1920x1080 (primary)
- [ ] 1440x900
- [ ] 1280x720 (minimum)

---

## Success Criteria

### Functional Requirements

- ✅ Admins can grant/revoke feature access to any user
- ✅ Admins can view user's plan-based features and overrides
- ✅ Admins can set optional expiration dates on overrides
- ✅ Admins can delete overrides to revert to plan default
- ✅ Admins can view computed access (final result)
- ✅ Admins can adjust user credits (add/deduct)
- ✅ Admins can view credit balance breakdown
- ✅ Admins can view full transaction history
- ✅ All mutations are atomic (commit or rollback together)
- ✅ All mutations include audit trail (admin username, timestamp, reason)

### Non-Functional Requirements

- ✅ Transaction safety: Rollback on any error
- ✅ Validation: Client-side and server-side
- ✅ Confirmation: Required for all mutations
- ✅ Warnings: Large amounts and negative balances
- ✅ Error handling: User-friendly error messages
- ✅ Logging: All operations logged for debugging
- ✅ Performance: Operations complete in < 2 seconds
- ✅ UI consistency: Matches existing pages' design

### Quality Metrics

- **Test Coverage**: > 80% for service layer
- **Error Rate**: < 1% of operations fail
- **Rollback Success**: 100% on error
- **Audit Trail**: 100% coverage of mutations
- **User Satisfaction**: Operations are intuitive and safe

---

## Known Limitations & Future Improvements

### Phase 3 Limitations

1. **No Dedicated Audit Table**: Audit data stored in transaction metadata/notes fields
2. **No Bulk Operations**: One user at a time
3. **No Expiration Automation**: Manual expiration date management
4. **No Email Notifications**: Users not notified of changes
5. **No Approval Workflow**: Direct execution (no review/approve)

### Phase 4+ Enhancements

1. Create dedicated `admin_audit_log` table
2. Add bulk operations (CSV import/export)
3. Add automatic expiration cleanup job
4. Add email notifications to users
5. Add approval workflow for large adjustments
6. Add undo/rollback capability
7. Add detailed change history viewer
8. Add role-based permissions (admin vs. viewer)

---

## Dependencies

### Web-Backend Models
- `User` (app/models/user.py)
- `Feature` (app/models/feature.py)
- `UserFeatureOverride` (app/models/user_feature_override.py)
- `CreditBalance` (app/models/credit_models.py)
- `CreditTransaction` (app/models/credit_models.py)
- `Plan` (app/models/plan.py)
- `PlanFeature` (app/models/plan_feature.py)

### Web-Backend CRUD
- `crud_user_feature_override_sync` (app/crud/crud_user_feature_override_sync.py)
- `crud_feature_sync` (app/crud/crud_feature_sync.py)
- `crud_credit_sync` (app/crud/crud_credit_sync.py)
- `crud_plan_sync` (app/crud/crud_plan_sync.py)

### Python Packages
```txt
streamlit>=1.30.0
sqlalchemy>=2.0.0
pandas>=2.0.0
plotly>=5.0.0
bcrypt>=4.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

---

## Deployment Notes

### Database Access
- Use port-forward to staging database: `kubectl port-forward svc/postgres 5432:5432 -n aicallgo-staging`
- Connection string in `.streamlit/secrets.toml`
- Read-write access required for Phase 3 (unlike Phase 2 which was read-only)

### Security Considerations
- Admin username tracked in all audit trails
- No password changes through admin board (use separate system)
- Session timeout: 8 hours (Streamlit default)
- All operations logged for compliance

### Performance
- Database queries should complete in < 500ms
- Page load time < 2 seconds
- Form submissions < 2 seconds
- Use caching for read operations (`@st.cache_data(ttl=60)`)
- Clear cache after mutations

---

## Implementation Timeline

**Day 1**: Tasks 21-22 (Entitlement Service + Page)
- Morning: Implement entitlement_service.py
- Afternoon: Build pages/6_⚡_Entitlements.py
- End of day: Test grant/revoke operations

**Day 2**: Task 22 continued (Entitlement UI Polish)
- Morning: Add override history display
- Afternoon: Add delete override functionality
- End of day: Test all entitlement workflows

**Day 3**: Tasks 23-24 (Credit Service + Page)
- Morning: Implement credit_service.py
- Afternoon: Build pages/7_💰_Credits.py balance display
- End of day: Test balance retrieval and history

**Day 4**: Task 24 continued (Credit UI Complete)
- Morning: Add adjustment form with preview
- Afternoon: Add confirmations and warnings
- End of day: Test credit adjustments

**Day 5**: Tasks 25-26 (Audit Service + Integration)
- Morning: Implement audit_service.py
- Afternoon: Integrate audit logging into services
- End of day: Test audit trail creation

**Day 6**: Tasks 27-28 (Transaction Safety + Validation)
- Morning: Add transaction safety to all operations
- Afternoon: Add comprehensive validation
- End of day: Full integration testing

---

## Rollout Plan

1. **Development**: Test on local with port-forward to staging DB
2. **Staging Deployment**: Deploy to Kubernetes staging namespace
3. **Admin Testing**: Internal team validates all workflows
4. **Production Deployment**: Deploy to production namespace
5. **Documentation**: Update admin documentation with new features
6. **Training**: Brief team on new capabilities

---

## Support & Troubleshooting

### Common Issues

**Issue**: "User not found" error
- **Cause**: User ID mismatch or inactive user
- **Solution**: Verify user is active and ID is correct

**Issue**: "Feature not found" error
- **Cause**: Feature key doesn't exist in database
- **Solution**: Check app/core/startup.py for valid feature keys

**Issue**: Transaction rollback without clear error
- **Cause**: Database constraint violation
- **Solution**: Check logs for IntegrityError details

**Issue**: Audit trail not showing
- **Cause**: ADMIN_USERNAME not set in secrets
- **Solution**: Add to .streamlit/secrets.toml

### Debug Tips

1. Enable debug logging in `config/settings.py`
2. Check Streamlit console for errors
3. Check database logs for constraint violations
4. Use `session.flush()` before `session.commit()` to catch errors early
5. Test with small amounts first

---

## Conclusion

Phase 3 delivers the core admin functionality needed for day-to-day user management. By implementing entitlement overrides and credit adjustments with full audit trails and transaction safety, the admin board becomes a production-ready tool for customer support and operations teams.

**Key Achievements**:
- ✅ Safe data manipulation with rollback protection
- ✅ Complete audit trail for compliance
- ✅ User-friendly validation and confirmations
- ✅ Consistent UI/UX with existing pages
- ✅ Production-ready error handling

**Next Phase**: Phase 4 will add promotion tracking, appointment viewing, system monitoring, CSV exports, and enhanced refresh capabilities.
