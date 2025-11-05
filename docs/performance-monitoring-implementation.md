# Performance Monitoring Implementation Guide

## Overview

This document provides a comprehensive guide for implementing a performance monitoring page in the admin-board service. The page displays CPU and memory usage for all services running in the Kubernetes cluster with time-series graphs, following the same UI pattern as the existing Logs page.

### Purpose

Provide a bird's-eye view of system load to quickly identify:
- Whether services are overloaded or running normally
- Resource usage patterns across all services
- Individual pod health within multi-replica deployments

### Target Users

Internal operations team monitoring AICallGO infrastructure health.

## Architecture

### Technical Approach

**Phase 1: Real-time Metrics (Recommended Starting Point)**
- Use Kubernetes Metrics Server API for current CPU/memory data
- Query via `/apis/metrics.k8s.io/v1beta1/pods` endpoint
- Display aggregated metrics for deployments with multiple replicas
- Store recent data points in session state for time-series charts

**Phase 2: Historical Metrics (Future Enhancement)**
- Enable Grafana Cloud integration in Terraform (`enable_grafana_cloud = true`)
- Query Prometheus for historical data
- Display longer time-series trends (hours/days instead of minutes)

### Infrastructure Requirements

**Kubernetes Metrics Server**:
- Must be deployed in the cluster (typically pre-installed in Digital Ocean Kubernetes)
- Scrapes metrics from kubelet every 60 seconds by default
- Provides current CPU and memory usage via API

**Verification Command**:
```bash
kubectl get deployment metrics-server -n kube-system
```

**If not deployed**:
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Available Monitoring Infrastructure

The AICallGO infrastructure already has Grafana Cloud configured but disabled:
- **Location**: `terraform/modules/grafana_cloud/`
- **Status**: `enable_grafana_cloud = false` in staging.tfvars
- **Components**: Grafana Alloy, Prometheus, Loki, kube-state-metrics, node-exporter
- **Credentials**: Configured in `staging-secrets.tfvars` and `prod-secrets.tfvars`

To enable for Phase 2:
```bash
cd terraform
# Edit staging.tfvars: set enable_grafana_cloud = true
make staging-plan
make staging-apply
```

## Refresh Cadence & Load Analysis

### Recommended: 30-Second Auto-Refresh

**Rationale**:
1. **Metrics-server update frequency**: Scrapes every 60 seconds by default
2. **Balance**: Fast enough to catch issues, slow enough to avoid unnecessary load
3. **User experience**: Feels responsive without being jarring
4. **Cluster load**: Minimal impact (120 API calls/hour per user)

### Load Impact Analysis

| Refresh Interval | Requests/Hour/User | Impact Level | Use Case |
|------------------|-------------------|--------------|----------|
| 15 seconds | 240 | Low | Real-time monitoring during incidents |
| **30 seconds** | **120** | **Very Low** | **Default - optimal balance** |
| 60 seconds | 60 | Minimal | Casual monitoring |
| 120 seconds | 30 | Negligible | Background monitoring |

### Optimization Strategies

**1. Caching**:
```python
@st.cache_data(ttl=30)  # Match refresh interval
def get_deployment_metrics(deployment_name: str):
    """Cached for 30 seconds to prevent redundant API calls."""
    pass
```
- Reduces load by ~50% with 2 concurrent users
- Prevents duplicate queries within the TTL window

**2. Lazy Loading**:
- Only fetch metrics for the **selected service**, not all services
- Reduces API calls by 80-90% (8 services → 1 service)
- Service list fetched separately (lightweight operation)

**3. Progressive Loading**:
```python
# Step 1: Load service list (fast, lightweight)
deployments = list_deployments()

# Step 2: Load metrics only for selected service
if selected_service:
    metrics = get_deployment_metrics(selected_service)
```

**4. User Controls**:
```python
# Allow users to adjust or pause refresh
auto_refresh = st.toggle("Auto-refresh", value=True)
refresh_interval = st.selectbox(
    "Refresh Interval",
    options=[15, 30, 60, 120],
    index=1,  # Default to 30 seconds
    format_func=lambda x: f"{x}s"
)
```

### Comparison with Other Tools

