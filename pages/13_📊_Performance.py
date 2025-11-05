"""
Performance monitoring page for AICallGO services.

Displays CPU and memory usage for all Kubernetes deployments with:
- Real-time metrics with 30-second auto-refresh
- Time-series charts showing usage trends
- Per-pod breakdown for multi-replica deployments
- Health indicators based on resource limits
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List
import logging

from services.k8s_service import list_deployments
from services.k8s_metrics_service import (
    get_deployment_metrics,
    format_cpu,
    format_memory
)
from config.settings import settings

logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Performance | AICallGO Admin",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if "selected_service" not in st.session_state:
    st.session_state.selected_service = None
if "metrics_history" not in st.session_state:
    st.session_state.metrics_history = {}
if "last_metrics_update" not in st.session_state:
    st.session_state.last_metrics_update = datetime.utcnow()


def add_metrics_to_history(service_name: str, metrics: Dict):
    """Add current metrics to history for time-series charts."""
    if service_name not in st.session_state.metrics_history:
        st.session_state.metrics_history[service_name] = {
            "timestamps": [],
            "cpu": [],
            "memory": []
        }

    history = st.session_state.metrics_history[service_name]

    # Add current data
    history["timestamps"].append(datetime.utcnow())
    history["cpu"].append(metrics["total_cpu_cores"])
    history["memory"].append(metrics["total_memory_gb"])

    # Keep only last 20 data points (10 minutes at 30s intervals)
    if len(history["timestamps"]) > 20:
        history["timestamps"] = history["timestamps"][-20:]
        history["cpu"] = history["cpu"][-20:]
        history["memory"] = history["memory"][-20:]


def create_time_series_chart(
    timestamps: List[datetime],
    values: List[float],
    title: str,
    y_label: str,
    color: str = "#00B4D8"
) -> go.Figure:
    """Create a time-series line chart using Plotly."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=values,
        mode='lines+markers',
        line=dict(color=color, width=2),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1)'
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title=y_label,
        height=300,
        margin=dict(l=50, r=50, t=50, b=50),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            showgrid=True
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            showgrid=True
        )
    )

    return fig


def get_service_health(deployment_name: str) -> str:
    """Get health status emoji for a service (cached)."""
    try:
        metrics = get_deployment_metrics(deployment_name, settings.K8S_NAMESPACE)

        # Check if any pod is critical
        if any(pod["status"] == "🔴" for pod in metrics["pods"]):
            return "🔴"

        # Check if any pod is warning
        if any(pod["status"] == "🟡" for pod in metrics["pods"]):
            return "🟡"

        # Check overall usage
        cpu_usage = metrics.get("cpu_usage_percent", 0)
        mem_usage = metrics.get("memory_usage_percent", 0)

        if cpu_usage > 90 or mem_usage > 90:
            return "🔴"
        elif cpu_usage > 70 or mem_usage > 70:
            return "🟡"
        else:
            return "🟢"
    except Exception:
        return "⚪"


def render_service_list(deployments: List[Dict]):
    """Render the service list sidebar."""
    st.markdown("### Services")
    st.caption(f"Total: {len(deployments)}")

    for deployment in deployments:
        name = deployment["name"]
        replicas = deployment["replicas"]
        ready = deployment["ready_replicas"]

        # Get health status
        health_emoji = get_service_health(name)

        # Determine button type
        is_selected = st.session_state.selected_service == name
        button_type = "primary" if is_selected else "secondary"

        # Display service button
        button_label = f"{health_emoji} {name}\n({ready}/{replicas})"
        if st.button(
            button_label,
            key=f"service_{name}",
            type=button_type,
            use_container_width=True
        ):
            st.session_state.selected_service = name
            st.rerun()


