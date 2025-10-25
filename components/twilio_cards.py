"""
Twilio-specific card components for phone number pool visualization.
"""
import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


def pool_status_card(pool_status: Dict[str, int]):
    """
    Display overall pool status card with key metrics.

    Args:
        pool_status: Dict from twilio_service.get_pool_status()
    """
    total = pool_status.get("total_numbers", 0)
    available = pool_status.get("available_numbers", 0)
    assigned = pool_status.get("assigned_numbers", 0)
    error = pool_status.get("error_numbers", 0)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Active",
            total,
            help="Total active phone numbers in the pool"
        )

    with col2:
        st.metric(
            "Available",
            available,
            delta=f"{(available/total*100) if total > 0 else 0:.0f}% of total",
            help="Numbers ready for assignment"
        )

    with col3:
        st.metric(
            "Assigned",
            assigned,
            delta=f"{(assigned/total*100) if total > 0 else 0:.0f}% of total",
            help="Numbers currently in use by businesses"
        )

    with col4:
        if error > 0:
            st.metric(
                "Errors",
                error,
                delta="Attention needed",
                delta_color="inverse",
                help="Numbers with sync or configuration errors"
            )
        else:
            st.metric(
                "Errors",
                error,
                delta="All healthy",
                delta_color="normal",
                help="Numbers with sync or configuration errors"
            )


