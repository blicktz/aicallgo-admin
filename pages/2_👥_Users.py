"""
Users - User browsing with search and detail view
"""
import streamlit as st
import pandas as pd
from config.auth import require_auth
from database.connection import get_session
from services.user_service import (
    get_users,
    get_user_by_id,
    update_user_email,
    generate_deleted_email
)
from services.business_service import get_businesses_by_user
from services.billing_service import get_subscription_by_user, get_credit_balance
from components.tables import render_dataframe
from utils.formatters import format_datetime, format_currency, format_status_badge

# Auth check
if not require_auth():
    st.stop()

st.title("👥 Users")
st.markdown("Browse and search users")

# Search and filters
search_query = st.text_input("🔍 Search by email or name", placeholder="Enter email or name...")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    plan_filter = st.selectbox("Plan", ["all", "trial", "professional", "scale"])
with col2:
    status_filter = st.selectbox("Status", ["all", "active", "inactive"])
with col3:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# Initialize session state for selected user
if "selected_user_id" not in st.session_state:
    st.session_state.selected_user_id = None

# Load users
@st.cache_data(ttl=60)
def load_users(search, plan, status, page_num, per_page):
    """Load users with filters"""
    with get_session() as session:
        offset = page_num * per_page
        return get_users(
            session,
            limit=per_page,
            offset=offset,
            search_query=search if search else None,
            plan_filter=plan if plan != "all" else None,
            status_filter=status if status != "all" else None
        )

# Main layout: table + detail panel (30% list, 70% details)
table_col, detail_col = st.columns([3, 7])

with table_col:
    st.markdown("### User List")

    try:
        users = load_users(search_query, plan_filter, status_filter, 0, 50)

        if not users:
            st.info("No users found matching your criteria")
        else:
            # Convert to DataFrame
            users_df = pd.DataFrame([
                {
                    "Email": u.email,
                    "Name": u.full_name or "N/A",
                    "Status": "Active" if u.is_active else "Inactive",
                    "ID": str(u.id)
                }
                for u in users
            ])

            # Add selection handler
            st.markdown("*Click on a row to view details*")

            # Display DataFrame with row selection
            event = st.dataframe(
                users_df.drop(columns=["ID"]),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                height=600
            )

            # Update selected user ID if a row is selected
            if event and "selection" in event and "rows" in event["selection"]:
                if len(event["selection"]["rows"]) > 0:
                    selected_idx = event["selection"]["rows"][0]
                    selected_user_id = users_df.iloc[selected_idx]["ID"]
                    st.session_state.selected_user_id = selected_user_id

            # Show count
            st.caption(f"Showing {len(users)} users")

    except Exception as e:
        st.error(f"Failed to load users: {str(e)}")