- **Kubernetes Dashboard**: 30-60 second default refresh
- **Grafana**: 30 seconds for real-time, 5 minutes for dashboards
- **kubectl top**: Manual refresh (on-demand)
- **Our approach**: 30 seconds with user control

## UI Design

### Layout Pattern

Follow the existing Logs page pattern (`pages/11_📋_Logs.py`):

```
┌─────────────────────────────────────────────────────────────┐
│  📊 Performance Monitoring                                   │
├─────────────┬───────────────────────────────────────────────┤
│             │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐             │
│ Services    │  │Total│ │Total│ │ Avg │ │ Avg │             │
│ (20%)       │  │ CPU │ │ Mem │ │ CPU │ │ Mem │             │
│             │  └─────┘ └─────┘ └─────┘ └─────┘             │
│ 🟢 web-     │                                                │
│    backend  │  ┌──────────────────────────────────────┐    │
│    (3)      │  │  CPU Usage Over Time (Last 5 min)   │    │
│             │  │  [Time-series line chart]            │    │
│ 🟢 ai-agent │  └──────────────────────────────────────┘    │
│    (2)      │                                                │
│             │  ┌──────────────────────────────────────┐    │
│ 🟡 nextjs-  │  │  Memory Usage Over Time              │    │
│    frontend │  │  [Time-series line chart]            │    │
│    (2)      │  └──────────────────────────────────────┘    │
│             │                                                │
│ 🟢 crawl4ai │  ▼ Per-Pod Breakdown                          │
│    (1)      │  ┌────────────────────────────────────┐      │
│             │  │ Pod Name    CPU    Memory  Status │      │
│ ...         │  │ pod-1      0.8c    2.1GB    🟢    │      │
│             │  │ pod-2      0.9c    2.0GB    🟢    │      │
│             │  │ pod-3      0.7c    2.1GB    🟢    │      │
│             │  └────────────────────────────────────┘      │
└─────────────┴───────────────────────────────────────────────┘
```

### Components

**Left Sidebar (20% width)**:
- Service name with health indicator emoji
- Replica count in parentheses
- Clickable button to select service
- Scrollable if many services

**Right Panel (80% width)**:
- **Metrics Row**: 4 metric cards showing key stats
- **Time-Series Charts**: CPU and memory trends (last 5-10 minutes)
- **Per-Pod Breakdown**: Expandable table with individual pod metrics
- **Auto-refresh Controls**: Toggle and interval selector

### Health Indicators

Color-coded status based on resource usage percentage (usage vs limits):

| Emoji | Status | Threshold | Meaning |
|-------|--------|-----------|---------|
| 🟢 | Healthy | < 70% | Normal operation |
| 🟡 | Warning | 70-90% | Approaching limits |
| 🔴 | Critical | > 90% | Near resource limits |
| ⚪ | Unknown | No limits set | Cannot determine health |

**Implementation**:
```python
def get_health_status(usage: float, limit: float) -> str:
    """Return health emoji based on usage percentage."""
    if limit == 0:
        return "⚪"  # No limit set

    percentage = (usage / limit) * 100

    if percentage < 70:
        return "🟢"
    elif percentage < 90:
        return "🟡"
    else:
        return "🔴"
```

## Implementation Details

### File Structure

```
services/admin-board/
├── pages/
│   └── 13_📊_Performance.py          # New page (300 lines)
├── services/
│   ├── k8s_service.py                 # Modify: add resource formatting
│   └── k8s_metrics_service.py         # New service (150 lines)
├── components/
│   └── performance_metrics_panel.py   # Optional: extracted component
└── streamlit_app.py                   # Modify: add to navigation
```

### 1. Create Metrics Service

**File**: `services/k8s_metrics_service.py`

