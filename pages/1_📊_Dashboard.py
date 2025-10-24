"""
Dashboard - System overview with KPIs and charts
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from config.auth import require_auth
from database.connection import get_session
from services.user_service import get_user_stats, get_recent_signups
from services.billing_service import get_billing_stats, get_revenue_trend_data
from services.call_log_service import get_call_stats, get_call_trend_data
from services.agent_service import get_agent_stats
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
with col1:
    st.markdown("")  # Spacer
with col2:
    auto_refresh = st.checkbox("Auto-refresh (60s)", value=False)

# Load data
@st.cache_data(ttl=60)
def load_dashboard_data():
    """Load all dashboard data with caching"""
    with get_session() as session:
        user_stats = get_user_stats(session)
        billing_stats = get_billing_stats(session, date_range=30)
        call_stats = get_call_stats(session, date_range=30)
        agent_stats = get_agent_stats(session)
        recent_users = get_recent_signups(session, limit=5)
        call_trend = get_call_trend_data(session, days=30)
        revenue_trend = get_revenue_trend_data(session, days=30)

        return {
            "user_stats": user_stats,
            "billing_stats": billing_stats,
            "call_stats": call_stats,
            "agent_stats": agent_stats,
            "recent_users": recent_users,
            "call_trend": call_trend,
            "revenue_trend": revenue_trend,
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
    # Calls over time chart with real data
    line_chart(data["call_trend"], "date", "calls", "Calls Over Time (30 days)", y_title="Number of Calls")

with chart_col2:
    # Revenue trend chart with real data
    area_chart(data["revenue_trend"], "date", ["revenue"], "Revenue Trend (30 days)", stacked=False)

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

# Agent Metrics Row
st.markdown("### AI Agent Configuration")
agent_col1, agent_col2, agent_col3, agent_col4 = st.columns(4)

with agent_col1:
    metric_card(
        "Configured Agents",
        format_number_abbrev(data["agent_stats"]["total_agents"]),
        help_text="Total AI agents configured"
    )

with agent_col2:
    metric_card(
        "With FAQs",
        format_number_abbrev(data["agent_stats"]["agents_with_faq"]),
        help_text="Agents with FAQ items configured"
    )

with agent_col3:
    metric_card(
        "Avg FAQ Count",
        f"{data['agent_stats']['avg_faq_count']:.1f}",
        help_text="Average number of FAQs per agent"
    )

with agent_col4:
    metric_card(
        "Call Transfer Enabled",
        format_number_abbrev(data["agent_stats"]["agents_with_call_transfer"]),
        help_text="Agents with call transfer feature enabled"
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

# Auto-refresh logic
if auto_refresh:
    import time
    countdown_placeholder = st.empty()

    for remaining in range(60, 0, -1):
        countdown_placeholder.info(f"🔄 Refreshing in {remaining} seconds...")
        time.sleep(1)

    # Clear cache and rerun
    st.cache_data.clear()
    st.rerun()

# Footer with last updated time
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
