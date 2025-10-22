"""
System - Health checks and database statistics
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from config.auth import require_auth
from database.connection import get_session
from services.system_service import (
    check_database_health,
    get_table_row_counts,
    get_growth_stats,
    get_data_quality_metrics,
    get_system_info,
    generate_system_report
)
import logging

logger = logging.getLogger(__name__)

# Auth check
if not require_auth():
    st.stop()

st.title("🔧 System")
st.markdown("Health checks and database statistics")

# Refresh button at the top
col1, col2 = st.columns([8, 2])
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Health Checks Section
st.markdown("### Health Checks")

health_col1, health_col2 = st.columns(2)

with health_col1:
    st.markdown("#### Database")
    try:
        with get_session() as session:
            db_health = check_database_health(session)

        if db_health["status"] == "connected":
            st.success(f"✅ Connected (Response time: {db_health['response_time_ms']}ms)")
        else:
            st.error(f"❌ Error: {db_health['error']}")

    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        st.error(f"❌ Failed to check database: {str(e)}")

with health_col2:
    st.markdown("#### External Services")
    # Note: Don't actually call external APIs, just check local sync status
    st.info("⚠️ Not configured - Check Stripe dashboard for external service status")

st.divider()

# Database Statistics
st.markdown("### Database Statistics")

try:
    with get_session() as session:
        counts = get_table_row_counts(session)

    # Table row counts
    st.markdown("#### Table Row Counts")

    count_col1, count_col2, count_col3 = st.columns(3)

    with count_col1:
        st.metric("Total Users", f"{counts.get('users_total', 0):,}")
        st.caption(f"Active: {counts.get('users_active', 0):,}")

        st.metric("Businesses", f"{counts.get('businesses', 0):,}")
        st.metric("AI Agents", f"{counts.get('ai_agents', 0):,}")

    with count_col2:
        st.metric("Call Logs (Total)", f"{counts.get('call_logs_total', 0):,}")
        st.caption(f"Last 30 days: {counts.get('call_logs_30d', 0):,}")

        st.metric("Appointments (Total)", f"{counts.get('appointments_total', 0):,}")
        st.caption(f"Upcoming: {counts.get('appointments_upcoming', 0):,}")
        st.caption(f"Past: {counts.get('appointments_past', 0):,}")

    with count_col3:
        st.metric("Active Subscriptions", f"{counts.get('subscriptions_active', 0):,}")
        st.caption(f"Trial: {counts.get('subscriptions_trial', 0):,}")
        st.caption(f"Cancelled: {counts.get('subscriptions_cancelled', 0):,}")

        st.metric("Credit Transactions", f"{counts.get('credit_transactions', 0):,}")
        st.metric("Promotion Codes", f"{counts.get('promotion_codes', 0):,}")

except Exception as e:
    logger.error(f"Failed to load table counts: {e}", exc_info=True)
    st.error(f"❌ Failed to load table counts: {str(e)}")

st.divider()

# Growth Trends
st.markdown("### Growth Trends")

try:
    with get_session() as session:
        growth = get_growth_stats(session)

    growth_col1, growth_col2, growth_col3 = st.columns(3)

    with growth_col1:
        st.markdown("#### New Users")
        st.metric("Today", f"{growth.get('new_users_today', 0):,}")
        st.metric("Last 7 days", f"{growth.get('new_users_7d', 0):,}")
        st.metric("Last 30 days", f"{growth.get('new_users_30d', 0):,}")

    with growth_col2:
        st.markdown("#### New Businesses")
        st.metric("Today", f"{growth.get('new_businesses_today', 0):,}")
        st.metric("Last 7 days", f"{growth.get('new_businesses_7d', 0):,}")
        st.metric("Last 30 days", f"{growth.get('new_businesses_30d', 0):,}")

    with growth_col3:
        st.markdown("#### New Calls")
        st.metric("Today", f"{growth.get('new_calls_today', 0):,}")
        st.metric("Last 7 days", f"{growth.get('new_calls_7d', 0):,}")
        st.caption("(30-day metric not available)")

except Exception as e:
    logger.error(f"Failed to load growth stats: {e}", exc_info=True)
    st.error(f"❌ Failed to load growth stats: {str(e)}")

st.divider()

# Data Quality Metrics
st.markdown("### Data Quality Metrics")

try:
    with get_session() as session:
        quality = get_data_quality_metrics(session)

    quality_col1, quality_col2, quality_col3 = st.columns(3)

    with quality_col1:
        st.markdown("#### Users with Businesses")
        st.metric(
            "Count",
            f"{quality.get('users_with_businesses_count', 0):,}",
            delta=f"{quality.get('users_with_businesses_pct', 0)}%"
        )

    with quality_col2:
        st.markdown("#### Users with Active Agents")
        st.metric(
            "Count",
            f"{quality.get('users_with_agents_count', 0):,}",
            delta=f"{quality.get('users_with_agents_pct', 0)}%"
        )

    with quality_col3:
        st.markdown("#### Users with Subscriptions")
        st.metric(
            "Count",
            f"{quality.get('users_with_subscriptions_count', 0):,}",
            delta=f"{quality.get('users_with_subscriptions_pct', 0)}%"
        )

except Exception as e:
    logger.error(f"Failed to load data quality metrics: {e}", exc_info=True)
    st.error(f"❌ Failed to load data quality metrics: {str(e)}")

st.divider()

# System Information
st.markdown("### System Information")

try:
    sys_info = get_system_info()

    info_col1, info_col2 = st.columns(2)

    with info_col1:
        st.markdown(f"**Python Version:** {sys_info.get('python_version', 'N/A')}")
        st.markdown(f"**Streamlit Version:** {sys_info.get('streamlit_version', 'N/A')}")
        st.markdown(f"**Platform:** {sys_info.get('platform', 'N/A')} {sys_info.get('platform_version', '')}")

    with info_col2:
        st.markdown(f"**Database:** {sys_info.get('database_url', 'N/A')}")
        st.markdown(f"**Environment:** {sys_info.get('environment', 'unknown')}")
        st.markdown(f"**Server Time:** {sys_info.get('current_time', 'N/A')}")

except Exception as e:
    logger.error(f"Failed to load system info: {e}", exc_info=True)
    st.error(f"❌ Failed to load system info: {str(e)}")

st.divider()

# Manual Actions
st.markdown("### Manual Actions")

action_col1, action_col2, action_col3 = st.columns(3)

with action_col1:
    if st.button("🗑️ Clear All Cache", use_container_width=True):
        try:
            st.cache_data.clear()
            st.success("✓ Cache cleared successfully")
            st.rerun()
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}", exc_info=True)
            st.error(f"❌ Failed to clear cache: {str(e)}")

with action_col2:
    if st.button("🔍 Test Database", use_container_width=True):
        try:
            with st.spinner("Testing database connection..."):
                with get_session() as session:
                    db_health = check_database_health(session)

                if db_health["status"] == "connected":
                    st.success(f"✓ Database connected ({db_health['response_time_ms']}ms)")
                else:
                    st.error(f"❌ Database error: {db_health['error']}")

        except Exception as e:
            logger.error(f"Database test failed: {e}", exc_info=True)
            st.error(f"❌ Database test failed: {str(e)}")

with action_col3:
    if st.button("📊 Generate Report", use_container_width=True):
        try:
            with st.spinner("Generating system report..."):
                with get_session() as session:
                    report = generate_system_report(session)

                # Convert report to CSV
                report_df = pd.DataFrame([
                    {"Metric": "Timestamp", "Value": report["timestamp"]},
                    {"Metric": "Database Status", "Value": report["database_health"]["status"]},
                    {"Metric": "Database Response Time (ms)", "Value": report["database_health"]["response_time_ms"]},
                    {"Metric": "---", "Value": "---"},
                    {"Metric": "Total Users", "Value": report["table_counts"]["users_total"]},
                    {"Metric": "Active Users", "Value": report["table_counts"]["users_active"]},
                    {"Metric": "Businesses", "Value": report["table_counts"]["businesses"]},
                    {"Metric": "AI Agents", "Value": report["table_counts"]["ai_agents"]},
                    {"Metric": "Call Logs (Total)", "Value": report["table_counts"]["call_logs_total"]},
                    {"Metric": "Call Logs (30d)", "Value": report["table_counts"]["call_logs_30d"]},
                    {"Metric": "Appointments", "Value": report["table_counts"]["appointments_total"]},
                    {"Metric": "Active Subscriptions", "Value": report["table_counts"]["subscriptions_active"]},
                    {"Metric": "---", "Value": "---"},
                    {"Metric": "New Users (Today)", "Value": report["growth_stats"]["new_users_today"]},
                    {"Metric": "New Users (7d)", "Value": report["growth_stats"]["new_users_7d"]},
                    {"Metric": "New Users (30d)", "Value": report["growth_stats"]["new_users_30d"]},
                    {"Metric": "New Businesses (Today)", "Value": report["growth_stats"]["new_businesses_today"]},
                    {"Metric": "New Businesses (7d)", "Value": report["growth_stats"]["new_businesses_7d"]},
                    {"Metric": "New Businesses (30d)", "Value": report["growth_stats"]["new_businesses_30d"]},
                    {"Metric": "New Calls (Today)", "Value": report["growth_stats"]["new_calls_today"]},
                    {"Metric": "New Calls (7d)", "Value": report["growth_stats"]["new_calls_7d"]},
                    {"Metric": "---", "Value": "---"},
                    {"Metric": "Users with Businesses (%)", "Value": report["data_quality"]["users_with_businesses_pct"]},
                    {"Metric": "Users with Agents (%)", "Value": report["data_quality"]["users_with_agents_pct"]},
                    {"Metric": "Users with Subscriptions (%)", "Value": report["data_quality"]["users_with_subscriptions_pct"]},
                ])

                csv = report_df.to_csv(index=False)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

                st.download_button(
                    label="📥 Download System Report CSV",
                    data=csv,
                    file_name=f"system_report_{timestamp}.csv",
                    mime="text/csv",
                    key='download-report-csv',
                    use_container_width=True
                )

                st.success("✓ System report generated")

        except Exception as e:
            logger.error(f"Failed to generate report: {e}", exc_info=True)
            st.error(f"❌ Failed to generate report: {str(e)}")

# Last updated timestamp
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
