"""
Credits - Credit balance and adjustment management
"""
import streamlit as st
import pandas as pd
from decimal import Decimal
from config.auth import require_auth
from database.connection import get_session
from services.user_service import get_users, get_user_by_id
from services.credit_service import (
    get_credit_balance,
    get_credit_transactions,
    adjust_credits,
    calculate_adjustment_preview
)
from utils.formatters import format_datetime, format_currency
import sys
from pathlib import Path
import logging
import os

# Add web-backend to path for CreditTransactionType
backend_path = Path(__file__).parent.parent.parent / "web-backend"
sys.path.insert(0, str(backend_path))

from app.models.credit_models import CreditTransactionType

logger = logging.getLogger(__name__)


def format_minutes(amount: Decimal | float | int, signed: bool = False) -> str:
    """
    Format amount as minutes with 1 decimal place.

    Args:
        amount: Amount to format
        signed: If True, show + or - sign

    Returns:
        Formatted string like "150.5 min" or "+10.5 min"
    """
    if amount is None:
        return "0.0 min"

    value = float(amount)
    if signed:
        if value >= 0:
            return f"+{value:.1f} min"
        else:
            return f"{value:.1f} min"
    else:
        return f"{value:.1f} min"


# Auth check
if not require_auth():
    st.stop()

st.title("💰 Credits")
st.markdown("Manage user credit balances and adjustments")

# Initialize session state
if "selected_user_id" not in st.session_state:
    st.session_state.selected_user_id = None
if "confirm_large_adjustment" not in st.session_state:
    st.session_state.confirm_large_adjustment = False
if "confirm_negative" not in st.session_state:
    st.session_state.confirm_negative = False

# Main layout: user search (30%) + credit management (70%)
search_col, manage_col = st.columns([3, 7])

# Section 1: User Search (Left Column)
with search_col:
    st.markdown("### User Search")

    search_query = st.text_input(
        "🔍 Search by email or name",
        placeholder="Enter email or name...",
        key="user_search"
    )

    # Load users
    @st.cache_data(ttl=60)
    def load_users(search, status, per_page):
        """Load users with filters"""
        with get_session() as session:
            return get_users(
                session,
                limit=per_page,
                offset=0,
                search_query=search if search else None,
                status_filter=status
            )

    try:
        users = load_users(search_query, "active", 50)

        if not users:
            st.info("No users found")
        else:
            # Convert to DataFrame
            users_df = pd.DataFrame([
                {
                    "Email": u.email,
                    "Name": u.full_name or "N/A",
                    "ID": str(u.id)
                }
                for u in users
            ])

            st.markdown("*Click on a row to select user*")

            # Display DataFrame with row selection
            event = st.dataframe(
                users_df.drop(columns=["ID"]),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                height=600
            )

            # Update selected user ID
            if event and "selection" in event and "rows" in event["selection"]:
                if len(event["selection"]["rows"]) > 0:
                    selected_idx = event["selection"]["rows"][0]
                    selected_user_id = users_df.iloc[selected_idx]["ID"]
                    st.session_state.selected_user_id = selected_user_id

            st.caption(f"Showing {len(users)} users")

    except Exception as e:
        st.error(f"Failed to load users: {str(e)}")
        logger.exception("Failed to load users")

