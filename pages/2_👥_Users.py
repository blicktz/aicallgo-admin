"""
Users - User browsing with search and detail view
"""
import streamlit as st
import pandas as pd
from config.auth import require_auth
from database.connection import get_session
from services.user_service import get_users, get_user_by_id
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

# Main layout: table + detail panel
table_col, detail_col = st.columns([7, 3])

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
                    "Created": format_datetime(u.created_at, format_str="%Y-%m-%d %H:%M"),
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
                "Created": format_datetime(u.created_at),
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
