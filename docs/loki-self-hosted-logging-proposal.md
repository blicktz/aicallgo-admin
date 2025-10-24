# Self-Hosted Loki Logging Solution for Admin Board

**Status:** Proposal
**Created:** 2025-10-23
**Author:** Infrastructure Team
**Target:** Admin Board Log Viewer Enhancement

---

## Executive Summary

This document proposes implementing a self-hosted Grafana Loki deployment on our DOKS cluster to enhance the Admin Board's log viewing capabilities. The solution addresses current Kubernetes API rate limit concerns while providing superior log search, history, and filtering capabilities at minimal infrastructure cost.

**Key Benefits:**
- Eliminates Kubernetes API rate limit concerns
- Provides 7-30 days of searchable log history
- Enables powerful LogQL-based filtering and aggregation
- Requires minimal resources (~0.5 CPU cores, 1Gi memory)
- Zero external service costs
- Improves user experience with real-time search

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Problem Statement](#problem-statement)
3. [Proposed Solution](#proposed-solution)
4. [Architecture Overview](#architecture-overview)
5. [Implementation Plan](#implementation-plan)
6. [Resource Requirements](#resource-requirements)
7. [Storage & Retention Strategy](#storage--retention-strategy)
8. [Admin Board Integration](#admin-board-integration)
9. [Deployment Steps](#deployment-steps)
10. [Cost-Benefit Analysis](#cost-benefit-analysis)
11. [Alternatives Considered](#alternatives-considered)
12. [Risk Assessment](#risk-assessment)
13. [Success Metrics](#success-metrics)

---

## Current State Analysis

### Existing Log Viewing Implementation

**File:** `services/admin-board/pages/11_📋_Logs.py`

The current implementation queries logs directly from Kubernetes API:

```python
# Current flow
Admin Board → k8s_service.py → Kubernetes API → Pod Logs
```

**Current API Usage:**
- `list_deployments()`: 1 API call
- `_get_pods_for_deployment()`: 1 API call per deployment (×8 = 8 calls)
- `get_deployment_logs()`: 1 call to list pods + 1 call per pod (×2 avg = 3 calls)

**Per Refresh:** ~12 API calls
**With Auto-Refresh (10s):** 6 refreshes/min × 12 calls = **72 API calls/minute**
**Hourly Rate:** 72 × 60 = **4,320 API calls/hour**

### Current Limitations

1. **Rate Limit Concerns**
   - Digital Ocean API limit: 5,000 req/hour per token
   - Kubernetes API limit: 250 req/min (default)
   - Current usage (1 user): 72 req/min ✓ Safe
   - With 3-4 concurrent users: **216-288 req/min** ⚠️ Approaching limit

2. **Functionality Limitations**
   - No log history (only tail of current pods)
   - No search/filtering capabilities
   - No aggregation or log analytics
   - Loses logs when pods restart
   - Cannot view logs from terminated pods

3. **Scalability Issues**
   - Linear growth with services (8 services → 72 req/min)
   - Linear growth with users
   - No caching mechanism
   - Inefficient full-page refreshes

---

## Problem Statement

The Admin Board's current log viewing approach has three critical issues:

1. **API Rate Limit Risk**: As the number of services and concurrent users grows, we risk hitting Digital Ocean's Kubernetes API rate limits (250 req/min), which could impact cluster management operations.

2. **Poor User Experience**: Users can only view recent logs (tail), cannot search historical logs, and lose visibility when pods restart or are replaced.

3. **Scalability Constraints**: The current architecture doesn't scale well with additional services or users without risking rate limit exhaustion.

**Business Impact:**
- Development efficiency: Debugging requires log history
- Incident response: Need to investigate issues after they occur
- Operational visibility: Missing terminated pod logs

---

## Proposed Solution

Deploy a **self-hosted Grafana Loki** instance in monolithic mode on our DOKS cluster to serve as a centralized log aggregation and query system.

### Solution Overview

**Components:**
1. **Loki (Monolithic)**: Single-binary deployment for log storage and querying
2. **Promtail**: DaemonSet for log collection from pods
3. **Loki Service**: Python client in Admin Board for querying logs

**Data Flow:**
```
Pods → Promtail (DaemonSet) → Loki → Admin Board → Users
         ↓                       ↓
    Label extraction       Index + Store
                               ↓
                          Query API
```

### Key Features

1. **Centralized Storage**
   - 7-30 days of log retention (configurable)
   - Persists logs beyond pod lifecycle
   - Indexed metadata for fast queries

2. **Powerful Query Language (LogQL)**
   - Filter by service, pod, container, log level
   - Pattern matching and regex support
   - Aggregation and counting
   - Time-range queries

3. **No External Dependencies**
   - Runs entirely on DOKS cluster
   - No Grafana Cloud subscription required
   - Zero external API costs

4. **Minimal Resource Footprint**
   - Single Loki pod: ~200m CPU, 512Mi memory
   - Promtail fleet: ~250m CPU, 320Mi memory
   - Total: ~450m CPU, ~832Mi memory

---

## Architecture Overview

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ DOKS Cluster (aicallgo-staging)                             │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Application Namespace (aicallgo-staging)            │   │
│  │                                                       │   │
│  │  [web-backend] [ai-agent] [nextjs] [chatwoot]       │   │
│  │       │            │          │          │           │   │
│  │       └────────────┴──────────┴──────────┘           │   │
│  │                     │                                 │   │
│  └─────────────────────┼─────────────────────────────────┘   │
│                        │ Pod Logs                            │
│                        ↓                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Monitoring Namespace (aicallgo-staging-monitoring)   │   │
│  │                                                       │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Promtail DaemonSet (1 pod per node)          │  │   │
│  │  │ - Discovers pods automatically               │  │   │
│  │  │ - Reads logs from /var/log/pods              │  │   │
│  │  │ - Adds labels: namespace, pod, container     │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                        │                             │   │
│  │                        ↓ HTTP Push                   │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Loki (Monolithic Mode)                       │  │   │
│  │  │ - Single StatefulSet pod                     │  │   │
│  │  │ - Ingester + Distributor + Querier           │  │   │
│  │  │ - PersistentVolume (10Gi)                    │  │   │
│  │  │ - HTTP API on port 3100                      │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                        │                             │   │
│  └────────────────────────┼─────────────────────────────┘   │
│                           │ HTTP API                         │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            ↓ LogQL Queries
                  ┌─────────────────────┐
                  │   Admin Board       │
                  │  (loki_service.py)  │
                  │  - Query logs       │
                  │  - Filter/search    │
                  │  - Display results  │
                  └─────────────────────┘
```

### Network Communication

**Internal Cluster Communication:**
- Promtail → Loki: `http://loki.aicallgo-staging-monitoring.svc.cluster.local:3100/loki/api/v1/push`
- Admin Board → Loki: `http://loki.aicallgo-staging-monitoring.svc.cluster.local:3100/loki/api/v1/query_range`

**No External Traffic Required**: All communication stays within the cluster network.

### Deployment Modes Comparison

| Mode | Components | Use Case | Resources |
|------|------------|----------|-----------|
| **Monolithic (Proposed)** | Single pod | Small deployments, <20GB/day | Minimal |
| Simple Scalable | 3 separate pods | Medium deployments, 20-100GB/day | Moderate |
| Microservices | 10+ pods | Large deployments, >100GB/day | High |

**Our Choice: Monolithic Mode**
- Estimated log volume: ~300MB/day (well below 20GB limit)
- 8 services in staging environment
- Single replica sufficient for availability
- Minimal operational complexity

---

## Implementation Plan

### Phase 1: Terraform Infrastructure

#### 1.1 Create Loki Terraform Module

**New Directory:** `terraform/modules/loki/`

**Files to Create:**
```
terraform/modules/loki/
├── main.tf           # Helm release for Loki + Promtail
├── variables.tf      # Module variables
├── outputs.tf        # Loki endpoint, status
└── README.md         # Module documentation
```

**Key Resources:**

**main.tf:**
```hcl
resource "helm_release" "loki" {
  name       = "loki"
  namespace  = var.namespace
  repository = "https://grafana.github.io/helm-charts"
  chart      = "loki"
  version    = "6.0.0"  # Latest stable as of 2024

  values = [
    yamlencode({
      deploymentMode = "SingleBinary"

      loki = {
        auth_enabled = false

        commonConfig = {
          replication_factor = 1
        }

        storage = {
          type = "filesystem"
        }

        limits_config = {
          retention_period = var.retention_period
          ingestion_rate_mb = 10
          ingestion_burst_size_mb = 20
        }

        schemaConfig = {
          configs = [{
            from = "2024-01-01"
            store = "tsdb"
            object_store = "filesystem"
            schema = "v13"
            index = {
              prefix = "index_"
              period = "24h"
            }
          }]
        }
      }

      singleBinary = {
        replicas = 1

        persistence = {
          enabled = true
          size = var.storage_size
        }

        resources = {
          requests = {
            cpu = var.cpu_request
            memory = var.memory_request
          }
          limits = {
            cpu = var.cpu_limit
            memory = var.memory_limit
          }
        }
      }

      # Enable Promtail for log collection
      promtail = {
        enabled = true

        config = {
          clients = [{
            url = "http://loki:3100/loki/api/v1/push"
          }]

          snippets = {
            extraScrapeConfigs = yamlencode([{
              job_name = "kubernetes-pods"

              kubernetes_sd_configs = [{
                role = "pod"
                namespaces = {
                  names = var.log_namespaces
                }
              }]

              relabel_configs = [
                {
                  source_labels = ["__meta_kubernetes_pod_name"]
                  target_label = "pod"
                }
                {
                  source_labels = ["__meta_kubernetes_namespace"]
                  target_label = "namespace"
                }
                {
                  source_labels = ["__meta_kubernetes_pod_container_name"]
                  target_label = "container"
                }
                {
                  source_labels = ["__meta_kubernetes_pod_label_app"]
                  target_label = "app"
                }
              ]
            }])
          }
        }

        resources = {
          requests = {
            cpu = "50m"
            memory = "64Mi"
          }
          limits = {
            cpu = "100m"
            memory = "128Mi"
          }
        }
      }
    })
  ]
}

# Create a ConfigMap with Loki connection info
resource "kubernetes_config_map" "loki_info" {
  metadata {
    name      = "loki-connection"
    namespace = var.namespace
  }

  data = {
    loki_url = "http://loki.${var.namespace}.svc.cluster.local:3100"
    loki_query_endpoint = "http://loki.${var.namespace}.svc.cluster.local:3100/loki/api/v1/query_range"
    retention_period = var.retention_period
  }
}
```

**variables.tf:**
```hcl
variable "namespace" {
  description = "Kubernetes namespace for Loki deployment"
  type        = string
}

variable "storage_size" {
  description = "PersistentVolume size for Loki data"
  type        = string
  default     = "10Gi"
}

variable "retention_period" {
  description = "Log retention period (e.g., 168h for 7 days)"
  type        = string
  default     = "168h"
}

variable "log_namespaces" {
  description = "List of namespaces to collect logs from"
  type        = list(string)
  default     = []
}

variable "cpu_request" {
  description = "CPU request for Loki pod"
  type        = string
  default     = "100m"
}

variable "cpu_limit" {
  description = "CPU limit for Loki pod"
  type        = string
  default     = "200m"
}

variable "memory_request" {
  description = "Memory request for Loki pod"
  type        = string
  default     = "256Mi"
}

variable "memory_limit" {
  description = "Memory limit for Loki pod"
  type        = string
  default     = "512Mi"
}

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}
```

**outputs.tf:**
```hcl
output "loki_url" {
  description = "Internal Loki service URL"
  value       = "http://loki.${var.namespace}.svc.cluster.local:3100"
}

output "loki_query_endpoint" {
  description = "Loki query API endpoint"
  value       = "http://loki.${var.namespace}.svc.cluster.local:3100/loki/api/v1/query_range"
}

output "helm_release_status" {
  description = "Status of the Loki Helm release"
  value       = helm_release.loki.status
}

output "retention_period" {
  description = "Configured log retention period"
  value       = var.retention_period
}
```

#### 1.2 Update Root Terraform Configuration

**File:** `terraform/main.tf`

Add module invocation after the Redis module:

```hcl
# Loki Module - Self-hosted log aggregation
module "loki" {
  count  = var.enable_loki && var.enable_k8s_resources ? 1 : 0
  source = "./modules/loki"

  namespace        = module.k8s_base[0].monitoring_namespace_name
  environment      = var.environment
  storage_size     = var.loki_storage_size
  retention_period = var.loki_retention_period
  log_namespaces   = ["aicallgo-${var.environment}"]

  cpu_request    = var.loki_cpu_request
  cpu_limit      = var.loki_cpu_limit
  memory_request = var.loki_memory_request
  memory_limit   = var.loki_memory_limit

  depends_on = [module.k8s_base]
}
```

**File:** `terraform/variables.tf`

Add variables for Loki configuration:

```hcl
# Loki Configuration
variable "enable_loki" {
  description = "Enable self-hosted Loki for log aggregation"
  type        = bool
  default     = false
}

variable "loki_storage_size" {
  description = "PersistentVolume size for Loki data storage"
  type        = string
  default     = "10Gi"
}

variable "loki_retention_period" {
  description = "Log retention period (e.g., 168h for 7 days, 720h for 30 days)"
  type        = string
  default     = "168h"
}

variable "loki_cpu_request" {
  description = "CPU request for Loki pod"
  type        = string
  default     = "100m"
}

variable "loki_cpu_limit" {
  description = "CPU limit for Loki pod"
  type        = string
  default     = "200m"
}

variable "loki_memory_request" {
  description = "Memory request for Loki pod"
  type        = string
  default     = "256Mi"
}

variable "loki_memory_limit" {
  description = "Memory limit for Loki pod"
  type        = string
  default     = "512Mi"
}
```

**File:** `terraform/staging-public.tfvars`

Enable and configure Loki:

```hcl
# Self-hosted Loki Configuration
enable_loki             = true
loki_storage_size       = "10Gi"   # Approximately 30 days of logs
loki_retention_period   = "168h"   # 7 days retention
loki_cpu_request        = "100m"
loki_cpu_limit          = "200m"
loki_memory_request     = "256Mi"
loki_memory_limit       = "512Mi"
```

**File:** `terraform/outputs.tf`

Add Loki outputs:

```hcl
# Loki Outputs
output "loki_url" {
  description = "Loki internal service URL"
  value       = var.enable_loki && length(module.loki) > 0 ? module.loki[0].loki_url : "Loki not enabled"
}

output "loki_query_endpoint" {
  description = "Loki query API endpoint for Admin Board"
  value       = var.enable_loki && length(module.loki) > 0 ? module.loki[0].loki_query_endpoint : "Loki not enabled"
}

output "loki_status" {
  description = "Loki deployment status"
  value = var.enable_loki && length(module.loki) > 0 ? {
    helm_status     = module.loki[0].helm_release_status
    retention       = module.loki[0].retention_period
    storage_size    = var.loki_storage_size
  } : "Loki not enabled"
}
```

### Phase 2: Admin Board Integration

#### 2.1 Create Loki Service Module

**New File:** `services/admin-board/services/loki_service.py`

```python
"""
Loki service for querying logs from self-hosted Loki instance.
Provides integration with Grafana Loki HTTP API.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import requests
from config.settings import settings

logger = logging.getLogger(__name__)

class LokiService:
    """Service for querying logs from Loki."""

    def __init__(self):
        self.enabled = settings.LOKI_ENABLED
        self.base_url = settings.LOKI_URL
        self.query_endpoint = f"{self.base_url}/loki/api/v1/query_range"
        self.default_limit = settings.LOKI_DEFAULT_LIMIT

    def is_available(self) -> bool:
        """Check if Loki service is available."""
        if not self.enabled:
            return False

        try:
            response = requests.get(
                f"{self.base_url}/ready",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Loki health check failed: {e}")
            return False

    def query_logs(
        self,
        query: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = None,
        direction: str = "backward"
    ) -> Dict[str, Any]:
        """
        Query logs using LogQL.

        Args:
            query: LogQL query string (e.g., '{app="web-backend"}')
            start_time: Start time for query (default: 1 hour ago)
            end_time: End time for query (default: now)
            limit: Maximum number of log lines to return
            direction: Query direction ("forward" or "backward")

        Returns:
            Dict with log streams and metadata
        """
        if not self.enabled:
            return {"error": "Loki service not enabled"}

        # Default time range: last 1 hour
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        # Convert to nanosecond timestamps (Loki format)
        start_ns = int(start_time.timestamp() * 1e9)
        end_ns = int(end_time.timestamp() * 1e9)

        params = {
            "query": query,
            "start": start_ns,
            "end": end_ns,
            "limit": limit or self.default_limit,
            "direction": direction
        }

        try:
            response = requests.get(
                self.query_endpoint,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            if data.get("status") != "success":
                return {"error": f"Loki query failed: {data.get('error', 'Unknown error')}"}

            return self._parse_response(data)

        except requests.exceptions.RequestException as e:
            logger.error(f"Loki query failed: {e}")
            return {"error": str(e)}

    def get_deployment_logs(
        self,
        deployment_name: str,
        namespace: str = None,
        hours: int = 1,
        limit: int = None
    ) -> Dict[str, str]:
        """
        Get logs for a specific deployment.

        Args:
            deployment_name: Name of the deployment
            namespace: Kubernetes namespace (default: from settings)
            hours: Number of hours of logs to fetch
            limit: Maximum number of log lines

        Returns:
            Dict mapping pod names to their logs
        """
        if namespace is None:
            namespace = settings.K8S_NAMESPACE

        # LogQL query to match all pods for this deployment
        query = f'{{namespace="{namespace}", app="{deployment_name}"}}'

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        result = self.query_logs(
            query=query,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

        if "error" in result:
            return result

        # Group logs by pod
        logs_by_pod = {}
        for stream in result.get("streams", []):
            labels = stream.get("labels", {})
            pod_name = labels.get("pod", "unknown")
            container_name = labels.get("container", "")

            # Create a unique key for pod/container
            if container_name:
                key = f"{pod_name}/{container_name}"
            else:
                key = pod_name

            # Combine log lines
            log_lines = [entry["line"] for entry in stream.get("values", [])]
            logs_by_pod[key] = "\n".join(log_lines)

        return logs_by_pod

    def search_logs(
        self,
        namespace: str,
        search_term: str,
        hours: int = 1,
        limit: int = None
    ) -> Dict[str, Any]:
        """
        Search logs for a specific term.

        Args:
            namespace: Kubernetes namespace
            search_term: Text to search for in logs
            hours: Number of hours to search
            limit: Maximum number of results

        Returns:
            Dict with matching log entries
        """
        # LogQL query with text filter
        query = f'{{namespace="{namespace}"}} |= "{search_term}"'

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        return self.query_logs(
            query=query,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

    def _parse_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Loki API response.

        Args:
            data: Raw response from Loki

        Returns:
            Parsed response with streams and metadata
        """
        result_data = data.get("data", {})
        result_type = result_data.get("resultType", "")

        if result_type != "streams":
            return {"error": f"Unexpected result type: {result_type}"}

        streams = []
        for stream in result_data.get("result", []):
            stream_labels = stream.get("stream", {})
            values = stream.get("values", [])

            # Parse log entries
            entries = []
            for value in values:
                # value is [timestamp_ns, log_line]
                timestamp_ns = int(value[0])
                timestamp = datetime.fromtimestamp(timestamp_ns / 1e9)
                log_line = value[1]

                entries.append({
                    "timestamp": timestamp.isoformat(),
                    "line": log_line
                })

            streams.append({
                "labels": stream_labels,
                "values": entries
            })

        stats = result_data.get("stats", {})

        return {
            "streams": streams,
            "total_entries": sum(len(s["values"]) for s in streams),
            "stats": stats
        }


# Singleton instance
_loki_service = None

def get_loki_service() -> LokiService:
    """Get singleton Loki service instance."""
    global _loki_service
    if _loki_service is None:
        _loki_service = LokiService()
    return _loki_service

def is_loki_available() -> bool:
    """Check if Loki is available."""
    return get_loki_service().is_available()
```

#### 2.2 Update Settings

**File:** `services/admin-board/config/settings.py`

Add Loki configuration:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Loki Configuration
    LOKI_ENABLED: bool = Field(
        default=True,
        description="Enable Loki log querying"
    )

    LOKI_URL: str = Field(
        default="http://loki.aicallgo-staging-monitoring.svc.cluster.local:3100",
        description="Loki service URL"
    )

    LOKI_DEFAULT_LIMIT: int = Field(
        default=5000,
        description="Default limit for log query results"
    )

    LOKI_MAX_HOURS: int = Field(
        default=168,  # 7 days
        description="Maximum hours of logs that can be queried"
    )
```

#### 2.3 Update Logs Page

**File:** `services/admin-board/pages/11_📋_Logs.py`

Add Loki integration with source toggle:

```python
import streamlit as st
from datetime import datetime, timedelta
from config.auth import require_auth
from services.k8s_service import (
    is_k8s_available,
    list_deployments,
    get_deployment_logs as get_k8s_logs,
    get_cluster_info
)
from services.loki_service import (
    is_loki_available,
    get_loki_service
)
import logging
from ansi2html import Ansi2HTMLConverter

logger = logging.getLogger(__name__)

# Auth check
if not require_auth():
    st.stop()

st.title("📋 Logs")

# Check available log sources
k8s_available = is_k8s_available()
loki_available = is_loki_available()

if not k8s_available and not loki_available:
    st.error("❌ No log sources available")
    st.info("""
    **Available log sources:**

    1. **Kubernetes API** - Direct pod log access (set K8S_LOGS_ENABLED=true)
    2. **Loki** - Centralized log aggregation (requires Loki deployment)
    """)
    st.stop()

# Source selection
col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])

with col1:
    cluster_info = get_cluster_info()
    if cluster_info.get("available"):
        st.caption(f"**Cluster:** K8s {cluster_info.get('kubernetes_version', 'N/A')} | "
                   f"{cluster_info.get('node_count', 0)} nodes | "
                   f"Namespace: {cluster_info.get('namespace', 'N/A')}")

with col2:
    # Log source selector
    log_sources = []
    if k8s_available:
        log_sources.append("Kubernetes API")
    if loki_available:
        log_sources.append("Loki")

    if len(log_sources) > 1:
        log_source = st.selectbox(
            "Source",
            options=log_sources,
            index=1 if loki_available else 0,
            key="log_source_selector"
        )
    else:
        log_source = log_sources[0]
        st.caption(f"Source: {log_source}")

with col3:
    if log_source == "Loki":
        time_ranges = {
            "Last 1 hour": 1,
            "Last 6 hours": 6,
            "Last 24 hours": 24,
            "Last 7 days": 168
        }
        time_range_label = st.selectbox(
            "Time Range",
            options=list(time_ranges.keys()),
            index=0,
            key="time_range_selector"
        )
        time_range_hours = time_ranges[time_range_label]
    else:
        tail_lines = st.selectbox(
            "Tail lines",
            options=[50, 100, 200, 500, 1000],
            index=1,
            key="tail_lines_selector"
        )

with col4:
    auto_refresh = st.checkbox("Auto-refresh", value=False, key="auto_refresh_checkbox")

with col5:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        if "current_logs" in st.session_state:
            del st.session_state.current_logs
        st.rerun()

# Auto-refresh logic (increased to 30 seconds for Loki)
if auto_refresh:
    import time
    refresh_interval = 30 if log_source == "Loki" else 10
    time.sleep(refresh_interval)
    if "current_logs" in st.session_state:
        del st.session_state.current_logs
    st.rerun()

st.divider()

# LogQL search box for Loki
if log_source == "Loki":
    with st.expander("🔍 Advanced Search (LogQL)", expanded=False):
        st.markdown("""
        **LogQL Examples:**
        - Filter by level: `|= "ERROR"` or `|= "WARNING"`
        - JSON fields: `| json | status_code >= 400`
        - Regex: `|~ "error|ERROR|Error"`
        - Exclude: `!= "health"`
        """)

        search_term = st.text_input(
            "Search filter",
            placeholder="e.g., |= \"error\" or leave empty for all logs",
            key="loki_search"
        )

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

        service_label = f"{status_emoji} {name}"
        replica_info = f"{ready}/{replicas}"

        is_selected = st.session_state.selected_service == name
        button_type = "primary" if is_selected else "secondary"

        if st.button(
            f"{service_label}\n`{replica_info}`",
            key=f"btn_{name}",
            use_container_width=True,
            type=button_type
        ):
            if st.session_state.selected_service != name:
                st.session_state.selected_service = name
                if "current_logs" in st.session_state:
                    del st.session_state.current_logs
                st.rerun()

# RIGHT PANEL: Logs viewer
with logs_col:
    selected_service = st.session_state.selected_service
    selected_deployment = next((d for d in deployments if d["name"] == selected_service), None)

    if selected_deployment:
        ready = selected_deployment["ready_replicas"]
        replicas = selected_deployment["replicas"]
        pods = selected_deployment["pods"]

        # Header
        header_col1, header_col2 = st.columns([6, 1])
        with header_col1:
            st.markdown(f"### Logs: `{selected_service}`")
            st.caption(f"Source: {log_source} | Replicas: {ready}/{replicas}")
        with header_col2:
            if log_source == "Loki":
                st.caption(f"📅 {time_range_label}")

        # Fetch logs
        if "current_logs" not in st.session_state:
            with st.spinner(f"Loading logs from {log_source}..."):
                if log_source == "Loki":
                    loki_service = get_loki_service()
                    logs_by_pod = loki_service.get_deployment_logs(
                        deployment_name=selected_service,
                        hours=time_range_hours,
                        limit=5000
                    )
                else:
                    logs_by_pod = get_k8s_logs(selected_service, tail_lines=tail_lines)

                st.session_state.current_logs = logs_by_pod
        else:
            logs_by_pod = st.session_state.current_logs

        # Display logs
        if "error" in logs_by_pod:
            st.error(logs_by_pod["error"])
        elif not logs_by_pod:
            st.warning("No logs available for this service")
        else:
            # Terminal CSS (same as before)
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

            # Build logs HTML
            log_html = '<div class="terminal-logs">'

            for pod_container_name, logs in logs_by_pod.items():
                log_html += '<span class="log-separator">=' * 80 + '</span>\n'
                log_html += f'<span class="log-pod-name">Pod/Container: {pod_container_name}</span>\n'
                log_html += '<span class="log-separator">=' * 80 + '</span>\n'

                if logs:
                    # Convert ANSI codes to HTML colors
                    converter = Ansi2HTMLConverter(inline=True, scheme='xterm')
                    colored_logs = converter.convert(logs, full=False)
                    log_html += colored_logs
                else:
                    log_html += '<span style="color: #808080;">(No logs available)</span>\n'

                log_html += '\n\n'

            log_html += '</div>'

            st.markdown(log_html, unsafe_allow_html=True)

        # Pod details (collapsed)
        if pods and log_source == "Kubernetes API":
            with st.expander("📦 Pod Details", expanded=False):
                for pod in pods:
                    pod_name = pod["name"]
                    phase = pod["phase"]
                    containers = pod["containers"]
                    node = pod["node"]

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
footer_col1, footer_col2 = st.columns([3, 1])
with footer_col1:
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with footer_col2:
    st.caption(f"Source: {log_source}")
```

#### 2.4 Update Environment Configuration

**File:** `services/admin-board/.env.example`

Add Loki configuration:

```bash
# Loki Configuration
LOKI_ENABLED=true
LOKI_URL=http://loki.aicallgo-staging-monitoring.svc.cluster.local:3100
LOKI_DEFAULT_LIMIT=5000
LOKI_MAX_HOURS=168
```

---

## Resource Requirements

### Detailed Resource Analysis

#### Loki Pod (Monolithic Mode)

**CPU:**
- Request: 100m (0.1 cores)
- Limit: 200m (0.2 cores)
- Average usage: ~80-120m under normal load
- Peak usage: ~150-180m during heavy queries

**Memory:**
- Request: 256Mi
- Limit: 512Mi
- Average usage: ~200-300Mi
- Peak usage: ~400-450Mi during ingestion spikes

**Storage:**
- PersistentVolume: 10Gi (default)
- Usage rate: ~300MB/day (estimated for 8 services)
- Retention: 7-30 days configurable

**Network:**
- Ingestion: ~1-2 Mbps average
- Queries: ~0.5-1 Mbps average
- Total: <5 Mbps

#### Promtail DaemonSet (Per Node)

**CPU:**
- Request: 50m per pod
- Limit: 100m per pod
- Average: ~30-40m per pod
- **Total for 5 nodes**: 250m request, 500m limit

**Memory:**
- Request: 64Mi per pod
- Limit: 128Mi per pod
- Average: ~50-70Mi per pod
- **Total for 5 nodes**: 320Mi request, 640Mi limit

**Storage:**
- No persistent storage needed
- Uses node filesystem for reading pod logs

### Total Resource Footprint

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit | Storage |
|-----------|-------------|-----------|----------------|--------------|---------|
| Loki | 100m | 200m | 256Mi | 512Mi | 10Gi PV |
| Promtail (×5) | 250m | 500m | 320Mi | 640Mi | 0 |
| **Total** | **350m** | **700m** | **576Mi** | **1152Mi** | **10Gi** |

### Current Cluster Capacity

**DOKS Staging Cluster:**
- Node size: s-2vcpu-4gb (2 vCPU, 4GB RAM per node)
- Node count: 0-5 (auto-scaling)
- Total capacity (5 nodes): 10 vCPU, 20GB RAM

**Resource Utilization Impact:**
- CPU: 350m / 10000m = **3.5% of cluster capacity**
- Memory: 576Mi / 20480Mi = **2.8% of cluster capacity**
- Storage: 10Gi (one PersistentVolume on Digital Ocean Volumes)

**Conclusion:** Minimal impact on cluster resources.

---

## Storage & Retention Strategy

### Log Volume Analysis

**Estimated Daily Log Volume (8 Services):**

| Service | Est. Logs/Day | Notes |
|---------|---------------|-------|
| web-backend | 100 MB | High traffic, API logs |
| web-backend-worker | 30 MB | Celery tasks |
| ai-agent-backend | 50 MB | Call logs, verbose |
| outcall-agent | 30 MB | Similar to ai-agent |
| nextjs-frontend | 20 MB | SSR logs, errors |
| crawl4ai-service | 30 MB | Crawling logs |
| chatwoot-web | 20 MB | Rails logs |
| chatwoot-worker | 10 MB | Background jobs |
| **Total** | **~290 MB/day** | Compressed ~60-80 MB/day |

**Note:** Loki compresses logs, so actual disk usage is typically 20-30% of raw log size.

### Retention Scenarios

| Storage Size | Retention Period | Cost/Month (DO) | Use Case |
|--------------|------------------|-----------------|----------|
| 5 Gi | 14-20 days | $1.00 | Minimal, testing |
| 10 Gi | 30-40 days | $2.00 | Recommended |
| 20 Gi | 60-80 days | $4.00 | Extended history |
| 50 Gi | 150+ days | $10.00 | Long-term audit |

**Recommended:** **10Gi with 7-14 day retention** for staging environment.

### Retention Configuration

**Automatic Cleanup:**
Loki automatically deletes logs older than the configured retention period:

```yaml
limits_config:
  retention_period: 168h  # 7 days
```

**Manual Cleanup:**
If needed, can also configure:
```yaml
compactor:
  retention_enabled: true
  retention_delete_delay: 2h
```

### Storage Optimization Techniques

1. **Log Level Filtering:**
   - Filter debug logs at Promtail level
   - Only ship info/warn/error to Loki
   - Reduces volume by 30-50%

2. **Namespace Filtering:**
   - Only collect from app namespace
   - Exclude kube-system, monitoring, etc.
   - Reduces volume by 60-70%

3. **Compression:**
   - Loki uses Snappy compression by default
   - ~70-80% compression ratio
   - Automatically handled

4. **Sampling (if needed):**
   - Can configure Promtail to sample logs
   - E.g., keep 1 in every N health check logs
   - Only if hitting storage limits

---

## Admin Board Integration

### User Experience Improvements

#### 1. Source Selection

Users can toggle between:
- **Kubernetes API**: Real-time, last N lines
- **Loki**: Historical, time-range queries

#### 2. Time Range Selection (Loki Mode)

Dropdown options:
- Last 1 hour
- Last 6 hours
- Last 24 hours
- Last 7 days
- Custom range (date picker)

#### 3. Advanced Search (LogQL)

Search box with examples:
```logql
# Filter by log level
|= "ERROR"

# Exclude health checks
!= "/health"

# JSON field filtering
| json | status_code >= 400

# Regex matching
|~ "error|ERROR|Error"

# Multiple conditions
|= "error" | json | user_id="123"
```

#### 4. Log Display

- Same terminal-style interface
- ANSI color support preserved
- Automatic scrolling to latest
- Pod/container grouping

#### 5. Performance

**Current (K8s API):**
- Refresh: 10 seconds
- API calls: 72/min per user
- History: None

**With Loki:**
- Refresh: 30 seconds (less frequent needed)
- API calls: 2/min per user (97% reduction)
- History: 7-30 days

### API Comparison

| Metric | Kubernetes API | Loki API |
|--------|---------------|----------|
| Refresh rate | 10s | 30s |
| Calls per refresh | 12 | 1-2 |
| Calls per minute | 72 | 2-4 |
| History | None | 7-30 days |
| Search | No | Yes (LogQL) |
| Filter | No | Yes |
| Aggregation | No | Yes |
| Rate limit risk | High | None |

---

## Deployment Steps

### Prerequisites

1. DOKS cluster running
2. kubectl configured with cluster access
3. Helm 3.x installed
4. Terraform >= 1.5.0

### Step-by-Step Deployment

#### Step 1: Create Loki Terraform Module

```bash
cd terraform

# Create module directory
mkdir -p modules/loki

# Create files (main.tf, variables.tf, outputs.tf)
# Use content from Phase 1 above
```

#### Step 2: Update Root Terraform Configuration

```bash
# Edit terraform/main.tf - add module invocation
# Edit terraform/variables.tf - add Loki variables
# Edit terraform/staging-public.tfvars - enable Loki
```

#### Step 3: Initialize and Plan

```bash
cd terraform

# Initialize new module
terraform init

# Plan changes
terraform plan \
  -var-file=staging-public.tfvars \
  -var-file=staging-secrets.tfvars

# Review plan output - should show:
# - helm_release.loki to be created
# - kubernetes_config_map.loki_info to be created
```

#### Step 4: Apply Terraform Changes

```bash
# Apply infrastructure changes
terraform apply \
  -var-file=staging-public.tfvars \
  -var-file=staging-secrets.tfvars

# Wait for deployment to complete (~3-5 minutes)
```

#### Step 5: Verify Loki Deployment

```bash
# Set kubeconfig
export KUBECONFIG=~/staging-kubeconfig.txt

# Check Loki pods
kubectl get pods -n aicallgo-staging-monitoring | grep loki

# Expected output:
# loki-0                          1/1     Running   0          2m
# loki-promtail-xxxxx            1/1     Running   0          2m
# loki-promtail-yyyyy            1/1     Running   0          2m
# ... (one promtail per node)

# Check Loki logs
kubectl logs -n aicallgo-staging-monitoring loki-0 --tail=50

# Should see:
# level=info msg="Loki started"
# level=info msg="Server listening on :3100"

# Check Promtail logs
kubectl logs -n aicallgo-staging-monitoring -l app.kubernetes.io/name=promtail --tail=20

# Should see:
# level=info msg="Starting Promtail"
# level=info msg="Seeked /var/log/pods/..."
```

#### Step 6: Test Loki Query API

```bash
# Port-forward Loki service
kubectl port-forward -n aicallgo-staging-monitoring svc/loki 3100:3100 &

# Test health endpoint
curl http://localhost:3100/ready
# Should return: ready

# Test query endpoint
curl -G http://localhost:3100/loki/api/v1/query_range \
  --data-urlencode 'query={namespace="aicallgo-staging"}' \
  --data-urlencode 'limit=10'

# Should return JSON with log streams

# Kill port-forward when done
pkill -f "port-forward.*loki"
```

#### Step 7: Update Admin Board Code

```bash
cd services/admin-board

# Create loki_service.py
# Update config/settings.py
# Update pages/11_📋_Logs.py
# Update .env.example

# Use content from Phase 2 above
```

#### Step 8: Test Admin Board Locally (Optional)

```bash
cd services/admin-board

# Set up port-forward for testing
kubectl port-forward -n aicallgo-staging-monitoring svc/loki 3100:3100 &

# Update .env for local testing
cat >> .env <<EOF
LOKI_ENABLED=true
LOKI_URL=http://localhost:3100
LOKI_DEFAULT_LIMIT=5000
EOF

# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run streamlit_app.py

# Test in browser:
# 1. Navigate to Logs page
# 2. Select "Loki" as source
# 3. Choose a service (e.g., web-backend)
# 4. Verify logs appear
# 5. Test search filter
# 6. Test time range selector
```

#### Step 9: Deploy Updated Admin Board

```bash
# Build new admin-board image
cd services/admin-board
docker build -t registry.digitalocean.com/aicallgo-registry/admin-board:loki-v1 .

# Push to registry
docker push registry.digitalocean.com/aicallgo-registry/admin-board:loki-v1

# Update deployment (if using CI/CD, push to branch)
# Or manually update image tag:
kubectl set image deployment/admin-board \
  admin-board=registry.digitalocean.com/aicallgo-registry/admin-board:loki-v1 \
  -n aicallgo-staging

# Wait for rollout
kubectl rollout status deployment/admin-board -n aicallgo-staging
```

#### Step 10: Verify End-to-End

```bash
# Access admin board
# URL: https://staging.julya.ai/admin (or your configured URL)

# Test workflow:
# 1. Login to admin board
# 2. Navigate to Logs page
# 3. Verify "Loki" appears in source selector
# 4. Select "Loki" as source
# 5. Choose a service
# 6. Verify logs load successfully
# 7. Test search: enter |= "error"
# 8. Test time range: select "Last 24 hours"
# 9. Compare with K8s API source

# Monitor Loki resource usage
kubectl top pod -n aicallgo-staging-monitoring | grep loki

# Check storage usage
kubectl exec -n aicallgo-staging-monitoring loki-0 -- df -h /loki
```

---

## Cost-Benefit Analysis

### Implementation Costs

**Development Time:**
- Terraform module creation: 2-3 hours
- Admin Board integration: 3-4 hours
- Testing and debugging: 2-3 hours
- Documentation: 1-2 hours
- **Total: 8-12 hours**

**Infrastructure Costs (Monthly):**
- Storage (10Gi PV): $2.00/month
- Compute (included in node pool): $0.00/month (already running)
- **Total: $2.00/month**

**Alternatives Costs:**
- Grafana Cloud Free: $0/month but 50GB limit, then expensive
- Grafana Cloud Pro: $50+/month
- ELK Stack: Much heavier resources, ~$20-50/month equivalent
- **Our Solution: $2/month**

### Benefits

**Quantitative Benefits:**
- API rate limit reduction: 72 → 2 calls/min (97% reduction)
- Log history: 0 days → 7-30 days
- Storage cost: $2/month
- User capacity: 3-4x more concurrent users
- Query performance: Same or better
- Debugging efficiency: 50%+ improvement (estimated)

**Qualitative Benefits:**
- Better developer experience
- Faster incident response
- Historical debugging capabilities
- Powerful search and filtering
- Reduced risk of rate limiting
- Foundation for future observability

### Return on Investment

**Cost Avoidance:**
- Grafana Cloud Pro: $50/month → Save $48/month
- Alternative: ELK Stack resource cost → Save ~$18-48/month

**Productivity Gains:**
- Faster debugging: 10-20 min saved per issue
- Average 5 debugging sessions/week
- Savings: 50-100 min/week = ~2 hours/week
- Value: ~$100-200/month (developer time)

**ROI:**
- Monthly cost: $2
- Monthly benefit: $150-250 (conservatively)
- **ROI: 75x - 125x**

---

## Alternatives Considered

### Alternative 1: Grafana Cloud

**Pros:**
- Managed service (no maintenance)
- Professional UI
- Alerting integration

**Cons:**
- Expensive ($50+/month after free tier)
- Free tier: 50GB/month limit (we'd hit ~9GB/month)
- External dependency
- Data leaves cluster

**Verdict:** ❌ Too expensive for convenience feature

### Alternative 2: ELK Stack (Elasticsearch + Kibana)

**Pros:**
- Full-featured
- Rich UI
- Mature ecosystem

**Cons:**
- Heavy resource usage (3-5GB memory minimum)
- Complex setup
- Elasticsearch resource hungry
- Overkill for our needs

**Verdict:** ❌ Too resource-intensive

### Alternative 3: Simple File-Based Logs

**Pros:**
- Minimal resources
- Very simple

**Cons:**
- No search/filtering
- No aggregation
- Difficult to query
- Manual cleanup required
- Same K8s API limitations

**Verdict:** ❌ Doesn't solve the problem

### Alternative 4: Continue with K8s API Only

**Pros:**
- Already implemented
- Zero additional cost
- Simple

**Cons:**
- Rate limit concerns
- No history
- No search
- Poor scalability
- Limited functionality

**Verdict:** ❌ Doesn't address limitations

### Alternative 5: Self-Hosted Loki (Proposed)

**Pros:**
- Lightweight (~500m CPU, 1Gi memory)
- No external costs ($2/month storage only)
- Powerful LogQL search
- Historical logs (7-30 days)
- No rate limits
- Foundation for future observability

**Cons:**
- Initial setup time (8-12 hours)
- Minimal maintenance required
- Storage management

**Verdict:** ✅ **BEST OPTION**

---

## Risk Assessment

### Technical Risks

#### Risk 1: Storage Exhaustion

**Likelihood:** Low
**Impact:** Medium
**Mitigation:**
- Start with 7-day retention (very conservative)
- Loki auto-deletes old logs
- Monitor storage usage via kubectl
- Can increase storage if needed (easy to scale)
- Alert at 80% storage usage

#### Risk 2: Resource Contention

**Likelihood:** Very Low
**Impact:** Low
**Mitigation:**
- Resource requests/limits configured
- Only 3.5% of cluster CPU
- Can reduce limits if needed
- Monitoring enabled

#### Risk 3: Loki Pod Failure

**Likelihood:** Low
**Impact:** Low (logs viewer only, not critical)
**Mitigation:**
- K8s API fallback always available
- Automatic pod restart on failure
- PersistentVolume preserves data
- Can switch source in UI

#### Risk 4: Query Performance

**Likelihood:** Low
**Impact:** Low
**Mitigation:**
- Limit queries to 5000 lines
- Time range restrictions
- Indexed queries (fast)
- 30s refresh rate (not real-time)

#### Risk 5: Initial Setup Complexity

**Likelihood:** Medium
**Impact:** Low
**Mitigation:**
- Well-documented process
- Terraform automation
- Tested approach
- Reversible (can disable)

### Operational Risks

#### Risk 1: Maintenance Burden

**Likelihood:** Low
**Impact:** Low
**Mitigation:**
- Minimal maintenance required
- Automated cleanup
- Stateless Promtail (restarts easily)
- Well-supported Helm chart

#### Risk 2: Version Compatibility

**Likelihood:** Low
**Impact:** Low
**Mitigation:**
- Use stable Helm chart version
- Pin Loki version
- Test upgrades in staging first

### Mitigation Summary

All identified risks are **Low** or **Very Low** likelihood with **Low** to **Medium** impact. The solution is low-risk with significant benefits.

---

## Success Metrics

### Key Performance Indicators

#### 1. API Rate Reduction

**Baseline:** 72 K8s API calls/min
**Target:** <10 K8s API calls/min
**Measurement:** Monitor via K8s API server metrics

#### 2. Log History Availability

**Baseline:** 0 days
**Target:** 7-30 days
**Measurement:** Query Loki for logs from N days ago

#### 3. Resource Usage

**Target:** <500m CPU, <1Gi memory
**Measurement:** `kubectl top pod -n aicallgo-staging-monitoring`

#### 4. Storage Usage

**Target:** <10Gi total, <300MB/day ingestion
**Measurement:** `kubectl exec loki-0 -- df -h /loki`

#### 5. User Experience

**Target:** Logs load in <5 seconds
**Measurement:** User feedback, page load times

#### 6. Search Functionality

**Target:** LogQL queries return results in <3 seconds
**Measurement:** Admin Board query timing

### Monitoring Plan

**Weekly Checks (First Month):**
- Storage usage trend
- Resource consumption
- Query performance
- Error rates in Loki logs

**Monthly Checks (Ongoing):**
- Storage retention validation
- Helm chart version updates
- Cost tracking

**Alerts to Configure:**
- Storage >80% full
- Loki pod restarts >3 in 1 hour
- Query latency >10 seconds
- Promtail pods unhealthy

---

## Conclusion

Deploying self-hosted Loki on our DOKS cluster provides significant benefits for the Admin Board's log viewing capabilities while maintaining minimal infrastructure costs and resource usage.

**Summary:**
- **Cost:** $2/month (storage only)
- **Resources:** ~500m CPU, ~1Gi memory (3% of cluster)
- **Benefits:** 97% API rate reduction, 7-30 days history, powerful search
- **Implementation:** 8-12 hours
- **ROI:** 75x-125x
- **Risk:** Low

**Recommendation:** ✅ **Proceed with implementation**

This solution addresses all current limitations, scales well with growth, and provides a foundation for future observability improvements.

---

## Appendix

### A. Useful Loki Queries (LogQL)

```logql
# All logs for a service
{namespace="aicallgo-staging", app="web-backend"}

# Errors only
{namespace="aicallgo-staging"} |= "ERROR"

# Exclude health checks
{namespace="aicallgo-staging"} != "/health"

# HTTP 500 errors
{namespace="aicallgo-staging"} | json | status_code >= 500

# Specific time range
{namespace="aicallgo-staging"} [1h]

# Count errors per service
count_over_time({namespace="aicallgo-staging"} |= "ERROR" [5m])

# Rate of logs
rate({namespace="aicallgo-staging"}[5m])

# Multiple filters
{namespace="aicallgo-staging", app="web-backend"} |= "ERROR" | json | user_id="123"

# Regex matching
{namespace="aicallgo-staging"} |~ "error|ERROR|Error"
```

### B. Terraform Commands Reference

```bash
# Initialize
terraform init

# Validate
terraform validate

# Format
terraform fmt -recursive

# Plan specific module
terraform plan -target=module.loki

# Apply specific module
terraform apply -target=module.loki

# Show module outputs
terraform output loki_url

# Destroy module (if needed)
terraform destroy -target=module.loki

# Show state
terraform state list | grep loki
```

### C. Kubernetes Commands Reference

```bash
# Loki pod status
kubectl get pods -n aicallgo-staging-monitoring -l app.kubernetes.io/name=loki

# Loki logs
kubectl logs -n aicallgo-staging-monitoring loki-0 -f

# Promtail logs
kubectl logs -n aicallgo-staging-monitoring -l app.kubernetes.io/name=promtail -f

# Resource usage
kubectl top pod -n aicallgo-staging-monitoring

# Storage info
kubectl get pvc -n aicallgo-staging-monitoring

# Exec into Loki pod
kubectl exec -it -n aicallgo-staging-monitoring loki-0 -- sh

# Port-forward for testing
kubectl port-forward -n aicallgo-staging-monitoring svc/loki 3100:3100

# Restart Loki
kubectl rollout restart statefulset/loki -n aicallgo-staging-monitoring

# Scale Promtail
kubectl scale daemonset/loki-promtail -n aicallgo-staging-monitoring --replicas=0
```

### D. Troubleshooting Guide

**Issue:** Loki pod not starting

```bash
# Check pod status
kubectl describe pod -n aicallgo-staging-monitoring loki-0

# Common causes:
# - PVC not bound: Check pvc status
# - Resource limits: Check node capacity
# - Image pull errors: Check image name/tag
```

**Issue:** No logs appearing

```bash
# Check Promtail status
kubectl get pods -n aicallgo-staging-monitoring -l app.kubernetes.io/name=promtail

# Check Promtail logs
kubectl logs -n aicallgo-staging-monitoring -l app.kubernetes.io/name=promtail

# Common causes:
# - Promtail not running on all nodes
# - Namespace filter misconfigured
# - Promtail can't reach Loki
```

**Issue:** Query errors in Admin Board

```bash
# Check Loki service
kubectl get svc -n aicallgo-staging-monitoring loki

# Test from admin-board pod
kubectl exec -it -n aicallgo-staging admin-board-xxx -- curl http://loki.aicallgo-staging-monitoring.svc.cluster.local:3100/ready

# Common causes:
# - Service name incorrect
# - Network policy blocking
# - Loki pod unhealthy
```

**Issue:** High resource usage

```bash
# Check resource usage
kubectl top pod -n aicallgo-staging-monitoring loki-0

# Reduce limits if needed
kubectl set resources statefulset/loki -n aicallgo-staging-monitoring \
  --limits=cpu=100m,memory=256Mi

# Or reduce retention period in Terraform
```

### E. References

- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Loki Helm Chart](https://github.com/grafana/helm-charts/tree/main/charts/loki)
- [LogQL Syntax](https://grafana.com/docs/loki/latest/logql/)
- [Promtail Configuration](https://grafana.com/docs/loki/latest/clients/promtail/)
- [Digital Ocean DOKS Docs](https://docs.digitalocean.com/products/kubernetes/)

---

**Document Version:** 1.0
**Last Updated:** 2025-10-23
**Next Review:** After implementation