def render_metrics_panel(service_name: str):
    """Render the metrics panel for selected service."""
    st.markdown(f"## {service_name}")

    # Fetch metrics
    try:
        metrics = get_deployment_metrics(service_name, settings.K8S_NAMESPACE)
    except Exception as e:
        st.error(f"Error fetching metrics: {e}")
        logger.error(f"Error fetching metrics for {service_name}: {e}")
        return

    # Add to history
    add_metrics_to_history(service_name, metrics)

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        cpu_delta = None
        if len(st.session_state.metrics_history[service_name]["cpu"]) > 1:
            cpu_delta = (
                metrics["total_cpu_cores"] -
                st.session_state.metrics_history[service_name]["cpu"][-2]
            )

        st.metric(
            label="Total CPU",
            value=f"{format_cpu(metrics['total_cpu_cores'])} cores",
            delta=f"{cpu_delta:+.2f}" if cpu_delta else None
        )
        if metrics.get("cpu_limit_cores"):
            st.caption(f"Limit: {format_cpu(metrics['cpu_limit_cores'])} cores")
            if metrics.get("cpu_usage_percent"):
                st.caption(f"Usage: {metrics['cpu_usage_percent']}%")

    with col2:
        mem_delta = None
        if len(st.session_state.metrics_history[service_name]["memory"]) > 1:
            mem_delta = (
                metrics["total_memory_gb"] -
                st.session_state.metrics_history[service_name]["memory"][-2]
            )

        st.metric(
            label="Total Memory",
            value=f"{format_memory(metrics['total_memory_gb'])}",
            delta=f"{mem_delta:+.2f}Gi" if mem_delta else None
        )
        if metrics.get("memory_limit_gb"):
            st.caption(f"Limit: {format_memory(metrics['memory_limit_gb'])}")
            if metrics.get("memory_usage_percent"):
                st.caption(f"Usage: {metrics['memory_usage_percent']}%")

    with col3:
        st.metric(
            label="Avg CPU/Pod",
            value=f"{format_cpu(metrics['avg_cpu_cores'])} cores"
        )
        st.caption(f"Pods: {metrics['pod_count']}")

    with col4:
        st.metric(
            label="Avg Memory/Pod",
            value=f"{format_memory(metrics['avg_memory_gb'])}"
        )
        st.caption(f"Pods: {metrics['pod_count']}")

    st.divider()

    # Time-series charts
    history = st.session_state.metrics_history[service_name]

    if len(history["timestamps"]) > 1:
        col1, col2 = st.columns(2)

        with col1:
            cpu_chart = create_time_series_chart(
                history["timestamps"],
                history["cpu"],
                "CPU Usage Over Time",
                "Cores",
                color="#00B4D8"
            )
            st.plotly_chart(cpu_chart, use_container_width=True)

        with col2:
            mem_chart = create_time_series_chart(
                history["timestamps"],
                history["memory"],
                "Memory Usage Over Time",
                "GB",
                color="#FF6B6B"
            )
            st.plotly_chart(mem_chart, use_container_width=True)
    else:
        st.info("⏳ Collecting data... Time-series charts will appear after 30 seconds")

    st.divider()

    # Per-pod breakdown
    with st.expander("Per-Pod Breakdown", expanded=True):
        if metrics["pods"]:
            # Create DataFrame
            df = pd.DataFrame(metrics["pods"])
            df.columns = ["Pod Name", "CPU (cores)", "Memory (GB)", "Status"]

            # Display table
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

            # Summary stats
            st.caption(f"Total pods: {metrics['pod_count']}")
        else:
            st.warning("No pod metrics available")


def handle_auto_refresh(refresh_interval: int):
    """Handle auto-refresh logic."""
    time_since = (
        datetime.utcnow() - st.session_state.last_metrics_update
    ).total_seconds()

    if time_since >= refresh_interval:
        st.session_state.last_metrics_update = datetime.utcnow()
        st.rerun()


# Main app
def main():
    st.title("📊 Performance Monitoring")
    st.caption("Real-time CPU and memory usage for all services")

    # Controls
    control_col1, control_col2, control_col3 = st.columns([2, 2, 6])

    with control_col1:
        auto_refresh = st.toggle("Auto-refresh", value=True)

    with control_col2:
        refresh_interval = st.selectbox(
            "Interval",
            options=[15, 30, 60, 120],
            index=1,  # Default to 30 seconds
            format_func=lambda x: f"{x}s"
        )

    with control_col3:
        if st.button("🔄 Refresh Now"):
            st.session_state.last_metrics_update = datetime.utcnow()
            st.rerun()

    st.divider()

    # Fetch deployments
    try:
        deployments = list_deployments()
    except Exception as e:
        st.error(f"Error fetching deployments: {e}")
        logger.error(f"Error fetching deployments: {e}")
        return

    if not deployments:
        st.warning("No deployments found")
        return

    # Two-column layout
    sidebar_col, main_col = st.columns([2, 8])

    with sidebar_col:
        render_service_list(deployments)

    with main_col:
        if st.session_state.selected_service:
            render_metrics_panel(st.session_state.selected_service)
        else:
            # Default: show first service
            st.session_state.selected_service = deployments[0]["name"]
            st.rerun()

    # Auto-refresh
    if auto_refresh:
        handle_auto_refresh(refresh_interval)


if __name__ == "__main__":
    main()