def pool_capacity_gauge(capacity_pct: float, current: int, maximum: int):
    """
    Display pool capacity as a visual gauge.

    Args:
        capacity_pct: Percentage of pool capacity used
        current: Current number count
        maximum: Maximum pool size
    """
    # Determine color based on capacity
    if capacity_pct >= 90:
        color = "🔴"
        status = "CRITICAL"
        bg_color = "#fee2e2"
        border_color = "#ef4444"
    elif capacity_pct >= 75:
        color = "🟡"
        status = "WARNING"
        bg_color = "#fef3c7"
        border_color = "#f59e0b"
    else:
        color = "🟢"
        status = "HEALTHY"
        bg_color = "#d1fae5"
        border_color = "#10b981"

    st.markdown(
        f"""
        <div style="padding: 1.5rem; background: {bg_color}; border-radius: 0.5rem;
                    border-left: 4px solid {border_color}; margin: 1rem 0;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.875rem; font-weight: 600; color: #374151; margin-bottom: 0.5rem;">
                        Pool Capacity
                    </div>
                    <div style="font-size: 2rem; font-weight: 700; color: #111827;">
                        {capacity_pct:.1f}%
                    </div>
                    <div style="font-size: 0.875rem; color: #6b7280; margin-top: 0.25rem;">
                        {current} of {maximum} numbers
                    </div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 3rem;">{color}</div>
                    <div style="font-size: 0.75rem; font-weight: 600; color: #374151;">
                        {status}
                    </div>
                </div>
            </div>
            <div style="margin-top: 1rem; background: #ffffff; border-radius: 9999px; height: 8px; overflow: hidden;">
                <div style="background: {border_color}; height: 100%; width: {min(capacity_pct, 100)}%;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def sync_status_indicator(sync_health: Dict[str, Any]):
    """
    Display Twilio sync health status.

    Args:
        sync_health: Dict from twilio_service.get_sync_health()
    """
    total_errors = sync_health.get("total_sync_errors", 0)
    last_success = sync_health.get("last_successful_sync")
    not_synced_24h = sync_health.get("numbers_not_synced_24h", 0)

    # Determine overall health status
    if total_errors > 0 or not_synced_24h > 5:
        icon = "⚠️"
        status = "NEEDS ATTENTION"
        color = "#f59e0b"
        bg_color = "#fef3c7"
    elif not_synced_24h > 0:
        icon = "ℹ️"
        status = "MONITORING"
        color = "#3b82f6"
        bg_color = "#dbeafe"
    else:
        icon = "✅"
        status = "HEALTHY"
        color = "#10b981"
        bg_color = "#d1fae5"

    # Format last sync time
    if last_success:
        time_diff = datetime.now(timezone.utc) - last_success
        if time_diff.total_seconds() < 3600:
            time_str = f"{int(time_diff.total_seconds() / 60)} minutes ago"
        elif time_diff.total_seconds() < 86400:
            time_str = f"{int(time_diff.total_seconds() / 3600)} hours ago"
        else:
            time_str = last_success.strftime("%Y-%m-%d %H:%M UTC")
    else:
        time_str = "Never"

    # Use Streamlit native components instead of HTML
    st.markdown(f"**Sync Status:** {icon} {status}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Last Sync", time_str)
    with col2:
        st.metric("Sync Errors", total_errors, delta="Issues" if total_errors > 0 else "None", delta_color="inverse" if total_errors > 0 else "off")
    with col3:
        st.metric("Not Synced 24h", not_synced_24h, delta="Needs attention" if not_synced_24h > 5 else ("Monitoring" if not_synced_24h > 0 else "Good"), delta_color="inverse" if not_synced_24h > 0 else "off")


def recycling_queue_card(recycling_data: Dict[str, List[Dict[str, Any]]]):
    """
    Display recycling queue status card.

    Args:
        recycling_data: Dict from twilio_service.get_recycling_candidates()
    """
    immediate = recycling_data.get("immediate", [])
    grace_period = recycling_data.get("grace_period", [])

    total_candidates = len(immediate) + len(grace_period)

    if total_candidates == 0:
        icon = "✅"
        status = "No recycling needed"
    elif len(immediate) > 0:
        icon = "🔴"
        status = f"{len(immediate)} number(s) need immediate recycling"
    else:
        icon = "🟡"
        status = f"{len(grace_period)} number(s) in grace period"

    # Use Streamlit native components instead of HTML
    st.markdown(f"**Recycling Queue:** {icon} {status}")

    if total_candidates > 0:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Immediate", len(immediate), delta="Needs action now" if len(immediate) > 0 else None, delta_color="inverse")
        with col2:
            st.metric("Grace Period", len(grace_period), delta="30+ days past due" if len(grace_period) > 0 else None, delta_color="inverse")


def activity_timeline_card(history: Dict[str, Any]):
    """
    Display recent pool activity timeline.

    Args:
        history: Dict from twilio_service.get_pool_history_metrics()
    """
    purchases = history.get("purchases_by_day", {})
    assignments = history.get("assignments_by_day", {})
    releases = history.get("releases_by_day", {})

    total_purchases = sum(purchases.values())
    total_assignments = sum(assignments.values())
    total_releases = sum(releases.values())

    period = history.get("period_days", 30)

    st.markdown(f"**Activity Summary (Last {period} Days)**")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Purchased",
            total_purchases,
            help=f"New numbers purchased in last {period} days"
        )

    with col2:
        st.metric(
            "Assigned",
            total_assignments,
            help=f"Numbers assigned in last {period} days"
        )

    with col3:
        st.metric(
            "Released",
            total_releases,
            help=f"Numbers released in last {period} days"
        )

    # Net change
    net_change = total_purchases - total_releases
    if net_change > 0:
        st.caption(f"📈 Net pool growth: +{net_change} numbers")
    elif net_change < 0:
        st.caption(f"📉 Net pool reduction: {net_change} numbers")
    else:
        st.caption("➡️ Pool size stable")


def configuration_info_card(config: Dict[str, int]):
    """
    Display pool configuration settings.

    Args:
        config: Dict with configuration values
            - max_pool_size: Maximum pool size
            - purchase_batch_size: How many to buy at once
            - max_unused: Maximum unused available numbers
    """
    st.markdown("**Pool Configuration**")

    st.markdown(
        f"""
        <div style="padding: 1rem; background: #f9fafb; border-radius: 0.5rem;
                    border: 1px solid #e5e7eb; margin: 0.5rem 0;">
            <div style="margin-bottom: 0.75rem;">
                <div style="font-size: 0.875rem; color: #6b7280;">Max Pool Size</div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #111827;">
                    {config.get('max_pool_size', 'N/A')} numbers
                </div>
            </div>
            <div style="margin-bottom: 0.75rem;">
                <div style="font-size: 0.875rem; color: #6b7280;">Purchase Batch Size</div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #111827;">
                    {config.get('purchase_batch_size', 'N/A')} numbers
                </div>
            </div>
            <div>
                <div style="font-size: 0.875rem; color: #6b7280;">Max Unused Available</div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #111827;">
                    {config.get('max_unused', 'N/A')} numbers
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def status_badge(status: str) -> str:
    """
    Generate HTML for a status badge.

    Args:
        status: Phone number status (available, assigned, released, error)

    Returns:
        HTML string for status badge
    """
    status_colors = {
        "available": {"bg": "#d1fae5", "text": "#065f46", "label": "Available"},
        "assigned": {"bg": "#dbeafe", "text": "#1e40af", "label": "Assigned"},
        "released": {"bg": "#e5e7eb", "text": "#374151", "label": "Released"},
        "error": {"bg": "#fee2e2", "text": "#991b1b", "label": "Error"},
    }

    colors = status_colors.get(status.lower(), {"bg": "#f3f4f6", "text": "#1f2937", "label": status.title()})

    return f"""
    <span style="display: inline-block; padding: 0.25rem 0.75rem; background: {colors['bg']};
                 color: {colors['text']}; border-radius: 9999px; font-size: 0.875rem;
                 font-weight: 600;">
        {colors['label']}
    </span>
    """
