"""
Call monitoring panel component.

Real-time monitoring dashboard for active calls, DLQ status, and reconciliation.
"""

import streamlit as st
import asyncio
from datetime import datetime
from typing import Dict, Any

from database.connection import get_session
from services.call_monitoring_service import get_call_monitoring_service
from services.dlq_monitoring_service import get_dlq_monitoring_service
from services.reconciliation_service import get_reconciliation_service
from utils.formatters import format_phone, format_duration


def render_monitoring_panel(auto_refresh: bool = True, refresh_interval: int = 5):
    """Render the complete call monitoring panel.

    Displays:
    - Metrics row with key statistics
    - Active calls table (expandable)
    - DLQ status (expandable)
    - Reconciliation status (expandable)

    Args:
        auto_refresh: Enable auto-refresh
        refresh_interval: Refresh interval in seconds (default: 5)
    """
    # Create container for monitoring panel
    with st.container():
        # Header with refresh controls
        header_col1, header_col2 = st.columns([6, 2])

        with header_col1:
            st.markdown("### 📊 Real-Time Call Monitoring")

        with header_col2:
            # Manual refresh button
            if st.button("🔄 Refresh Now", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        # Auto-refresh toggle and status
        if auto_refresh:
            # Show last updated time
            if "monitoring_last_update" not in st.session_state:
                st.session_state.monitoring_last_update = datetime.utcnow()

            last_update = st.session_state.monitoring_last_update
            time_since_update = (datetime.utcnow() - last_update).seconds

            st.caption(
                f"🔄 Auto-refresh enabled (every {refresh_interval}s) • "
                f"Last updated: {time_since_update}s ago"
            )

            # Trigger rerun after interval
            if time_since_update >= refresh_interval:
                st.session_state.monitoring_last_update = datetime.utcnow()
                st.cache_data.clear()
                st.rerun()
        else:
            st.caption("ℹ️ Auto-refresh disabled")

        # Fetch data from services
        monitoring_data = asyncio.run(_fetch_monitoring_data())

        # Update last update time
        st.session_state.monitoring_last_update = datetime.utcnow()

        # Render metrics row
        _render_metrics_row(monitoring_data)

        st.divider()

        # Render expandable sections
        _render_active_calls_section(monitoring_data["active_calls"])
        _render_dlq_section(monitoring_data["dlq"])
        _render_reconciliation_section(monitoring_data["reconciliation"])


async def _fetch_monitoring_data() -> Dict[str, Any]:
    """Fetch all monitoring data from services.

    Returns:
        Dict with active_calls, dlq, and reconciliation data
    """
    call_service = get_call_monitoring_service()
    dlq_service = get_dlq_monitoring_service()
    recon_service = get_reconciliation_service()

    try:
        # Connect to Redis
        await call_service.redis_service.connect()

        # Fetch data from all services
        with get_session() as db_session:
            active_calls = await call_service.get_active_calls_with_business(db_session)
            health_summary = await call_service.get_health_summary()

        dlq_summary = await dlq_service.get_dlq_summary()
        recon_status = await recon_service.get_reconciliation_status()

        return {
            "active_calls": {
                "calls": active_calls,
                "count": len(active_calls),
                "health_summary": health_summary,
            },
            "dlq": dlq_summary,
            "reconciliation": recon_status,
        }

    except Exception as e:
        st.error(f"Error fetching monitoring data: {str(e)}")
        return {
            "active_calls": {"calls": [], "count": 0, "health_summary": {}},
            "dlq": {"depth": 0, "has_failures": False, "recent_messages": []},
            "reconciliation": {"last_run_at": None, "status": "error"},
        }
    finally:
        # Clean up
        await recon_service.close()


def _render_metrics_row(data: Dict[str, Any]):
    """Render metrics row with key statistics.

    Args:
        data: Monitoring data
    """
    col1, col2, col3, col4 = st.columns(4)

    # Active calls count
    with col1:
        active_count = data["active_calls"]["count"]
        health = data["active_calls"]["health_summary"]
        stale_count = health.get("stale", 0)

        delta_color = "normal"
        if stale_count > 0:
            delta_color = "inverse"

        st.metric(
            "Active Calls",
            active_count,
            delta=f"{stale_count} stale" if stale_count > 0 else None,
            delta_color=delta_color,
        )

    # DLQ depth
    with col2:
        dlq_depth = data["dlq"]["depth"]
        st.metric(
            "DLQ Depth",
            dlq_depth,
            delta="Issues!" if dlq_depth > 0 else None,
            delta_color="inverse" if dlq_depth > 0 else "normal",
        )

    # Last reconciliation
    with col3:
        recon = data["reconciliation"]
        recon_service = get_reconciliation_service()
        last_run_text = recon_service.format_last_run_time(recon.get("last_run_at"))

        st.metric(
            "Last Reconciliation",
            last_run_text,
            delta=f"{recon.get('queued_count', 0)} queued" if recon.get("queued_count", 0) > 0 else None,
        )

    # System health
    with col4:
        health = data["active_calls"]["health_summary"]
        stale_count = health.get("stale", 0)
        warning_count = health.get("warning", 0)

        if stale_count > 0:
            health_status = "🔴 Issues"
            health_delta = f"{stale_count} stale"
        elif warning_count > 0:
            health_status = "🟡 Warning"
            health_delta = f"{warning_count} slow"
        else:
            health_status = "🟢 Healthy"
            health_delta = None

        st.metric(
            "System Health",
            health_status,
            delta=health_delta,
        )


def _render_active_calls_section(data: Dict[str, Any]):
    """Render active calls section.

    Args:
        data: Active calls data
    """
    calls = data["calls"]
    count = data["count"]
    health = data["health_summary"]

    # Determine if should be expanded (if there are stale calls)
    stale_count = health.get("stale", 0)
    expanded = stale_count > 0 or count > 0

    with st.expander(f"🔴 Active Calls ({count} in progress)", expanded=expanded):
        if count == 0:
            st.info("No active calls at the moment")
            return

        # Render calls table
        st.markdown("**Current Active Calls**")

        for call in calls:
            # Health indicator
            health_icon = {
                "healthy": "🟢",
                "warning": "🟡",
                "stale": "🔴",
            }.get(call["health_status"], "⚪")

            # Format heartbeat age
            heartbeat_text = "No heartbeat"
            if call["heartbeat_age_seconds"] is not None:
                age = call["heartbeat_age_seconds"]
                if age < 60:
                    heartbeat_text = f"{age}s ago"
                elif age < 3600:
                    heartbeat_text = f"{age // 60}m {age % 60}s ago"
                else:
                    heartbeat_text = f"{age // 3600}h {(age % 3600) // 60}m ago"

            # Call row
            col1, col2, col3, col4, col5 = st.columns([1, 3, 3, 2, 2])

            with col1:
                st.markdown(f"### {health_icon}")

            with col2:
                st.markdown(f"**{format_phone(call['from_phone'])}**")
                st.caption(call["business_name"])

            with col3:
                st.markdown(f"Duration: **{format_duration(call['duration_seconds'])}**")
                st.caption(f"Started: {call['start_time'].strftime('%H:%M:%S')}")

            with col4:
                st.markdown(f"Heartbeat:")
                st.caption(heartbeat_text)

            with col5:
                st.caption(f"SID: {call['call_sid'][:10]}...")

            # Warning for stale calls
            if call["health_status"] == "stale":
                st.warning(
                    f"⚠️ **Stale call detected!** No heartbeat for {heartbeat_text}. Call may have crashed.",
                    icon="⚠️"
                )

            st.divider()

        # Show health summary
        st.caption(
            f"Health: {health.get('healthy', 0)} healthy • "
            f"{health.get('warning', 0)} warning • "
            f"{health.get('stale', 0)} stale"
        )


def _render_dlq_section(data: Dict[str, Any]):
    """Render DLQ status section.

    Args:
        data: DLQ data
    """
    depth = data["depth"]
    messages = data["recent_messages"]
    has_failures = data["has_failures"]

    # Expand if there are failures
    with st.expander(f"⚠️ DLQ Status (Depth: {depth})", expanded=has_failures):
        if not has_failures:
            st.success("✅ No failed operations in queue")
            return

        st.warning(f"**{depth} failed operations pending retry**")

        # Render recent failures
        if messages:
            st.markdown("**Recent Failed Operations:**")

            for msg in messages[:10]:  # Show up to 10
                col1, col2, col3 = st.columns([2, 3, 2])

                with col1:
                    st.markdown(f"**Call SID:**")
                    st.caption(msg["call_sid"][:15] + "...")

                with col2:
                    st.markdown(f"**Error:**")
                    st.caption(msg["error_message"])

                with col3:
                    st.markdown(f"**Retry:**")
                    retry_status = msg["retry_status"]
                    retry_in = msg.get("retry_in", "Unknown")

                    if msg["is_final_failure"]:
                        st.error(f"{retry_status} - FAILED")
                    else:
                        st.info(f"{retry_status} - in {retry_in}")

                # Show full error in expander
                with st.expander(f"View full error for {msg['call_sid'][:10]}"):
                    st.code(msg["full_error"], language="text")

                st.divider()


def _render_reconciliation_section(data: Dict[str, Any]):
    """Render reconciliation status section.

    Args:
        data: Reconciliation data
    """
    last_run_at = data.get("last_run_at")
    status = data.get("status", "unknown")
    missing_count = data.get("missing_count", 0)
    queued_count = data.get("queued_count", 0)
    error = data.get("error")

    # Expand if there's an error or missing notifications
    expanded = status == "error" or queued_count > 0

    with st.expander("🔄 Reconciliation Status", expanded=expanded):
        # Last run info
        recon_service = get_reconciliation_service()
        last_run_text = recon_service.format_last_run_time(last_run_at)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Last Run", last_run_text)

        with col2:
            st.metric("Missing Found", missing_count)

        with col3:
            st.metric("Queued", queued_count)

        # Status message
        if status == "success":
            if queued_count > 0:
                st.info(f"✅ Last run successful. Queued {queued_count} missing notifications.")
            else:
                st.success("✅ Last run successful. No missing notifications found.")
        elif status == "error":
            st.error(f"❌ Last run failed: {error}")
        else:
            st.warning("⚠️ Reconciliation status unknown")

        st.divider()

        # Manual trigger button
        st.markdown("**Manual Control:**")

        if st.button("🔄 Trigger Reconciliation Now", type="primary", use_container_width=True):
            with st.spinner("Triggering reconciliation job..."):
                result = asyncio.run(_trigger_reconciliation())

                if result["success"]:
                    st.success(f"✅ {result['message']}")
                    st.caption(f"Task ID: {result.get('task_id')}")
                    # Wait a moment then rerun to show updated status
                    asyncio.run(asyncio.sleep(2))
                    st.rerun()
                else:
                    st.error(f"❌ {result['message']}")
                    if result.get("error"):
                        st.caption(f"Error: {result['error']}")


async def _trigger_reconciliation() -> Dict[str, Any]:
    """Trigger reconciliation job.

    Returns:
        Dict with success status and message
    """
    recon_service = get_reconciliation_service()
    try:
        result = await recon_service.trigger_reconciliation()
        return result
    finally:
        await recon_service.close()
