"""
Promotions - Promotion code tracking and usage monitoring
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from config.auth import require_auth
from database.connection import get_session
from services.promotion_service import (
    get_promotion_codes,
    get_promotion_code_by_id,
    get_users_by_promotion_code,
    get_usage_history,
    get_promotion_code_stats
)
from utils.formatters import format_datetime, format_status_badge
import logging

logger = logging.getLogger(__name__)

# Auth check
if not require_auth():
    st.stop()

st.title("🎟️ Promotions")
st.markdown("Track promotion codes and usage")

# Search and filters
col1, col2 = st.columns([3, 1])
with col1:
    search_query = st.text_input("🔍 Search by code or Stripe ID", placeholder="Enter promotion code...")
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Initialize session state for selected promotion code
if "selected_promo_id" not in st.session_state:
    st.session_state.selected_promo_id = None

# Load promotion codes
@st.cache_data(ttl=60)
def load_promotion_codes(search, page_num, per_page):
    """Load promotion codes with filters"""
    try:
        with get_session() as session:
            offset = page_num * per_page
            return get_promotion_codes(
                session,
                limit=per_page,
                offset=offset,
                search_query=search if search else None
            )
    except Exception as e:
        logger.error(f"Error loading promotion codes: {e}", exc_info=True)
        raise

# Main layout: table + detail panel
table_col, detail_col = st.columns([4, 6])

with table_col:
    st.markdown("### Promotion Codes")

    try:
        promo_codes = load_promotion_codes(search_query, 0, 50)

        if not promo_codes:
            st.info("No promotion codes found")
        else:
            # Convert to DataFrame
            promo_df = pd.DataFrame([
                {
                    "Code": pc.code or "N/A",
                    "Stripe ID": pc.stripe_promotion_id or "N/A",
                    "Created": format_datetime(pc.created_at, format_str='%Y-%m-%d'),
                    "ID": str(pc.id)
                }
                for pc in promo_codes
            ])

            # Display DataFrame with row selection
            st.markdown("*Click on a row to view details*")

            event = st.dataframe(
                promo_df.drop(columns=["ID"]),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                height=500
            )

            # Update selected promotion code ID if a row is selected
            if event and "selection" in event and "rows" in event["selection"]:
                if len(event["selection"]["rows"]) > 0:
                    selected_idx = event["selection"]["rows"][0]
                    selected_promo_id = promo_df.iloc[selected_idx]["ID"]
                    st.session_state.selected_promo_id = selected_promo_id

            # Show count
            st.caption(f"Showing {len(promo_codes)} promotion codes")

    except Exception as e:
        logger.error(f"Failed to load promotion codes: {e}", exc_info=True)
        st.error(f"❌ Failed to load promotion codes: {str(e)}")

with detail_col:
    st.markdown("### Promotion Details")

    if st.session_state.selected_promo_id:
        # Load full promotion code details
        @st.cache_data(ttl=60)
        def load_promo_details(promo_id):
            """Load promotion code details with related data"""
            try:
                with get_session() as session:
                    promo_code = get_promotion_code_by_id(session, promo_id)
                    if not promo_code:
                        return None

                    users = get_users_by_promotion_code(session, promo_id)
                    stats = get_promotion_code_stats(session, promo_id)
                    usage = get_usage_history(session, promo_code_id=promo_id, limit=20)

                    return {
                        "promo_code": promo_code,
                        "users": users,
                        "stats": stats,
                        "usage": usage
                    }
            except Exception as e:
                logger.error(f"Error loading promo details: {e}", exc_info=True)
                raise

        try:
            details = load_promo_details(st.session_state.selected_promo_id)

            if not details or not details["promo_code"]:
                st.warning("Promotion code not found")
            else:
                promo = details["promo_code"]

                # Basic info card
                st.markdown("#### Basic Info")
                st.markdown(f"**Code:** `{promo.code}`")
                if promo.stripe_promotion_id:
                    stripe_url = f"https://dashboard.stripe.com/coupons/{promo.stripe_promotion_id}"
                    st.markdown(f"**Stripe ID:** [{promo.stripe_promotion_id}]({stripe_url})")
                else:
                    st.markdown(f"**Stripe ID:** N/A")
                st.markdown(f"**Created:** {format_datetime(promo.created_at)}")

                st.divider()

                # Statistics
                st.markdown("#### Statistics")
                stats = details["stats"]
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("Current Users", stats.get("user_count", 0))
                with col_stat2:
                    st.metric("Total Usage", stats.get("total_usage_count", 0))
                with col_stat3:
                    # Calculate success rate
                    usage_by_action = stats.get("usage_by_action", {})
                    applied = usage_by_action.get("applied", 0)
                    total = stats.get("total_usage_count", 1)
                    success_rate = int((applied / total * 100)) if total > 0 else 0
                    st.metric("Success Rate", f"{success_rate}%")

                # Usage breakdown
                if usage_by_action:
                    st.markdown("**Usage Breakdown:**")
                    for action, count in usage_by_action.items():
                        badge_type = {
                            "validated": "success",
                            "applied": "success",
                            "cleared": "warning",
                            "failed": "danger"
                        }.get(action, "info")
                        st.markdown(f"- {action.capitalize()}: **{count}**")

                st.divider()

                # Current users
                st.markdown("#### Current Users")
                users = details["users"]
                if users:
                    for user in users[:10]:  # Limit to 10
                        st.markdown(f"- {user.email}")
                    if len(users) > 10:
                        st.caption(f"+ {len(users) - 10} more users")
                else:
                    st.caption("No users currently using this code")

                st.divider()

                # Usage history
                st.markdown("#### Recent Usage History")
                usage = details["usage"]
                if usage:
                    usage_df = pd.DataFrame([
                        {
                            "Date": format_datetime(u.created_at, format_str='%Y-%m-%d %H:%M'),
                            "User": u.user.email if u.user else "N/A",
                            "Action": u.action.capitalize(),
                            "Invoice": u.stripe_invoice_id or "-",
                        }
                        for u in usage
                    ])

                    st.dataframe(
                        usage_df,
                        use_container_width=True,
                        hide_index=True,
                        height=300
                    )

                    if len(usage) >= 20:
                        st.caption("Showing last 20 usage records")
                else:
                    st.caption("No usage history found")

        except Exception as e:
            logger.error(f"Failed to load promotion details: {e}", exc_info=True)
            st.error(f"❌ Failed to load promotion details: {str(e)}")

    else:
        st.info("Select a promotion code from the table to view details")

# Export functionality
st.divider()

export_col1, export_col2 = st.columns(2)

with export_col1:
    if st.button("📥 Export Codes to CSV", use_container_width=True):
        try:
            with st.spinner("Exporting promotion codes..."):
                promo_codes = load_promotion_codes(search_query, 0, 1000)  # Load more for export

                if not promo_codes:
                    st.warning("No promotion codes to export")
                else:
                    export_df = pd.DataFrame([
                        {
                            "Code": pc.code or "N/A",
                            "Stripe Promotion ID": pc.stripe_promotion_id or "N/A",
                            "Created At": format_datetime(pc.created_at),
                            "ID": str(pc.id)
                        }
                        for pc in promo_codes
                    ])

                    csv = export_df.to_csv(index=False)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

                    st.download_button(
                        label="📥 Download Codes CSV",
                        data=csv,
                        file_name=f"promotion_codes_{timestamp}.csv",
                        mime="text/csv",
                        key='download-codes-csv',
                        use_container_width=True
                    )

                    st.success(f"✓ Exported {len(export_df)} promotion codes")

                    if len(promo_codes) >= 1000:
                        st.warning("⚠️ Export limited to 1000 codes. Use filters to export specific codes.")

        except Exception as e:
            logger.error(f"CSV export failed: {e}", exc_info=True)
            st.error(f"❌ Failed to export: {str(e)}")

with export_col2:
    if st.button("📥 Export Usage to CSV", use_container_width=True, disabled=not st.session_state.selected_promo_id):
        try:
            if not st.session_state.selected_promo_id:
                st.warning("Please select a promotion code first")
            else:
                with st.spinner("Exporting usage history..."):
                    with get_session() as session:
                        usage = get_usage_history(
                            session,
                            promo_code_id=st.session_state.selected_promo_id,
                            limit=1000
                        )

                    if not usage:
                        st.warning("No usage history to export")
                    else:
                        export_df = pd.DataFrame([
                            {
                                "Date": format_datetime(u.created_at),
                                "User Email": u.user.email if u.user else "N/A",
                                "Action": u.action,
                                "Stripe Invoice ID": u.stripe_invoice_id or "N/A",
                                "Stripe Subscription ID": u.stripe_subscription_id or "N/A",
                                "Failure Reason": u.failure_reason or "N/A"
                            }
                            for u in usage
                        ])

                        csv = export_df.to_csv(index=False)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

                        st.download_button(
                            label="📥 Download Usage CSV",
                            data=csv,
                            file_name=f"promotion_usage_{timestamp}.csv",
                            mime="text/csv",
                            key='download-usage-csv',
                            use_container_width=True
                        )

                        st.success(f"✓ Exported {len(export_df)} usage records")

                        if len(usage) >= 1000:
                            st.warning("⚠️ Export limited to 1000 records.")

        except Exception as e:
            logger.error(f"Usage CSV export failed: {e}", exc_info=True)
            st.error(f"❌ Failed to export usage: {str(e)}")

# Last updated timestamp
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