```python
"""
Kubernetes metrics service for fetching CPU and memory usage.
Uses the metrics.k8s.io API to query metrics-server.
"""

from typing import Dict, List, Any, Optional
from kubernetes import client
from kubernetes.client.rest import ApiException
import logging

logger = logging.getLogger(__name__)


def get_pod_metrics(namespace: str) -> Dict[str, Any]:
    """
    Fetch CPU and memory metrics for all pods in a namespace.

    Returns metrics from the Kubernetes Metrics Server API.

    Args:
        namespace: Kubernetes namespace to query

    Returns:
        Dictionary with pod metrics

    Example response:
        {
            "items": [
                {
                    "metadata": {"name": "web-backend-abc123"},
                    "containers": [
                        {
                            "name": "web-backend",
                            "usage": {
                                "cpu": "250m",
                                "memory": "512Mi"
                            }
                        }
                    ]
                }
            ]
        }
    """
    try:
        api = client.CustomObjectsApi()
        metrics = api.list_namespaced_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="pods"
        )
        return metrics
    except ApiException as e:
        logger.error(f"Error fetching pod metrics: {e}")
        return {"items": []}


def get_deployment_metrics(
    deployment_name: str,
    namespace: str
) -> Dict[str, Any]:
    """
    Aggregate metrics for all pods in a deployment.

    For deployments with multiple replicas, this calculates:
    - Total CPU usage (sum across all pods)
    - Total memory usage (sum across all pods)
    - Average CPU per pod
    - Average memory per pod
    - Per-pod breakdown

    Args:
        deployment_name: Name of the deployment
        namespace: Kubernetes namespace

    Returns:
        Dictionary with aggregated metrics:
        {
            "total_cpu_cores": 2.5,
            "total_memory_gb": 4.2,
            "avg_cpu_cores": 0.83,
            "avg_memory_gb": 1.4,
            "cpu_limit_cores": 6.0,
            "memory_limit_gb": 8.0,
            "cpu_usage_percent": 41.7,
            "memory_usage_percent": 52.5,
            "pod_count": 3,
            "pods": [
                {
                    "name": "web-backend-abc123",
                    "cpu_cores": 0.8,
                    "memory_gb": 1.5,
                    "status": "🟢"
                }
            ]
        }
    """
    from services.k8s_service import _get_pods_for_deployment

    # Get pod list
    pods = _get_pods_for_deployment(deployment_name, namespace)

    # Get metrics for all pods
    all_metrics = get_pod_metrics(namespace)
    pod_metrics_map = {
        item["metadata"]["name"]: item
        for item in all_metrics.get("items", [])
    }

    # Aggregate metrics
    total_cpu = 0.0
    total_memory = 0.0
    pod_details = []

    # Get limits from pod spec
    apps_v1 = client.AppsV1Api()
    try:
        deployment = apps_v1.read_namespaced_deployment(
            deployment_name, namespace
        )
        containers = deployment.spec.template.spec.containers
        cpu_limit = sum(
            parse_cpu(c.resources.limits.get("cpu", "0"))
            for c in containers if c.resources and c.resources.limits
        ) or None
        memory_limit = sum(
            parse_memory(c.resources.limits.get("memory", "0"))
            for c in containers if c.resources and c.resources.limits
        ) or None
    except ApiException:
        cpu_limit = None
        memory_limit = None

    for pod in pods:
        pod_name = pod["name"]

        # Get metrics for this pod
        if pod_name not in pod_metrics_map:
            continue

        pod_metrics = pod_metrics_map[pod_name]

        # Sum container metrics
        pod_cpu = 0.0
        pod_memory = 0.0

        for container in pod_metrics.get("containers", []):
            usage = container.get("usage", {})
            pod_cpu += parse_cpu(usage.get("cpu", "0"))
            pod_memory += parse_memory(usage.get("memory", "0"))

        total_cpu += pod_cpu
        total_memory += pod_memory

        # Determine health status
        if cpu_limit:
            health = get_health_status(pod_cpu, cpu_limit)
        else:
            health = "⚪"

        pod_details.append({
            "name": pod_name,
            "cpu_cores": round(pod_cpu, 2),
            "memory_gb": round(pod_memory, 2),
            "status": health
        })

    pod_count = len(pod_details)

    result = {
        "total_cpu_cores": round(total_cpu, 2),
        "total_memory_gb": round(total_memory, 2),
        "avg_cpu_cores": round(total_cpu / pod_count, 2) if pod_count > 0 else 0,
        "avg_memory_gb": round(total_memory / pod_count, 2) if pod_count > 0 else 0,
        "cpu_limit_cores": cpu_limit,
        "memory_limit_gb": memory_limit,
        "pod_count": pod_count,
        "pods": pod_details
    }

    # Calculate usage percentages
    if cpu_limit:
        result["cpu_usage_percent"] = round((total_cpu / (cpu_limit * pod_count)) * 100, 1)
    if memory_limit:
        result["memory_usage_percent"] = round((total_memory / (memory_limit * pod_count)) * 100, 1)

    return result


def parse_cpu(cpu_string: str) -> float:
    """
    Parse Kubernetes CPU string to cores (float).

    Examples:
        "250m" -> 0.25
        "1" -> 1.0
        "1.5" -> 1.5
        "1000m" -> 1.0
    """
    if not cpu_string:
        return 0.0

    cpu_string = str(cpu_string).strip()

    if cpu_string.endswith("m"):
        # Millicores
        return float(cpu_string[:-1]) / 1000
    else:
        # Cores
        return float(cpu_string)


def parse_memory(memory_string: str) -> float:
    """
    Parse Kubernetes memory string to GB (float).

    Examples:
        "512Mi" -> 0.512
        "2Gi" -> 2.0
        "1024Mi" -> 1.024
        "256000Ki" -> 0.256
    """
    if not memory_string:
        return 0.0

    memory_string = str(memory_string).strip()

    # Parse unit
    units = {
        "Ki": 1024,
        "Mi": 1024 ** 2,
        "Gi": 1024 ** 3,
        "Ti": 1024 ** 4,
        "K": 1000,
        "M": 1000 ** 2,
        "G": 1000 ** 3,
        "T": 1000 ** 4,
    }

    for unit, multiplier in units.items():
        if memory_string.endswith(unit):
            value = float(memory_string[:-len(unit)])
            bytes_value = value * multiplier
            return bytes_value / (1024 ** 3)  # Convert to GB

    # No unit, assume bytes
    return float(memory_string) / (1024 ** 3)


def get_health_status(usage: float, limit: float) -> str:
    """
    Return health emoji based on usage percentage.

    Args:
        usage: Current resource usage
        limit: Resource limit

    Returns:
        Emoji indicating health status
    """
    if limit == 0:
        return "⚪"  # No limit set

    percentage = (usage / limit) * 100

    if percentage < 70:
        return "🟢"
    elif percentage < 90:
        return "🟡"
    else:
        return "🔴"


def format_cpu(cores: float) -> str:
    """Format CPU cores for display."""
    if cores < 0.01:
        return f"{cores * 1000:.0f}m"
    return f"{cores:.2f}"


def format_memory(gb: float) -> str:
    """Format memory GB for display."""
    if gb < 0.1:
        return f"{gb * 1024:.0f}Mi"
    return f"{gb:.2f}Gi"
```

