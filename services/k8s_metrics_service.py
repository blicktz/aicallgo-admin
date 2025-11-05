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
    pods = _get_pods_for_deployment(deployment_name)

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
    cpu_limit = None
    memory_limit = None

    try:
        deployment = apps_v1.read_namespaced_deployment(
            deployment_name, namespace
        )
        containers = deployment.spec.template.spec.containers
        cpu_limit_sum = 0.0
        memory_limit_sum = 0.0

        for container in containers:
            if container.resources and container.resources.limits:
                cpu_limit_str = container.resources.limits.get("cpu", "0")
                memory_limit_str = container.resources.limits.get("memory", "0")
                cpu_limit_sum += parse_cpu(cpu_limit_str)
                memory_limit_sum += parse_memory(memory_limit_str)

        cpu_limit = cpu_limit_sum if cpu_limit_sum > 0 else None
        memory_limit = memory_limit_sum if memory_limit_sum > 0 else None
    except ApiException as e:
        logger.warning(f"Could not read deployment limits: {e}")

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
    if cpu_limit and pod_count > 0:
        result["cpu_usage_percent"] = round((total_cpu / (cpu_limit * pod_count)) * 100, 1)
    if memory_limit and pod_count > 0:
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
