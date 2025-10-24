"""
Logs - Kubernetes pod logs viewer
Real-time log viewing with Docker Desktop-style split layout
"""
import streamlit as st
from datetime import datetime
from config.auth import require_auth
from services.k8s_service import (
    is_k8s_available,
    list_deployments,
    get_deployment_logs,
    get_cluster_info
)
import logging
from ansi2html import Ansi2HTMLConverter

logger = logging.getLogger(__name__)

# Auth check
if not require_auth():
    st.stop()

st.title("📋 Logs")
st.markdown("View real-time logs from Kubernetes pods")

# Check if K8s is available
if not is_k8s_available():
    st.error("❌ Kubernetes access not configured")
    st.info("""
    **To enable logs viewer:**

    1. Set `K8S_LOGS_ENABLED=true` in .env
    2. Configure `KUBECONFIG_PATH` to point to your kubeconfig file
    3. Set `K8S_NAMESPACE` to your target namespace (e.g., aicallgo-staging)
    4. Restart the admin board

    For local development, you can use port-forwarding or configure kubectl access.
    """)
    st.stop()

# Cluster info and controls
col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
with col1:
    cluster_info = get_cluster_info()
    if cluster_info.get("available"):
        st.caption(f"**Cluster:** K8s {cluster_info.get('kubernetes_version', 'N/A')} | "
                   f"{cluster_info.get('node_count', 0)} nodes | "
                   f"Namespace: {cluster_info.get('namespace', 'N/A')}")
    else:
        st.caption("⚠️ Cluster info unavailable")

with col2:
    tail_lines = st.selectbox(
        "Tail lines",
        options=[50, 100, 200, 500, 1000],
        index=1,
        key="tail_lines_selector"
    )

with col3:
    auto_refresh = st.checkbox("Auto-refresh", value=False, key="auto_refresh_checkbox")

with col4:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        if "current_logs" in st.session_state:
            del st.session_state.current_logs
        st.rerun()

# Auto-refresh every 10 seconds if enabled
if auto_refresh:
    import time
    time.sleep(10)
    if "current_logs" in st.session_state:
        del st.session_state.current_logs
    st.rerun()

st.divider()

# Fetch deployments
with st.spinner("Loading services..."):
    deployments = list_deployments()

if not deployments:
    st.warning("No deployments found in the namespace")
    st.stop()

# Initialize session state for selected service
if "selected_service" not in st.session_state:
    st.session_state.selected_service = deployments[0]["name"]

# Create 20/80 split layout
sidebar_col, logs_col = st.columns([2, 8])

# LEFT SIDEBAR: Service list
with sidebar_col:
    st.markdown("### Services")

    # Create service selection
    for deployment in deployments:
        name = deployment["name"]
        replicas = deployment["replicas"]
        ready = deployment["ready_replicas"]
        available = deployment["available_replicas"]

        # Determine status color
        if ready == replicas and available == replicas and replicas > 0:
            status_emoji = "🟢"
        elif ready > 0:
            status_emoji = "🟡"
        else:
            status_emoji = "🔴"

        # Create clickable service button
        service_label = f"{status_emoji} {name}"
        replica_info = f"{ready}/{replicas}"

        # Check if this service is selected
        is_selected = st.session_state.selected_service == name

        # Use button with custom styling
        button_type = "primary" if is_selected else "secondary"
        if st.button(
            f"{service_label}\n`{replica_info}`",
            key=f"btn_{name}",
            use_container_width=True,
            type=button_type
        ):
            # Clear logs when changing selection
            if st.session_state.selected_service != name:
                st.session_state.selected_service = name
                if "current_logs" in st.session_state:
                    del st.session_state.current_logs
                st.rerun()