### 2. Create Performance Page

**File**: `pages/13_📊_Performance.py`

```python
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
from config.settings import K8S_NAMESPACE

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
        fillcolor=f'rgba{tuple(list(bytes.fromhex(color[1:])) + [0.1])}'
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


def render_service_list(deployments: List[Dict]):
    """Render the service list sidebar."""
    st.markdown("### Services")
    st.caption(f"Total: {len(deployments)}")

    for deployment in deployments:
        name = deployment["name"]
        replicas = deployment["replicas"]
        ready = deployment["ready_replicas"]

        # Get health status (if metrics available)
        health_emoji = "🟢"  # Default

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
        metrics = get_deployment_metrics(service_name, K8S_NAMESPACE)
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

    with col3:
        st.metric(
            label="Avg CPU/Pod",
            value=f"{format_cpu(metrics['avg_cpu_cores'])} cores"
        )
        if metrics.get("cpu_usage_percent"):
            st.caption(f"Usage: {metrics['cpu_usage_percent']}%")

    with col4:
        st.metric(
            label="Avg Memory/Pod",
            value=f"{format_memory(metrics['avg_memory_gb'])}"
        )
        if metrics.get("memory_usage_percent"):
            st.caption(f"Usage: {metrics['memory_usage_percent']}%")

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
        st.info("Collecting data... Time-series charts will appear after multiple data points.")

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
        st.cache_data.clear()
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
            st.cache_data.clear()
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
```

### 3. Modify Streamlit App Navigation

**File**: `streamlit_app.py`

Add the Performance page to the System section navigation:

```python
# In the navigation menu configuration
system_pages = [
    st.Page("pages/10_⚙️_Settings.py", title="Settings", icon="⚙️"),
    st.Page("pages/11_📋_Logs.py", title="Logs", icon="📋"),
    st.Page("pages/12_🔧_System_Info.py", title="System Info", icon="🔧"),
    st.Page("pages/13_📊_Performance.py", title="Performance", icon="📊"),  # Add this line
]
```

