"""
Reconciliation job monitoring service.

Monitors and triggers reconciliation tasks for missing call log notifications.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


class ReconciliationService:
    """Service for monitoring and triggering reconciliation jobs."""

    def __init__(self):
        """Initialize reconciliation service."""
        self.web_backend_url = settings.WEB_BACKEND_URL
        self.api_key = settings.INTERNAL_API_KEY
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client.

        Returns:
            httpx.AsyncClient: HTTP client
        """
        if not self.client:
            self.client = httpx.AsyncClient(
                base_url=self.web_backend_url,
                headers={"X-API-Key": self.api_key},
                timeout=30.0,
            )
        return self.client

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def trigger_reconciliation(self) -> Dict[str, Any]:
        """Trigger manual reconciliation job.

        Returns:
            Dict with:
                - success: Boolean
                - message: Status message
                - task_id: Celery task ID if successful
                - error: Error message if failed
        """
        try:
            client = await self._get_client()

            # Call web-backend API to trigger reconciliation
            response = await client.post(
                "/api/v1/internal/admin/reconciliation/trigger"
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(
                    f"Reconciliation triggered successfully: task_id={data.get('task_id')}"
                )
                return {
                    "success": True,
                    "message": "Reconciliation job started",
                    "task_id": data.get("task_id"),
                    "triggered_at": datetime.utcnow(),
                }
            else:
                logger.error(
                    f"Failed to trigger reconciliation: status={response.status_code}"
                )
                return {
                    "success": False,
                    "message": f"Failed to trigger reconciliation: HTTP {response.status_code}",
                    "error": response.text,
                }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error triggering reconciliation: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "Connection error to web backend",
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"Error triggering reconciliation: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "Unexpected error",
                "error": str(e),
            }

    async def get_reconciliation_status(self) -> Dict[str, Any]:
        """Get status of last reconciliation run.

        Returns:
            Dict with:
                - last_run_at: Last run timestamp
                - status: success/error
                - missing_count: Number of missing notifications found
                - queued_count: Number of notifications queued
                - error: Error message if failed
        """
        try:
            client = await self._get_client()

            # Call web-backend API to get reconciliation status
            response = await client.get(
                "/api/v1/internal/admin/reconciliation/status"
            )

            if response.status_code == 200:
                data = response.json()

                # Parse last run time
                last_run_at = None
                if "last_run_at" in data:
                    try:
                        last_run_at = datetime.fromisoformat(data["last_run_at"])
                    except (ValueError, TypeError):
                        pass

                return {
                    "last_run_at": last_run_at,
                    "status": data.get("status", "unknown"),
                    "missing_count": data.get("missing_count", 0),
                    "queued_count": data.get("queued_count", 0),
                    "error": data.get("error"),
                }
            else:
                logger.warning(
                    f"Failed to get reconciliation status: status={response.status_code}"
                )
                return {
                    "last_run_at": None,
                    "status": "unknown",
                    "missing_count": 0,
                    "queued_count": 0,
                    "error": "Failed to fetch status",
                }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting reconciliation status: {str(e)}", exc_info=True)
            return {
                "last_run_at": None,
                "status": "error",
                "missing_count": 0,
                "queued_count": 0,
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"Error getting reconciliation status: {str(e)}", exc_info=True)
            return {
                "last_run_at": None,
                "status": "error",
                "missing_count": 0,
                "queued_count": 0,
                "error": str(e),
            }

    def format_last_run_time(self, last_run_at: Optional[datetime]) -> str:
        """Format last run time for display.

        Args:
            last_run_at: Last run timestamp

        Returns:
            str: Formatted time like "15 minutes ago" or "Never"
        """
        if not last_run_at:
            return "Never"

        delta = datetime.utcnow() - last_run_at
        total_seconds = int(delta.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s ago"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes}m ago"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours}h ago"
        else:
            days = total_seconds // 86400
            return f"{days}d ago"


def get_reconciliation_service() -> ReconciliationService:
    """Get reconciliation service instance.

    Returns:
        ReconciliationService: Service instance
    """
    return ReconciliationService()