with detail_col:
    st.markdown("### User Details")

    if st.session_state.selected_user_id:
        # Load full user details
        @st.cache_data(ttl=60)
        def load_user_details(user_id):
            """Load user details with related data"""
            with get_session() as session:
                user = get_user_by_id(session, user_id)
                if not user:
                    return None

                businesses = get_businesses_by_user(session, user_id)
                subscription = get_subscription_by_user(session, user_id)
                credit_balance = get_credit_balance(session, user_id)

                return {
                    "user": user,
                    "businesses": businesses,
                    "subscription": subscription,
                    "credit_balance": credit_balance
                }

        try:
            details = load_user_details(st.session_state.selected_user_id)

            if not details or not details["user"]:
                st.warning("User not found")
            else:
                user = details["user"]

                # User info card
                st.markdown("#### Basic Info")
                st.markdown(f"**Email:** {user.email}")
                st.markdown(f"**Name:** {user.full_name or 'N/A'}")
                st.markdown(f"**Status:** {format_status_badge('active' if user.is_active else 'inactive')}")
                st.markdown(f"**Created:** {format_datetime(user.created_at)}")

                if user.stripe_customer_id:
                    stripe_url = f"https://dashboard.stripe.com/customers/{user.stripe_customer_id}"
                    st.markdown(f"**Stripe:** [View Customer]({stripe_url})")

                st.divider()

                # Email Management
                st.markdown("#### ✉️ Email Management")

                with st.expander("Edit Email Address", expanded=False):
                    st.caption("⚠️ Use case: 'Soft delete' user by changing email to _deleted_ format, freeing up original email for new account")

                    # Manual email edit
                    st.markdown("**Option 1: Manual Edit**")
                    new_email = st.text_input(
                        "New Email Address",
                        value="",
                        placeholder="user_deleted_abc123@example.com",
                        key=f"email_input_{user.id}"
                    )

                    col_manual, col_quick = st.columns(2)

                    with col_manual:
                        if st.button("💾 Update Email", key=f"update_btn_{user.id}", use_container_width=True):
                            if new_email:
                                with get_session() as session:
                                    success, message = update_user_email(session, str(user.id), new_email)
                                    if success:
                                        st.success(message)
                                        # Clear cache to refresh data
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error(message)
                            else:
                                st.warning("Please enter a new email address")

                    st.divider()

                    # Quick soft delete
                    st.markdown("**Option 2: Quick Soft Delete**")
                    st.caption("Automatically generates: `{username}_deleted_{random}@{domain}`")

                    # Initialize session state for generated email
                    generated_email_key = f"generated_deleted_email_{user.id}"
                    if generated_email_key not in st.session_state:
                        st.session_state[generated_email_key] = None

                    with col_quick:
                        # Button 1: Generate deleted email
                        if st.button("🗑️ Generate Deleted Email", key=f"soft_delete_btn_{user.id}", use_container_width=True):
                            try:
                                deleted_email = generate_deleted_email(user.email)
                                st.session_state[generated_email_key] = deleted_email
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error generating deleted email: {str(e)}")

                    # Show preview and confirm button if email was generated
                    if st.session_state[generated_email_key]:
                        st.info(f"📧 Generated: `{st.session_state[generated_email_key]}`")

                        col_confirm, col_cancel = st.columns(2)

                        with col_confirm:
                            # Button 2: Confirm and apply (now independent!)
                            if st.button("✅ Confirm & Apply", key=f"confirm_delete_{user.id}", use_container_width=True):
                                with get_session() as session:
                                    success, message = update_user_email(
                                        session,
                                        str(user.id),
                                        st.session_state[generated_email_key]
                                    )
                                    if success:
                                        st.success(f"✅ {message}")
                                        st.info(f"Original email `{user.email}` is now available for new account registration")
                                        # Clear the generated email from session state
                                        st.session_state[generated_email_key] = None
                                        # Clear cache to refresh data
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error(message)

                        with col_cancel:
                            # Button 3: Cancel
                            if st.button("❌ Cancel", key=f"cancel_delete_{user.id}", use_container_width=True):
                                st.session_state[generated_email_key] = None
                                st.rerun()

                st.divider()

                # Onboarding & Verification
                st.markdown("#### Onboarding & Verification")

                # Call forwarding verified status
                verified_badge = "✅ Verified" if user.call_forwarding_verified else "❌ Not Verified"
                verified_color = "green" if user.call_forwarding_verified else "red"
                st.markdown(f"**Call Forwarding:** :{verified_color}[{verified_badge}]")

                # Onboarding status
                if user.onboarding_status:
                    status_display = user.onboarding_status.replace('_', ' ').title()
                    st.markdown(f"**Onboarding Status:** {status_display}")

                # Onboarding completed timestamp
                if user.onboarding_completed_at:
                    st.markdown(f"**Completed At:** {format_datetime(user.onboarding_completed_at)}")

                # Extract data from onboarding_data JSONB field
                if user.onboarding_data:
                    onboarding_data = user.onboarding_data

                    # Test phone number
                    if onboarding_data.get('phone_number') or onboarding_data.get('test_phone_number'):
                        phone = onboarding_data.get('phone_number') or onboarding_data.get('test_phone_number')
                        st.markdown(f"**Test Phone:** {phone}")

                    # Carrier/Provider information
                    if onboarding_data.get('provider') or onboarding_data.get('carrier_name'):
                        carrier = onboarding_data.get('provider') or onboarding_data.get('carrier_name')
                        st.markdown(f"**Carrier:** {carrier}")

                    # Verification code (for debugging/support)
                    if onboarding_data.get('verification_code'):
                        st.markdown(f"**Verification Code:** `{onboarding_data.get('verification_code')}`")

                st.divider()

                # Subscription info
                st.markdown("#### Subscription")
                if details["subscription"]:
                    sub = details["subscription"]
                    st.markdown(f"**Status:** {format_status_badge(sub.status)}")
                    st.markdown(f"**Plan:** {sub.stripe_plan_id}")
                    if sub.current_period_end:
                        st.markdown(f"**Renews:** {format_datetime(sub.current_period_end, format_str='%Y-%m-%d')}")
                else:
                    st.caption("No active subscription")

                st.divider()

                # Credit balance
                st.markdown("#### Credit Balance")
                if details["credit_balance"]:
                    # Note: Adjust field names based on actual CreditBalance schema
                    st.info("Credit balance details - Schema needs verification")
                else:
                    st.caption("No credit balance record")

                st.divider()

                # Businesses
                st.markdown("#### Businesses")
                if details["businesses"]:
                    for biz in details["businesses"]:
                        st.markdown(f"- **{biz.business_name or 'Unnamed'}**")
                        if biz.industry:
                            st.caption(f"  Industry: {biz.industry}")
                else:
                    st.caption("No businesses")

                st.divider()

                # Quick Actions
                st.markdown("#### Quick Actions")
                st.button("⚡ Edit Entitlements", disabled=True, help="Coming in Phase 3")
                st.button("💰 Adjust Credits", disabled=True, help="Coming in Phase 3")
                st.button("📞 View Call Logs", disabled=True, help="Go to Call Logs page")

        except Exception as e:
            st.error(f"Failed to load user details: {str(e)}")

    else:
        st.info("Select a user from the table to view details")

# Export functionality
st.divider()
if st.button("📥 Export to CSV", use_container_width=True):
    try:
        users = load_users(search_query, plan_filter, status_filter, 0, 1000)  # Load more for export
        users_df = pd.DataFrame([
            {
                "Email": u.email,
                "Name": u.full_name or "N/A",
                "Status": "Active" if u.is_active else "Inactive",
                "ID": str(u.id)
            }
            for u in users
        ])

        csv = users_df.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            "users.csv",
            "text/csv",
            key='download-csv'
        )
    except Exception as e:
        st.error(f"Failed to export: {str(e)}")