### 4. Add Helper Functions to K8s Service

**File**: `services/k8s_service.py`

Add these utility functions if not already present:

```python
def format_resource_cpu(cpu_string: str) -> str:
    """Format CPU resource string for display."""
    from services.k8s_metrics_service import parse_cpu, format_cpu
    cores = parse_cpu(cpu_string)
    return format_cpu(cores)


def format_resource_memory(memory_string: str) -> str:
    """Format memory resource string for display."""
    from services.k8s_metrics_service import parse_memory, format_memory
    gb = parse_memory(memory_string)
    return format_memory(gb)
```

## Metrics Aggregation for Multiple Replicas

### Strategy

When a deployment has multiple replicas, we need to show both aggregate and per-pod metrics:

**1. Aggregate Metrics (Primary View)**:
- **Total CPU**: Sum of all pod CPU usage → Shows total capacity consumed
- **Total Memory**: Sum of all pod memory usage → Shows total memory footprint
- **Average CPU/Pod**: Total ÷ pod count → Shows typical pod behavior
- **Average Memory/Pod**: Total ÷ pod count → Shows typical pod footprint

**2. Per-Pod Metrics (Detailed View)**:
- Individual pod CPU and memory
- Health status per pod
- Helps identify outlier pods (stragglers, memory leaks)

### Why This Approach?

**Total (Sum)**:
- Best for capacity planning ("Do we have enough cluster resources?")
- Shows true cost/footprint
- Matches what cluster autoscaler sees

**Average**:
- Best for health assessment ("Are pods behaving normally?")
- Identifies outliers (one pod using 3x more than others = problem)
- Useful for horizontal pod autoscaler tuning

**Per-Pod**:
- Best for debugging
- Identifies specific problematic pods
- Shows distribution across replicas

### Example Display

```
web-backend (3 replicas)

Total CPU:    2.4 cores   (80% of 3.0 core limit)
Total Memory: 6.2 GB      (77% of 8.0 GB limit)

Avg CPU/Pod:    0.8 cores
Avg Memory/Pod: 2.1 GB

┌─────────────────────────────────────────┐
│ Per-Pod Breakdown                       │
├─────────────────────────────────────────┤
│ web-backend-abc123  0.8c  2.1GB  🟢    │
│ web-backend-def456  0.9c  2.0GB  🟢    │
│ web-backend-ghi789  0.7c  2.1GB  🟢    │
└─────────────────────────────────────────┘
```

### Alternative Approaches (Not Recommended)

**Max**: `max(pod1_cpu, pod2_cpu, pod3_cpu)`
- Use case: Identifying worst-case pod
- Problem: Doesn't show overall system load
- When to use: Only if debugging a specific performance issue

**Median**: `median(pod1_cpu, pod2_cpu, pod3_cpu)`
- Use case: Robust to outliers
- Problem: Less intuitive than average
- When to use: Only if many replicas (10+) with high variance

## Code Examples

### Fetching Metrics

```python
from services.k8s_metrics_service import get_deployment_metrics

# Get metrics for a specific deployment
metrics = get_deployment_metrics("web-backend", "aicallgo-staging")

# Access metrics
print(f"Total CPU: {metrics['total_cpu_cores']} cores")
print(f"Total Memory: {metrics['total_memory_gb']} GB")
print(f"Average CPU per pod: {metrics['avg_cpu_cores']} cores")
print(f"Pod count: {metrics['pod_count']}")

# Per-pod details
for pod in metrics["pods"]:
    print(f"{pod['name']}: {pod['cpu_cores']}c, {pod['memory_gb']}GB {pod['status']}")
```

### Caching Metrics

```python
import streamlit as st

@st.cache_data(ttl=30)  # Cache for 30 seconds
def get_cached_metrics(deployment: str, namespace: str):
    """Cached metrics fetch to reduce API calls."""
    return get_deployment_metrics(deployment, namespace)

# Usage
metrics = get_cached_metrics("web-backend", "aicallgo-staging")
```

### Auto-Refresh Pattern

