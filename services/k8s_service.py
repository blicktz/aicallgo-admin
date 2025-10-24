"""
Kubernetes service for viewing pod logs and managing deployments.
Provides integration with Digital Ocean Kubernetes cluster.
"""
from typing import Dict, List, Any, Optional, Generator
from datetime import datetime
import logging
import os
from config.settings import settings

logger = logging.getLogger(__name__)

# Lazy import kubernetes to avoid errors when it's not needed
_k8s_available = False
_client_core_v1 = None
_client_apps_v1 = None
_k8s_config = None

def _init_k8s_client():
    """Initialize Kubernetes client lazily."""
    global _k8s_available, _client_core_v1, _client_apps_v1, _k8s_config

    if not settings.K8S_LOGS_ENABLED:
        logger.info("Kubernetes logs feature is disabled")
        return False

    if _k8s_available:
        return True

    try:
        from kubernetes import client, config
        _k8s_config = config

        # Load kubeconfig
        if settings.KUBECONFIG_PATH:
            # Load from specified file path
            config.load_kube_config(config_file=settings.KUBECONFIG_PATH)
            logger.info(f"Loaded kubeconfig from {settings.KUBECONFIG_PATH}")
        else:
            # Try in-cluster config first, fallback to default kubeconfig
            try:
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes config")
            except config.ConfigException:
                config.load_kube_config()
                logger.info("Loaded default kubeconfig")

        _client_core_v1 = client.CoreV1Api()
        _client_apps_v1 = client.AppsV1Api()
        _k8s_available = True
        logger.info("Kubernetes client initialized successfully")
        return True

    except ImportError:
        logger.warning("kubernetes package not installed")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Kubernetes client: {e}")
        return False


def is_k8s_available() -> bool:
    """Check if Kubernetes client is available and configured."""
    return _init_k8s_client()


def list_deployments() -> List[Dict[str, Any]]:
    """
    List all deployments in the configured namespace.

    Returns:
        List of deployment information dicts with:
        - name: Deployment name
        - replicas: Number of replicas (desired)
        - ready_replicas: Number of ready replicas
        - available_replicas: Number of available replicas
        - created_at: Creation timestamp
        - labels: Deployment labels
        - pods: List of pod information
    """
    if not _init_k8s_client():
        return []

    try:
        # List deployments
        deployments = _client_apps_v1.list_namespaced_deployment(
            namespace=settings.K8S_NAMESPACE
        )

        result = []
        for deployment in deployments.items:
            # Get pods for this deployment
            pods = _get_pods_for_deployment(deployment.metadata.name)

            result.append({
                "name": deployment.metadata.name,
                "replicas": deployment.spec.replicas or 0,
                "ready_replicas": deployment.status.ready_replicas or 0,
                "available_replicas": deployment.status.available_replicas or 0,
                "created_at": deployment.metadata.creation_timestamp,
                "labels": deployment.metadata.labels or {},
                "pods": pods
            })

        # Sort by name
        result.sort(key=lambda x: x["name"])
        return result

    except Exception as e:
        logger.error(f"Failed to list deployments: {e}")
        return []


def _get_pods_for_deployment(deployment_name: str) -> List[Dict[str, Any]]:
    """
    Get all pods for a specific deployment.

    Args:
        deployment_name: Name of the deployment

    Returns:
        List of pod information dicts
    """
    try:
        # Get pods with label selector matching the deployment
        pods = _client_core_v1.list_namespaced_pod(
            namespace=settings.K8S_NAMESPACE,
            label_selector=f"app={deployment_name}"
        )

        result = []
        for pod in pods.items:
            # Get pod status
            phase = pod.status.phase

            # Get container statuses
            containers = []
            if pod.status.container_statuses:
                for container in pod.status.container_statuses:
                    containers.append({
                        "name": container.name,
                        "ready": container.ready,
                        "restart_count": container.restart_count,
                        "state": _get_container_state(container.state)
                    })

            result.append({
                "name": pod.metadata.name,
                "phase": phase,
                "created_at": pod.metadata.creation_timestamp,
                "containers": containers,
                "node": pod.spec.node_name,
                "ip": pod.status.pod_ip
            })

        # Sort by creation time (newest first)
        result.sort(key=lambda x: x["created_at"], reverse=True)
        return result

    except Exception as e:
        logger.error(f"Failed to get pods for deployment {deployment_name}: {e}")
        return []


