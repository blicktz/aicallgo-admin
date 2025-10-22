"""
Dashboard - System overview with KPIs and charts
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from config.auth import require_auth
from database.connection import get_session
from services.user_service import get_user_stats, get_recent_signups
from services.billing_service import get_billing_stats
from services.call_log_service import get_call_stats
from components.cards import metric_card, info_card
from components.charts import line_chart, area_chart
from utils.formatters import format_currency, format_number_abbrev, humanize_datetime

# Auth check
if not require_auth():
    st.stop()

# Page config
st.title("📊 Dashboard")
st.markdown("System overview and key metrics")

# Auto-refresh toggle
col1, col2 = st.columns([3, 1])
with col2:
    auto_refresh = st.checkbox("Auto-refresh (60s)", value=False)
    if auto_refresh:
        st.rerun()

# Load data
@st.cache_data(ttl=60)
def load_dashboard_data():
    """Load all dashboard data with caching"""
    with get_session() as session:
        user_stats = get_user_stats(session)
        billing_stats = get_billing_stats(session, date_range=30)
        call_stats = get_call_stats(session, date_range=30)
        recent_users = get_recent_signups(session, limit=5)

        return {
            "user_stats": user_stats,
            "billing_stats": billing_stats,
            "call_stats": call_stats,
            "recent_users": recent_users,
        }

with st.spinner("Loading dashboard..."):
    try:
        data = load_dashboard_data()
    except Exception as e:
        st.error(f"Failed to load dashboard data: {str(e)}")
        st.stop()

# KPI Cards Row
st.markdown("### Key Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    metric_card(
        "Total Users",
        format_number_abbrev(data["user_stats"]["total_users"]),
        f"+{data['user_stats']['new_users_7d']} (7d)",
        help_text="Total registered users"
    )

with col2:
    metric_card(
        "Active Subscriptions",
        format_number_abbrev(data["billing_stats"]["active_subs"]),
        delta=None,
        help_text="Non-trial, active subscriptions"
    )

with col3:
    metric_card(
        "Calls (30d)",
        format_number_abbrev(data["call_stats"]["total_calls"]),
        delta=None,
        help_text="Total calls in last 30 days"
    )

with col4:
    metric_card(
        "Revenue (30d)",
        format_currency(data["billing_stats"]["revenue_30d"]),
        delta=None,
        help_text="Total revenue from paid invoices"
    )

st.divider()

# Charts Row
st.markdown("### Trends")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    # Calls over time chart (mock data for now - will be implemented with real time series later)
    st.info("📊 Call trend chart - Coming soon with time series data")
    # TODO: Implement actual time series query in call_log_service
    # For now, showing a placeholder
    calls_df = pd.DataFrame({
        "date": pd.date_range(start=datetime.now() - timedelta(days=29), periods=30, freq="D"),
        "calls": [50 + i * 2 for i in range(30)]  # Mock data
    })
    line_chart(calls_df, "date", "calls", "Calls Over Time (30 days)", y_title="Number of Calls")

with chart_col2:
    # Revenue trend chart (mock data for now)
    st.info("💰 Revenue trend chart - Coming soon with time series data")
    # TODO: Implement actual revenue time series query
    revenue_df = pd.DataFrame({
        "date": pd.date_range(start=datetime.now() - timedelta(days=29), periods=30, freq="D"),
        "revenue": [800 + i * 10 for i in range(30)]  # Mock data
    })
    area_chart(revenue_df, "date", ["revenue"], "Revenue Trend (30 days)", stacked=False)

st.divider()

# Additional Metrics Row
st.markdown("### Call Statistics")
stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

with stat_col1:
    metric_card(
        "Answered by AI",
        format_number_abbrev(data["call_stats"]["answered_by_ai"]),
        help_text="Calls successfully handled by AI agent"
    )

with stat_col2:
    metric_card(
        "Forwarded",
        format_number_abbrev(data["call_stats"]["forwarded"]),
        help_text="Calls forwarded to human agents"
    )

with stat_col3:
    metric_card(
        "Missed",
        format_number_abbrev(data["call_stats"]["missed"]),
        delta_color="inverse",
        help_text="Calls that were not answered"
    )

with stat_col4:
    metric_card(
        "Avg Duration",
        f"{data['call_stats']['average_duration']:.0f}s",
        help_text="Average call duration in seconds"
    )

st.divider()

# Activity Feeds Row
st.markdown("### Recent Activity")
feed_col1, feed_col2 = st.columns(2)

with feed_col1:
    st.markdown("#### 🆕 New Signups")
    if data["recent_users"]:
        for user in data["recent_users"]:
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"**{user.email}**")
            with col_b:
                st.caption(humanize_datetime(user.created_at))
    else:
        st.info("No recent signups")

with feed_col2:
    st.markdown("#### ⚠️ Alerts")
    # TODO: Implement alert logic in billing_service
    # - Trial expirations (<24h)
    # - Failed payments
    # - Low credit balances (<$5)
    alert_count = 0

    if data["billing_stats"]["trial_subs"] > 0:
        st.warning(f"⏰ {data['billing_stats']['trial_subs']} trial subscriptions active")
        alert_count += 1

    if alert_count == 0:
        st.info("✅ No active alerts")

# Refresh button
st.divider()
if st.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# Footer with last updated time
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
