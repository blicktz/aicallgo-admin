"""
Twilio Phone Number Pool Dashboard
Comprehensive view of Twilio phone number inventory, health, and utilization
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from config.auth import require_auth
from config.settings import settings
from database.connection import get_session
from services.twilio_service import (
    get_pool_status,
    get_phone_numbers,
    get_phone_number_stats,
    get_recycling_candidates,
    get_sync_health,
    get_subscription_status_breakdown,
    get_old_unassigned_numbers,
    get_pool_history_metrics
)
from components.twilio_cards import (
    pool_status_card,
    pool_capacity_gauge,
    sync_status_indicator,
    recycling_queue_card,
    activity_timeline_card,
    configuration_info_card,
    status_badge
)
from utils.formatters import format_datetime, format_phone

# Auth check
if not require_auth():
    st.stop()

st.title("📞 Twilio Phone Number Pool")
st.markdown("Comprehensive dashboard for Twilio phone number inventory and health monitoring")

# Initialize session state for selected phone number
if "selected_phone_id" not in st.session_state:
    st.session_state.selected_phone_id = None

# Top filters and refresh
col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

with col1:
    status_filter = st.selectbox(
        "Status",
        ["all", "available", "assigned", "released", "error"],
        help="Filter phone numbers by status"
    )

with col2:
    search_query = st.text_input(
        "🔍 Search",
        placeholder="Phone number or SID...",
        help="Search by phone number or Twilio SID"
    )

with col3:
    include_inactive = st.checkbox(
        "Include Inactive",
        value=False,
        help="Include numbers marked as inactive"
    )

with col4:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

# ===============================
# CACHED DATA FUNCTIONS
# ===============================
@st.cache_data(ttl=60)
def load_pool_status():
    with get_session() as session:
        return get_pool_status(session)

@st.cache_data(ttl=60)
def load_pool_stats():
    with get_session() as session:
        return get_phone_number_stats(session)

@st.cache_data(ttl=60)
def load_sync_health():
    with get_session() as session:
        return get_sync_health(session)

@st.cache_data(ttl=60)
def load_recycling():
    with get_session() as session:
        return get_recycling_candidates(session)

@st.cache_data(ttl=60)
def load_history(days=7):
    with get_session() as session:
        return get_pool_history_metrics(session, days=days)

@st.cache_data(ttl=60)
def load_phone_numbers(status, search, inactive):
    with get_session() as session:
        return get_phone_numbers(
            session,
            status_filter=status if status != "all" else None,
            search_query=search if search else None,
            limit=200,
            offset=0,
            include_inactive=inactive
        )

@st.cache_data(ttl=60)
def load_subscription_breakdown():
    with get_session() as session:
        return get_subscription_status_breakdown(session)

@st.cache_data(ttl=60)
def load_old_unassigned():
    with get_session() as session:
        return get_old_unassigned_numbers(session, older_than_days=30)

# ===============================
# SECTION 1: OVERVIEW METRICS
# ===============================
st.markdown("## 📊 Pool Overview")

try:
    pool_status = load_pool_status()
    pool_status_card(pool_status)

except Exception as e:
    st.error(f"Failed to load pool status: {str(e)}")

st.divider()

# ===============================
# SECTION 2: POOL HEALTH DASHBOARD
# ===============================
st.markdown("## 🏥 Pool Health Dashboard")

health_col1, health_col2 = st.columns([5, 5])

with health_col1:
    st.markdown("### Capacity & Utilization")

    try:
        stats = load_pool_stats()

        # Pool capacity gauge
        pool_capacity_gauge(
            stats.get("pool_capacity_pct", 0),
            stats.get("pool_capacity_count", 0),
            stats.get("pool_capacity_max", 4)
        )

        # Additional stats
        st.markdown("**Efficiency Metrics**")
        metric_col1, metric_col2 = st.columns(2)

        with metric_col1:
            avg_time = stats.get("avg_time_to_assignment_hours")
            if avg_time is not None:
                if avg_time < 1:
                    st.metric("Avg Time to Assignment", f"{int(avg_time * 60)}m", help="Average time from purchase to first assignment")
                elif avg_time < 24:
                    st.metric("Avg Time to Assignment", f"{avg_time:.1f}h", help="Average time from purchase to first assignment")
                else:
                    st.metric("Avg Time to Assignment", f"{avg_time/24:.1f}d", help="Average time from purchase to first assignment")
            else:
                st.metric("Avg Time to Assignment", "N/A", help="No assignment data available")

        with metric_col2:
            oldest_days = stats.get("oldest_available_days")
            if oldest_days is not None:
                st.metric(
                    "Oldest Available",
                    f"{oldest_days}d",
                    help="Age of oldest unassigned number"
                )
            else:
                st.metric("Oldest Available", "N/A", help="No available numbers")

        # Recent activity timeline
        st.markdown("---")
        try:
            history = load_history(days=7)
            activity_timeline_card(history)

        except Exception as e:
            st.warning(f"Could not load activity timeline: {str(e)}")

    except Exception as e:
        st.error(f"Failed to load pool stats: {str(e)}")

with health_col2:
    st.markdown("### Health & Maintenance")

    try:
        sync_health = load_sync_health()
        sync_status_indicator(sync_health)

        recycling = load_recycling()
        recycling_queue_card(recycling)

        # Configuration info
        st.markdown("---")
        config = {
            "max_pool_size": getattr(settings, 'PN_ACTIVE_NUMBER_MAX_POOL_SIZE', 4),
            "purchase_batch_size": getattr(settings, 'PN_PURCHASE_BATCH_SIZE', 1),
            "max_unused": getattr(settings, 'PN_MAX_UNUSED', 2)
        }
        configuration_info_card(config)

    except Exception as e:
        st.error(f"Failed to load health metrics: {str(e)}")

st.divider()

# ===============================
# SECTION 3: PHONE NUMBER TABLE
# ===============================
st.markdown("## 📋 Phone Number Inventory")

try:
    phone_numbers, total_count = load_phone_numbers(status_filter, search_query, include_inactive)

    if not phone_numbers:
        st.info("No phone numbers found matching the filters")
    else:
        # Show count
        showing = len(phone_numbers)
        if showing < total_count:
            st.markdown(f"**Showing {showing} of {total_count} numbers** (limited to 200 for performance)")
        else:
            st.markdown(f"**Total: {total_count} numbers**")

        # Create DataFrame for display
        phone_df = pd.DataFrame([
            {
                "Phone": format_phone(phone.phone_number),
                "Status": phone.status,
                "Business": phone.business.business_name if phone.business else "—",
                "Purchased": phone.purchase_date.strftime("%Y-%m-%d") if phone.purchase_date else "—",
                "Assigned": phone.assigned_at.strftime("%Y-%m-%d") if phone.assigned_at else "—",
                "Last Sync": phone.last_twilio_sync_at.strftime("%Y-%m-%d %H:%M") if phone.last_twilio_sync_at else "Never",
                "Active": "✅" if phone.is_active else "❌",
                "Error": "⚠️" if phone.twilio_sync_error else "",
                "ID": str(phone.id)
            }
            for phone in phone_numbers
        ])

        # Display table
        st.markdown("*Click a row to view full details below*")
        phone_event = st.dataframe(
            phone_df.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            height=400
        )

        # Update selected phone ID
        if phone_event and "selection" in phone_event and "rows" in phone_event["selection"]:
            if len(phone_event["selection"]["rows"]) > 0:
                selected_idx = phone_event["selection"]["rows"][0]
                selected_phone_id = phone_df.iloc[selected_idx]["ID"]
                st.session_state.selected_phone_id = selected_phone_id

        st.divider()

        # ===============================
        # SECTION 4: PHONE DETAILS PANEL
        # ===============================
        if st.session_state.selected_phone_id:
            # Find the selected phone in the list
            selected_phone = next(
                (phone for phone in phone_numbers if str(phone.id) == st.session_state.selected_phone_id),
                None
            )

            if selected_phone:
                st.markdown("### 📱 Phone Number Details")

                detail_col1, detail_col2, detail_col3 = st.columns(3)

                with detail_col1:
                    st.markdown("**Phone Info**")
                    st.markdown(f"**Number:** {format_phone(selected_phone.phone_number)}")
                    st.markdown(f"**Status:** {status_badge(selected_phone.status)}", unsafe_allow_html=True)
                    st.markdown(f"**Country:** {selected_phone.country_code or 'US'}")
                    st.markdown(f"**Active:** {'✅ Yes' if selected_phone.is_active else '❌ No'}")

                with detail_col2:
                    st.markdown("**Lifecycle**")
                    if selected_phone.purchase_date:
                        st.markdown(f"**Purchased:** {format_datetime(selected_phone.purchase_date, '%Y-%m-%d')}")
                    if selected_phone.assigned_at:
                        st.markdown(f"**Assigned:** {format_datetime(selected_phone.assigned_at, '%Y-%m-%d %H:%M')}")
                    if selected_phone.released_at:
                        st.markdown(f"**Released:** {format_datetime(selected_phone.released_at, '%Y-%m-%d %H:%M')}")
                    if selected_phone.release_scheduled_at:
                        st.markdown(f"**Release Scheduled:** {format_datetime(selected_phone.release_scheduled_at, '%Y-%m-%d %H:%M')}")

                with detail_col3:
                    st.markdown("**Technical**")
                    if selected_phone.twilio_phone_number_sid:
                        st.markdown(f"**Twilio SID:** `{selected_phone.twilio_phone_number_sid[:20]}...`")
                    if selected_phone.last_twilio_sync_at:
                        st.markdown(f"**Last Sync:** {format_datetime(selected_phone.last_twilio_sync_at, '%Y-%m-%d %H:%M')}")
                    else:
                        st.markdown("**Last Sync:** Never")

                # Business assignment details
                if selected_phone.business:
                    with st.expander("🏢 Business Assignment", expanded=True):
                        st.markdown(f"**Business Name:** {selected_phone.business.business_name or 'Unnamed'}")
                        st.markdown(f"**Business ID:** `{selected_phone.business.id}`")
                        if selected_phone.business.industry:
                            st.markdown(f"**Industry:** {selected_phone.business.industry}")
                        if selected_phone.webhook_url:
                            st.markdown(f"**Webhook URL:** `{selected_phone.webhook_url[:50]}...`")
                            st.markdown(f"**Webhook Method:** {selected_phone.webhook_method or 'POST'}")

                # Sync error details
                if selected_phone.twilio_sync_error:
                    with st.expander("⚠️ Sync Error Details", expanded=True):
                        st.error(selected_phone.twilio_sync_error)
                        if selected_phone.last_twilio_sync_at:
                            st.caption(f"Error occurred at: {format_datetime(selected_phone.last_twilio_sync_at)}")

                # Capabilities
                if selected_phone.twilio_capabilities:
                    with st.expander("🔧 Twilio Capabilities", expanded=False):
                        st.json(selected_phone.twilio_capabilities)

                # Full details JSON
                with st.expander("📄 Full Details (JSON)", expanded=False):
                    details_json = {
                        "id": str(selected_phone.id),
                        "phone_number": selected_phone.phone_number,
                        "twilio_sid": selected_phone.twilio_phone_number_sid,
                        "status": selected_phone.status,
                        "is_active": selected_phone.is_active,
                        "country_code": selected_phone.country_code,
                        "purchase_date": selected_phone.purchase_date.isoformat() if selected_phone.purchase_date else None,
                        "assigned_at": selected_phone.assigned_at.isoformat() if selected_phone.assigned_at else None,
                        "released_at": selected_phone.released_at.isoformat() if selected_phone.released_at else None,
                        "business_id": str(selected_phone.business_id) if selected_phone.business_id else None,
                        "webhook_url": selected_phone.webhook_url,
                        "webhook_method": selected_phone.webhook_method,
                        "last_sync": selected_phone.last_twilio_sync_at.isoformat() if selected_phone.last_twilio_sync_at else None,
                        "sync_error": selected_phone.twilio_sync_error
                    }
                    st.json(details_json)

            else:
                st.warning("Selected phone number not found")
        else:
            st.info("👆 Select a phone number from the table above to view full details")

except Exception as e:
    st.error(f"Failed to load phone numbers: {str(e)}")

st.divider()

# ===============================
# SECTION 5: RECYCLING & MAINTENANCE
# ===============================
st.markdown("## ♻️ Recycling & Maintenance")

tab1, tab2, tab3 = st.tabs(["Immediate Recycling", "Grace Period", "Old Unassigned"])

with tab1:
    st.markdown("### Numbers with Expired Subscriptions (Immediate Recycling)")
    st.caption("Subscription statuses: canceled, unpaid, incomplete_expired")

    try:
        recycling_data = load_recycling()
        immediate = recycling_data.get("immediate", [])

        if not immediate:
            st.success("✅ No numbers require immediate recycling")
        else:
            st.warning(f"⚠️ {len(immediate)} number(s) eligible for immediate recycling")

            immediate_df = pd.DataFrame([
                {
                    "Phone": format_phone(item["phone_number"]),
                    "Business": item["business_name"],
                    "Subscription": item["subscription_status"],
                    "Days in Status": item["days_in_status"],
                    "Last Updated": item["subscription_updated"].strftime("%Y-%m-%d") if item["subscription_updated"] else "N/A"
                }
                for item in immediate
            ])

            st.dataframe(immediate_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Failed to load immediate recycling candidates: {str(e)}")

with tab2:
    st.markdown("### Numbers with Past Due Subscriptions (30+ Days)")
    st.caption("Numbers in grace period before recycling")

    try:
        grace = recycling_data.get("grace_period", [])

        if not grace:
            st.success("✅ No numbers in grace period")
        else:
            st.info(f"ℹ️ {len(grace)} number(s) in grace period (past_due 30+ days)")

            grace_df = pd.DataFrame([
                {
                    "Phone": format_phone(item["phone_number"]),
                    "Business": item["business_name"],
                    "Subscription": item["subscription_status"],
                    "Days in Status": item["days_in_status"],
                    "Last Updated": item["subscription_updated"].strftime("%Y-%m-%d") if item["subscription_updated"] else "N/A"
                }
                for item in grace
            ])

            st.dataframe(grace_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Failed to load grace period candidates: {str(e)}")

with tab3:
    st.markdown("### Old Unassigned Numbers (Available 30+ Days)")
    st.caption("Available numbers that have been idle for extended periods")

    try:
        old_numbers = load_old_unassigned()

        if not old_numbers:
            st.success("✅ No old unassigned numbers")
        else:
            st.info(f"ℹ️ {len(old_numbers)} number(s) available for 30+ days")

            old_df = pd.DataFrame([
                {
                    "Phone": format_phone(item["phone_number"]),
                    "Purchased": item["purchase_date"].strftime("%Y-%m-%d") if item["purchase_date"] else "N/A",
                    "Days Available": item["days_available"],
                    "Last Released": item["last_released"].strftime("%Y-%m-%d") if item["last_released"] else "Never",
                    "Twilio SID": item["twilio_sid"][:20] + "..." if item["twilio_sid"] else "N/A"
                }
                for item in old_numbers
            ])

            st.dataframe(old_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Failed to load old unassigned numbers: {str(e)}")

st.divider()

# ===============================
# SECTION 6: SUBSCRIPTION BREAKDOWN
# ===============================
st.markdown("## 💳 Subscription Status Breakdown")
st.caption("Distribution of assigned phone numbers by subscription status")

try:
    breakdown = load_subscription_breakdown()

    if not breakdown:
        st.info("No assigned numbers with active subscriptions")
    else:
        # Create columns for metrics
        status_cols = st.columns(min(len(breakdown), 4))

        for idx, (status, count) in enumerate(breakdown.items()):
            col_idx = idx % 4
            with status_cols[col_idx]:
                st.metric(status.replace("_", " ").title(), count)

        # Create pie chart data
        breakdown_df = pd.DataFrame([
            {"Subscription Status": status.replace("_", " ").title(), "Count": count}
            for status, count in breakdown.items()
        ])

        st.dataframe(breakdown_df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Failed to load subscription breakdown: {str(e)}")

st.divider()

# ===============================
# EXPORT FUNCTIONALITY
# ===============================
st.markdown("## 📥 Export")

if st.button("📥 Export Current View to CSV", use_container_width=True):
    try:
        phone_numbers, _ = load_phone_numbers(status_filter, search_query, include_inactive)

        if not phone_numbers:
            st.warning("No phone numbers to export")
        else:
            export_df = pd.DataFrame([
                {
                    "Phone Number": phone.phone_number,
                    "Status": phone.status,
                    "Business Name": phone.business.business_name if phone.business else "N/A",
                    "Business ID": str(phone.business_id) if phone.business_id else "N/A",
                    "Country Code": phone.country_code,
                    "Purchase Date": phone.purchase_date.isoformat() if phone.purchase_date else "N/A",
                    "Assigned Date": phone.assigned_at.isoformat() if phone.assigned_at else "N/A",
                    "Released Date": phone.released_at.isoformat() if phone.released_at else "N/A",
                    "Last Sync": phone.last_twilio_sync_at.isoformat() if phone.last_twilio_sync_at else "N/A",
                    "Sync Error": phone.twilio_sync_error or "N/A",
                    "Is Active": phone.is_active,
                    "Twilio SID": phone.twilio_phone_number_sid or "N/A",
                    "Webhook URL": phone.webhook_url or "N/A"
                }
                for phone in phone_numbers
            ])

            csv = export_df.to_csv(index=False)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"twilio_phone_numbers_{timestamp}.csv",
                mime="text/csv",
                key='download-csv',
                use_container_width=True
            )

            st.success(f"✓ Ready to export {len(export_df)} phone numbers")

    except Exception as e:
        st.error(f"Failed to export: {str(e)}")
