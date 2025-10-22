"""
Card components for metrics and information display.
"""
import streamlit as st
from typing import Optional


def metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    delta_color: str = "normal",
    help_text: Optional[str] = None
):
    """
    Display a metric card with optional change indicator.

    Args:
        label: Metric label (e.g., "Total Users")
        value: Main metric value (e.g., "1,247")
        delta: Change indicator (e.g., "+12 (7d)")
        delta_color: "normal", "inverse", or "off"
        help_text: Optional tooltip text

    Usage:
        metric_card("Total Users", "1,247", "+12 (7d)")
    """
    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text
    )


def stat_card(title: str, value: str, icon: str = "📊", description: Optional[str] = None):
    """
    Display a larger featured statistic card.

    Args:
        title: Card title
        value: Large display value
        icon: Emoji icon
        description: Optional description text

    Usage:
        stat_card("Revenue This Month", "$24,567", "💰", "Up 15% from last month")
    """
    st.markdown(
        f"""
        <div style="padding: 1.5rem; background: white; border-radius: 0.5rem;
                    border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <span style="font-size: 1.5rem;">{icon}</span>
                <h3 style="margin: 0; color: #1f2937; font-size: 0.875rem; font-weight: 600;">
                    {title}
                </h3>
            </div>
            <div style="font-size: 2rem; font-weight: 700; color: #111827; margin-bottom: 0.25rem;">
                {value}
            </div>
            {f'<div style="color: #6b7280; font-size: 0.875rem;">{description}</div>' if description else ''}
        </div>
        """,
        unsafe_allow_html=True
    )


def info_card(title: str, content: str, icon: str = "ℹ️", color: str = "blue"):
    """
    Display an informational card.

    Args:
        title: Card title
        content: Main content text
        icon: Emoji icon
        color: "blue", "green", "yellow", "red"

    Usage:
        info_card("Note", "This is read-only", "⚠️", "yellow")
    """
    color_map = {
        "blue": {"bg": "#eff6ff", "border": "#3b82f6", "text": "#1e40af"},
        "green": {"bg": "#f0fdf4", "border": "#22c55e", "text": "#15803d"},
        "yellow": {"bg": "#fefce8", "border": "#eab308", "text": "#a16207"},
        "red": {"bg": "#fef2f2", "border": "#ef4444", "text": "#b91c1c"},
    }

    colors = color_map.get(color, color_map["blue"])

    st.markdown(
        f"""
        <div style="padding: 1rem; background: {colors['bg']}; border-radius: 0.5rem;
                    border-left: 4px solid {colors['border']}; margin: 1rem 0;">
            <div style="display: flex; align-items: flex-start; gap: 0.75rem;">
                <span style="font-size: 1.25rem;">{icon}</span>
                <div>
                    <div style="font-weight: 600; color: {colors['text']}; margin-bottom: 0.25rem;">
                        {title}
                    </div>
                    <div style="color: {colors['text']}; font-size: 0.875rem;">
                        {content}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def alert_card(message: str, type: str = "info", dismissible: bool = False):
    """
    Display an alert message.

    Args:
        message: Alert message
        type: "info", "success", "warning", "error"
        dismissible: Show close button

    Usage:
        alert_card("Database connected successfully", "success")
    """
    if type == "info":
        st.info(message)
    elif type == "success":
        st.success(message)
    elif type == "warning":
        st.warning(message)
    elif type == "error":
        st.error(message)