```python
from datetime import datetime
import streamlit as st

# Initialize in session state
if "last_update" not in st.session_state:
    st.session_state.last_update = datetime.utcnow()

# Check if refresh needed
def should_refresh(interval_seconds: int) -> bool:
    elapsed = (datetime.utcnow() - st.session_state.last_update).total_seconds()
    return elapsed >= interval_seconds

# Refresh logic
if auto_refresh and should_refresh(30):
    st.session_state.last_update = datetime.utcnow()
    st.cache_data.clear()
    st.rerun()
```

### Time-Series History

```python
# Store in session state
if "metrics_history" not in st.session_state:
    st.session_state.metrics_history = {
        "timestamps": [],
        "cpu": [],
        "memory": []
    }

# Add data point
def add_data_point(cpu: float, memory: float):
    history = st.session_state.metrics_history
    history["timestamps"].append(datetime.utcnow())
    history["cpu"].append(cpu)
    history["memory"].append(memory)

    # Keep only last 20 points (10 minutes at 30s intervals)
    if len(history["timestamps"]) > 20:
        for key in history:
            history[key] = history[key][-20:]
```

## Testing & Verification

### 1. Verify Metrics Server

```bash
# Check if metrics-server is running
kubectl get deployment metrics-server -n kube-system

# Test metrics API manually
kubectl get --raw /apis/metrics.k8s.io/v1beta1/namespaces/aicallgo-staging/pods

# Compare with kubectl top
kubectl top pods -n aicallgo-staging
```

### 2. Test Metrics Service

Create a test script: `tests/test_k8s_metrics.py`

```python
from services.k8s_metrics_service import (
    parse_cpu,
    parse_memory,
    get_deployment_metrics
)

def test_parse_cpu():
    assert parse_cpu("250m") == 0.25
    assert parse_cpu("1") == 1.0
    assert parse_cpu("1500m") == 1.5

def test_parse_memory():
    assert parse_memory("512Mi") == 0.512
    assert parse_memory("2Gi") == 2.0

def test_get_deployment_metrics():
    metrics = get_deployment_metrics("web-backend", "aicallgo-staging")

    # Verify structure
    assert "total_cpu_cores" in metrics
    assert "total_memory_gb" in metrics
    assert "pods" in metrics
    assert isinstance(metrics["pods"], list)

    # Verify calculations
    if len(metrics["pods"]) > 0:
        assert metrics["avg_cpu_cores"] == sum(
            p["cpu_cores"] for p in metrics["pods"]
        ) / len(metrics["pods"])
```

### 3. Manual Verification

**Step 1: Access admin-board**
```bash
# Port-forward to admin-board
kubectl port-forward svc/admin-board 8501:8501 -n aicallgo-staging

# Open in browser
open http://localhost:8501
```

**Step 2: Navigate to Performance page**
- Go to System > Performance
- Select a service from the left sidebar

**Step 3: Verify metrics**
```bash
# In terminal, compare with kubectl top
kubectl top pods -n aicallgo-staging | grep web-backend

# web-backend-abc123  200m  512Mi
# web-backend-def456  250m  480Mi
```

**Expected**: Admin-board should show similar values (converted to cores and GB)

**Step 4: Test auto-refresh**
- Enable auto-refresh
- Wait 30 seconds
- Verify page updates automatically
- Check that time-series charts show new data points

**Step 5: Test multiple replicas**
- Select a service with 2+ replicas
- Verify total CPU = sum of pod CPUs
- Verify average CPU = total / pod count
- Expand per-pod breakdown
- Verify each pod shows individually

**Step 6: Load testing**
```bash
# Generate load on web-backend
kubectl exec -it web-backend-abc123 -n aicallgo-staging -- bash
# Inside pod: stress --cpu 2 --timeout 60

# Watch metrics in admin-board
# Should see CPU increase for that pod
```

### 4. Validate Calculations

```python
# Manual calculation
pods = [
    {"cpu": 0.8, "memory": 2.1},
    {"cpu": 0.9, "memory": 2.0},
    {"cpu": 0.7, "memory": 2.1}
]

total_cpu = sum(p["cpu"] for p in pods)      # = 2.4
avg_cpu = total_cpu / len(pods)              # = 0.8

# Should match admin-board display
```

## Future Enhancements

### Phase 2: Grafana Cloud Integration