# RIGHT PANEL: Logs viewer
with logs_col:
    selected_service = st.session_state.selected_service

    # Find selected deployment info
    selected_deployment = next((d for d in deployments if d["name"] == selected_service), None)

    if selected_deployment:
        # Header with service info
        ready = selected_deployment["ready_replicas"]
        replicas = selected_deployment["replicas"]
        pods = selected_deployment["pods"]

        st.markdown(f"### Logs: `{selected_service}`")
        st.caption(f"Replicas: {ready}/{replicas} ready | Pods: {len(pods)}")

        # Fetch logs if not in session state
        if "current_logs" not in st.session_state:
            with st.spinner(f"Loading logs for {selected_service}..."):
                logs_by_pod = get_deployment_logs(selected_service, tail_lines=tail_lines)
                st.session_state.current_logs = logs_by_pod
        else:
            logs_by_pod = st.session_state.current_logs

        # Display logs in a fixed-height container
        if "error" in logs_by_pod:
            st.error(logs_by_pod["error"])
        elif not logs_by_pod:
            st.warning("No logs available for this service")
        else:
            # VS Code Dark+ / Terminal color scheme CSS
            st.markdown("""
                <style>
                .terminal-logs {
                    background-color: #1e1e1e !important;
                    color: #d4d4d4 !important;
                    font-family: 'Courier New', Consolas, Monaco, monospace !important;
                    font-size: 13px !important;
                    line-height: 1.5 !important;
                    padding: 16px !important;
                    border-radius: 4px !important;
                    border: 1px solid #3e3e3e !important;
                    overflow-x: auto !important;
                    overflow-y: auto !important;
                    white-space: pre !important;
                    word-break: normal !important;
                    overflow-wrap: normal !important;
                    height: 550px !important;
                    max-width: none !important;
                    width: 100% !important;
                }
                .terminal-logs::-webkit-scrollbar {
                    width: 10px;
                    height: 10px;
                }
                .terminal-logs::-webkit-scrollbar-track {
                    background: #252526;
                }
                .terminal-logs::-webkit-scrollbar-thumb {
                    background: #424242;
                    border-radius: 4px;
                }
                .terminal-logs::-webkit-scrollbar-thumb:hover {
                    background: #4e4e4e;
                }
                .log-separator {
                    color: #569cd6;
                    font-weight: bold;
                }
                .log-pod-name {
                    color: #4ec9b0;
                    font-weight: bold;
                }
                </style>
            """, unsafe_allow_html=True)

            # Build logs HTML with proper formatting
            log_html = '<div class="terminal-logs">'

            for pod_container_name, logs in logs_by_pod.items():
                # Pod/Container header
                log_html += '<span class="log-separator">=' * 80 + '</span>\n'
                log_html += f'<span class="log-pod-name">Pod/Container: {pod_container_name}</span>\n'
                log_html += '<span class="log-separator">=' * 80 + '</span>\n'

                if logs:
                    # Convert ANSI color codes to HTML
                    converter = Ansi2HTMLConverter(inline=True, scheme='xterm')
                    colored_logs = converter.convert(logs, full=False)
                    log_html += colored_logs
                else:
                    log_html += '<span style="color: #808080;">(No logs available)</span>\n'

                log_html += '\n\n'

            log_html += '</div>'

            # Display the terminal-style logs
            st.markdown(log_html, unsafe_allow_html=True)

        # Pod details section (collapsed by default)
        if pods:
            with st.expander("📦 Pod Details", expanded=False):
                for pod in pods:
                    pod_name = pod["name"]
                    phase = pod["phase"]
                    containers = pod["containers"]
                    node = pod["node"]

                    # Pod phase indicator
                    phase_emoji = {
                        "Running": "🟢",
                        "Pending": "🟡",
                        "Succeeded": "✅",
                        "Failed": "🔴",
                        "Unknown": "⚪"
                    }.get(phase, "⚪")

                    st.markdown(f"**{phase_emoji} {pod_name}**")

                    pod_info_col1, pod_info_col2 = st.columns([3, 1])

                    with pod_info_col1:
                        # Container status
                        for container in containers:
                            container_status = "✅" if container["ready"] else "❌"
                            st.caption(
                                f"{container_status} {container['name']} - "
                                f"{container['state']} (restarts: {container['restart_count']})"
                            )

                    with pod_info_col2:
                        st.caption(f"Node: {node}")

                    st.markdown("---")

# Footer
st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