def _get_container_state(state) -> str:
    """Extract container state as a string."""
    if state.running:
        return "running"
    elif state.waiting:
        return f"waiting: {state.waiting.reason or 'unknown'}"
    elif state.terminated:
        return f"terminated: {state.terminated.reason or 'unknown'}"
    return "unknown"


def get_pod_logs(
    pod_name: str,
    container_name: Optional[str] = None,
    tail_lines: int = 100,
    follow: bool = False,
    timestamps: bool = True
) -> str:
    """
    Get logs from a specific pod.

    Args:
        pod_name: Name of the pod
        container_name: Name of the container (if pod has multiple containers)
        tail_lines: Number of lines to retrieve from the end
        follow: Whether to stream logs (not recommended for batch retrieval)
        timestamps: Include timestamps in logs

    Returns:
        Log content as string
    """
    if not _init_k8s_client():
        return "Kubernetes client not available"

    try:
        kwargs = {
            "name": pod_name,
            "namespace": settings.K8S_NAMESPACE,
            "tail_lines": tail_lines,
            "timestamps": timestamps
        }

        if container_name:
            kwargs["container"] = container_name

        logs = _client_core_v1.read_namespaced_pod_log(**kwargs)
        return logs

    except Exception as e:
        error_msg = f"Failed to get logs for pod {pod_name}: {e}"
        logger.error(error_msg)
        return error_msg


def stream_pod_logs(
    pod_name: str,
    container_name: Optional[str] = None,
    tail_lines: int = 100
) -> Generator[str, None, None]:
    """
    Stream logs from a specific pod in real-time.

    Args:
        pod_name: Name of the pod
        container_name: Name of the container (if pod has multiple containers)
        tail_lines: Number of lines to retrieve from the end initially

    Yields:
        Log lines as they arrive
    """
    if not _init_k8s_client():
        yield "Kubernetes client not available"
        return

    try:
        from kubernetes import watch

        kwargs = {
            "name": pod_name,
            "namespace": settings.K8S_NAMESPACE,
            "tail_lines": tail_lines,
            "timestamps": True
        }

        if container_name:
            kwargs["container"] = container_name

        w = watch.Watch()

        # Stream logs
        for line in w.stream(_client_core_v1.read_namespaced_pod_log, **kwargs):
            yield line

    except Exception as e:
        error_msg = f"Failed to stream logs for pod {pod_name}: {e}"
        logger.error(error_msg)
        yield error_msg


def get_deployment_logs(
    deployment_name: str,
    tail_lines: int = 100
) -> Dict[str, str]:
    """
    Get logs from all pods of a deployment.

    Args:
        deployment_name: Name of the deployment
        tail_lines: Number of lines to retrieve from each pod

    Returns:
        Dict mapping pod names to their logs
    """
    if not _init_k8s_client():
        return {"error": "Kubernetes client not available"}

    try:
        # Get pods for deployment
        pods = _client_core_v1.list_namespaced_pod(
            namespace=settings.K8S_NAMESPACE,
            label_selector=f"app={deployment_name}"
        )

        logs_by_pod = {}

        for pod in pods.items:
            pod_name = pod.metadata.name

            # Get logs from all containers in the pod
            if pod.spec.containers:
                if len(pod.spec.containers) == 1:
                    # Single container - just get logs directly
                    logs = get_pod_logs(pod_name, tail_lines=tail_lines)
                    logs_by_pod[pod_name] = logs
                else:
                    # Multiple containers - get logs from each
                    for container in pod.spec.containers:
                        container_name = container.name
                        logs = get_pod_logs(
                            pod_name,
                            container_name=container_name,
                            tail_lines=tail_lines
                        )
                        logs_by_pod[f"{pod_name}/{container_name}"] = logs

        return logs_by_pod

    except Exception as e:
        error_msg = f"Failed to get logs for deployment {deployment_name}: {e}"
        logger.error(error_msg)
        return {"error": error_msg}


def get_cluster_info() -> Dict[str, Any]:
    """
    Get basic cluster information.

    Returns:
        Dict with cluster info including version and node count
    """
    if not _init_k8s_client():
        return {"available": False, "error": "Kubernetes client not available"}

    try:
        # Get version info
        from kubernetes import client
        version_api = client.VersionApi()
        version_info = version_api.get_code()

        # Get node count
        nodes = _client_core_v1.list_node()

        return {
            "available": True,
            "kubernetes_version": version_info.git_version,
            "node_count": len(nodes.items),
            "namespace": settings.K8S_NAMESPACE
        }

    except Exception as e:
        logger.error(f"Failed to get cluster info: {e}")
        return {
            "available": False,
            "error": str(e)
        }