# Section 2: Credit Management (Right Column)
with manage_col:
    st.markdown("### Credit Management")

    if not st.session_state.selected_user_id:
        st.info("👈 Select a user to manage credits")
    else:
        # Load user details
        @st.cache_data(ttl=30)
        def load_user_credit_data(user_id):
            """Load user credit data"""
            with get_session() as session:
                user = get_user_by_id(session, user_id)
                if not user:
                    return None

                balance = get_credit_balance(session, user_id)
                transactions = get_credit_transactions(session, user_id, limit=50)

                return {
                    "user": user,
                    "balance": balance,
                    "transactions": transactions
                }

        try:
            data = load_user_credit_data(st.session_state.selected_user_id)

            if not data or not data["user"]:
                st.warning("User not found")
            else:
                user = data["user"]
                balance = data["balance"]
                transactions = data["transactions"]

                # User header
                st.markdown(f"**User:** {user.email}")
                st.markdown(f"**Name:** {user.full_name or 'N/A'}")
                st.divider()

                # Panel A: Balance Display
                st.markdown("#### Credit Balance")

                if balance:
                    # Main balance card
                    balance_color = "normal" if balance.total_balance >= 0 else "inverse"
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.metric(
                            "Total Balance (min)",
                            format_minutes(balance.total_balance),
                            delta=None
                        )
                    with col2:
                        st.metric("Last Updated", format_datetime(balance.last_updated))

                    # Warning for negative balance
                    if balance.total_balance < 0:
                        st.error(f"⚠️ User has negative balance (overrun): {format_minutes(balance.total_balance)}")

                    # Breakdown
                    st.markdown("**Balance Breakdown**")
                    breakdown_df = pd.DataFrame([
                        {"Source": "Trial Credits", "Amount (min)": format_minutes(balance.trial_credits)},
                        {"Source": "Subscription Credits", "Amount (min)": format_minutes(balance.subscription_credits)},
                        {"Source": "Credit Pack Credits", "Amount (min)": format_minutes(balance.credit_pack_credits)},
                        {"Source": "Adjustments", "Amount (min)": format_minutes(balance.adjustment_credits)},
                    ])
                    st.dataframe(breakdown_df, hide_index=True, use_container_width=True)
                else:
                    st.info("No credit balance record found")

                st.divider()

                # Panel B: Transaction History
                st.markdown("#### Transaction History")

                # Filters
                col1, col2 = st.columns([3, 1])
                with col1:
                    type_filter = st.selectbox(
                        "Transaction Type",
                        ["all"] + [t.value for t in CreditTransactionType]
                    )
                with col2:
                    if st.button("🔄 Refresh"):
                        st.cache_data.clear()
                        st.rerun()

                # Display transactions
                if transactions:
                    tx_df = pd.DataFrame([
                        {
                            "Date": format_datetime(tx.created_at),
                            "Type": tx.transaction_type.replace("_", " ").title(),
                            "Amount (min)": format_minutes(tx.amount, signed=True),
                            "Balance After (min)": format_minutes(tx.balance_after),
                            "Description": tx.description[:50] + "..." if len(tx.description) > 50 else tx.description
                        }
                        for tx in transactions
                        if type_filter == "all" or tx.transaction_type == type_filter
                    ])

                    st.dataframe(
                        tx_df,
                        hide_index=True,
                        use_container_width=True,
                        height=300
                    )

                    st.caption(f"Showing {len(tx_df)} transactions")
                else:
                    st.info("No transaction history")

                st.divider()

                # Panel C: Adjustment Form
                st.markdown("#### Adjust Credits")

                with st.form("credit_adjustment_form"):
                    # Amount input
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        amount = st.number_input(
                            "Adjustment Amount (min)",
                            value=0.0,
                            step=0.1,
                            format="%.1f",
                            help="Positive to add credits, negative to deduct"
                        )
                    with col2:
                        st.markdown("")
                        st.markdown("")
                        if amount > 0:
                            st.success(f"➕ Add {amount:.1f} min")
                        elif amount < 0:
                            st.error(f"➖ Deduct {abs(amount):.1f} min")

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

                    submitted = st.form_submit_button("Apply Adjustment", type="primary")

                    if submitted:
                        # Validation
                        if amount == 0:
                            st.error("Amount must be non-zero")
                            st.stop()

                        if len(reason) < 10:
                            st.error("Reason must be at least 10 characters")
                            st.stop()

                        # Confirmation for large amounts
                        if abs(amount) > 1000 and not st.session_state.confirm_large_adjustment:
                            st.warning(f"⚠️ Confirm large adjustment: {abs(amount):.1f} min")
                            if st.button("✅ Confirm Large Adjustment"):
                                st.session_state.confirm_large_adjustment = True
                                st.rerun()
                            st.stop()

                        # Confirmation for negative balance
                        try:
                            with get_session() as session:
                                preview = calculate_adjustment_preview(
                                    session, user.id, amount_decimal
                                )
                                if preview['new_balance'] < 0 and not st.session_state.confirm_negative:
                                    st.error(f"⚠️ This will create negative balance: {format_minutes(preview['new_balance'])}")
                                    if st.button("✅ Confirm Negative Balance"):
                                        st.session_state.confirm_negative = True
                                        st.rerun()
                                    st.stop()
                        except Exception as e:
                            st.error(f"Failed to validate: {str(e)}")
                            st.stop()

                        # Execute adjustment
                        try:
                            with get_session() as session:
                                transaction = adjust_credits(
                                    session=session,
                                    user_id=user.id,
                                    amount=amount_decimal,
                                    reason=reason,
                                    admin_username=os.getenv("ADMIN_USERNAME", "admin"),
                                    transaction_type=tx_type
                                )

                            st.success(f"✅ Credit adjustment successful: {format_minutes(amount_decimal, signed=True)}")
                            st.session_state.confirm_large_adjustment = False
                            st.session_state.confirm_negative = False
                            st.cache_data.clear()
                            st.rerun()

                        except ValueError as e:
                            st.error(f"❌ Validation error: {str(e)}")
                            st.session_state.confirm_large_adjustment = False
                            st.session_state.confirm_negative = False
                        except Exception as e:
                            st.error(f"❌ Failed to adjust credits: {str(e)}")
                            st.session_state.confirm_large_adjustment = False
                            st.session_state.confirm_negative = False
                            logger.exception("Failed to adjust credits")

        except Exception as e:
            st.error(f"Failed to load credit data: {str(e)}")
            logger.exception("Failed to load credit data")