Once `enable_grafana_cloud = true` is set in Terraform:

**1. Query Prometheus for Historical Data**

```python
import requests
from datetime import datetime, timedelta

def query_prometheus(query: str, start: datetime, end: datetime, step: str = "30s"):
    """Query Prometheus for historical metrics."""
    url = "https://prometheus-prod-56-prod-us-east-2.grafana.net/api/v1/query_range"

    params = {
        "query": query,
        "start": start.timestamp(),
        "end": end.timestamp(),
        "step": step
    }

    headers = {
        "Authorization": f"Bearer {GRAFANA_API_KEY}"
    }

    response = requests.get(url, params=params, headers=headers)
    return response.json()

# Example queries
cpu_query = 'sum(rate(container_cpu_usage_seconds_total{namespace="aicallgo-staging",pod=~"web-backend.*"}[5m]))'
memory_query = 'sum(container_memory_usage_bytes{namespace="aicallgo-staging",pod=~"web-backend.*"})'

# Fetch last 24 hours
end = datetime.utcnow()
start = end - timedelta(hours=24)

cpu_data = query_prometheus(cpu_query, start, end, step="1m")
```

**2. Extended Time Ranges**

Add time range selector:
```python
time_range = st.selectbox(
    "Time Range",
    options=["Last 5 minutes", "Last hour", "Last 6 hours", "Last 24 hours"],
    index=0
)
```

**3. Alerting**

Configure alerts based on thresholds:
```python
def check_alerts(metrics: Dict) -> List[str]:
    """Check for alert conditions."""
    alerts = []

    if metrics.get("cpu_usage_percent", 0) > 90:
        alerts.append(f"⚠️ High CPU usage: {metrics['cpu_usage_percent']}%")

    if metrics.get("memory_usage_percent", 0) > 90:
        alerts.append(f"⚠️ High memory usage: {metrics['memory_usage_percent']}%")

    return alerts

# Display alerts
alerts = check_alerts(metrics)
if alerts:
    for alert in alerts:
        st.warning(alert)
```

**4. Comparison Views**

Compare metrics across services:
```python
# Multi-service comparison
services = ["web-backend", "ai-agent", "nextjs-frontend"]
metrics_data = []

for service in services:
    metrics = get_deployment_metrics(service, namespace)
    metrics_data.append({
        "Service": service,
        "CPU (cores)": metrics["total_cpu_cores"],
        "Memory (GB)": metrics["total_memory_gb"]
    })

df = pd.DataFrame(metrics_data)
st.bar_chart(df.set_index("Service"))
```

**5. Cost Estimation**

Calculate estimated cloud costs based on resource usage:
```python
def estimate_cost(cpu_cores: float, memory_gb: float) -> float:
    """Estimate monthly cost based on resource usage."""
    # Digital Ocean pricing (example)
    cpu_cost_per_core_hour = 0.012  # $0.012/core/hour
    memory_cost_per_gb_hour = 0.003  # $0.003/GB/hour

    hours_per_month = 730

    cpu_cost = cpu_cores * cpu_cost_per_core_hour * hours_per_month
    memory_cost = memory_gb * memory_cost_per_gb_hour * hours_per_month

    return cpu_cost + memory_cost

# Display cost estimate
monthly_cost = estimate_cost(
    metrics["total_cpu_cores"],
    metrics["total_memory_gb"]
)
st.metric("Estimated Monthly Cost", f"${monthly_cost:.2f}")
```

### Phase 3: Advanced Analytics

**1. Anomaly Detection**

Detect unusual patterns:
```python
from scipy import stats

def detect_anomalies(history: List[float], threshold: float = 2.0) -> bool:
    """Detect if current value is anomalous using z-score."""
    if len(history) < 5:
        return False

    mean = np.mean(history[:-1])
    std = np.std(history[:-1])
    current = history[-1]

    z_score = abs((current - mean) / std) if std > 0 else 0
    return z_score > threshold

# Check for anomalies
if detect_anomalies(st.session_state.metrics_history[service_name]["cpu"]):
    st.warning("⚠️ Anomalous CPU usage detected!")
```

**2. Predictive Scaling**

Predict when resources will be exhausted:
```python
def predict_resource_exhaustion(
    history: List[float],
    limit: float,
    timestamps: List[datetime]
) -> Optional[datetime]:
    """Predict when resource usage will hit limit."""
    if len(history) < 3:
        return None

    # Linear regression
    from sklearn.linear_model import LinearRegression

    X = np.array([(t - timestamps[0]).total_seconds() for t in timestamps]).reshape(-1, 1)
    y = np.array(history)

    model = LinearRegression()
    model.fit(X, y)

    # Find when it will hit limit
    if model.coef_[0] <= 0:  # Decreasing or flat
        return None

    seconds_to_limit = (limit - model.intercept_) / model.coef_[0]
    exhaustion_time = timestamps[0] + timedelta(seconds=seconds_to_limit)

    return exhaustion_time if exhaustion_time > datetime.utcnow() else None
```

**3. Resource Recommendations**

Suggest optimal resource limits:
```python
def recommend_limits(metrics_history: Dict) -> Dict[str, float]:
    """Recommend resource limits based on historical usage."""
    cpu_history = metrics_history["cpu"]
    memory_history = metrics_history["memory"]

    # Use 95th percentile + 20% headroom
    cpu_p95 = np.percentile(cpu_history, 95)
    memory_p95 = np.percentile(memory_history, 95)

    return {
        "cpu_limit": cpu_p95 * 1.2,
        "memory_limit": memory_p95 * 1.2
    }

# Display recommendations
recommendations = recommend_limits(st.session_state.metrics_history[service_name])
st.info(f"💡 Recommended limits: CPU={recommendations['cpu_limit']:.2f} cores, Memory={recommendations['memory_limit']:.2f} GB")
```

## Troubleshooting

### Issue: "Metrics not available"

**Cause**: Metrics-server not deployed or not ready

**Solution**:
```bash
# Check metrics-server status
kubectl get deployment metrics-server -n kube-system

# If not found, install
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Wait for ready
kubectl wait --for=condition=available --timeout=60s deployment/metrics-server -n kube-system
```

### Issue: "Permission denied" when querying metrics API

**Cause**: Admin-board service account lacks RBAC permissions

**Solution**:
```yaml
# Add to k8s_config module
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: admin-board-metrics-reader
rules:
- apiGroups: ["metrics.k8s.io"]
  resources: ["pods", "nodes"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin-board-metrics-reader
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: admin-board-metrics-reader
subjects:
- kind: ServiceAccount
  name: admin-board
  namespace: aicallgo-staging
```

### Issue: Metrics are always zero

**Cause**: Parsing error or wrong container name

**Debug**:
```bash
# Check raw metrics
kubectl get --raw /apis/metrics.k8s.io/v1beta1/namespaces/aicallgo-staging/pods/web-backend-abc123 | jq

# Verify container names match
kubectl get pod web-backend-abc123 -n aicallgo-staging -o jsonpath='{.spec.containers[*].name}'
```

### Issue: Time-series charts not showing

**Cause**: Need multiple data points (takes 60+ seconds to accumulate)

**Solution**: Wait for 2+ refresh cycles, or show helpful message:
```python
if len(history["timestamps"]) < 2:
    st.info("⏳ Collecting data... Charts will appear after 60 seconds")
```

### Issue: High memory usage in admin-board

**Cause**: Storing too much history in session state

**Solution**: Limit history size (already implemented: max 20 points)
```python
# Keep only last 20 data points
if len(history["timestamps"]) > 20:
    history["timestamps"] = history["timestamps"][-20:]
```

## Summary

This implementation provides:

✅ **Real-time monitoring** with 30-second refresh (optimal balance)
✅ **Low cluster load** through caching and lazy loading
✅ **Aggregate + per-pod metrics** for multi-replica deployments
✅ **Time-series visualization** showing usage trends
✅ **Health indicators** with color-coded status
✅ **User controls** for refresh interval and auto-refresh toggle
✅ **Extensible architecture** ready for Grafana Cloud integration

**Next Steps**:
1. Implement the three files (metrics service, performance page, navigation update)
2. Test with metrics-server in staging environment
3. Verify calculations match kubectl top output
4. (Optional) Enable Grafana Cloud for historical data
5. (Optional) Add alerting and cost estimation features

**Estimated Implementation Time**: 2-3 hours for Phase 1, 1-2 days for Phase 2 with historical charts.
