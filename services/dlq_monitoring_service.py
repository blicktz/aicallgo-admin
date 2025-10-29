"""
Dead Letter Queue (DLQ) monitoring service.

Monitors failed call log operations and retry queue status.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

from services.redis_service import get_redis_service, DLQMessage

logger = logging.getLogger(__name__)


class DLQMonitoringService:
    """Service for monitoring dead letter queue."""

    def __init__(self):
        """Initialize DLQ monitoring service."""
        self.redis_service = get_redis_service()

    async def get_dlq_summary(self) -> Dict[str, Any]:
        """Get DLQ summary with depth and recent messages.

        Returns:
            Dict with:
                - depth: Number of messages in queue
                - has_failures: Boolean if queue has items
                - recent_messages: List of recent DLQ messages
        """
        try:
            depth = await self.redis_service.get_dlq_depth()
            messages = await self.redis_service.get_dlq_messages(limit=10)

            return {
                "depth": depth,
                "has_failures": depth > 0,
                "recent_messages": self._format_messages(messages),
            }

        except Exception as e:
            logger.error(f"Error getting DLQ summary: {str(e)}", exc_info=True)
            return {
                "depth": 0,
                "has_failures": False,
                "recent_messages": [],
            }

    async def get_dlq_depth(self) -> int:
        """Get number of messages in DLQ.

        Returns:
            int: Queue depth
        """
        try:
            return await self.redis_service.get_dlq_depth()
        except Exception as e:
            logger.error(f"Error getting DLQ depth: {str(e)}", exc_info=True)
            return 0

    async def get_dlq_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent DLQ messages formatted for display.

        Args:
            limit: Maximum number of messages to retrieve

        Returns:
            List[Dict]: Formatted DLQ messages
        """
        try:
            messages = await self.redis_service.get_dlq_messages(limit)
            return self._format_messages(messages)
        except Exception as e:
            logger.error(f"Error getting DLQ messages: {str(e)}", exc_info=True)
            return []

    def _format_messages(self, messages: List[DLQMessage]) -> List[Dict[str, Any]]:
        """Format DLQ messages for display.

        Args:
            messages: List of DLQMessage objects

        Returns:
            List[Dict]: Formatted message data
        """
        formatted = []

        for msg in messages:
            # Calculate time until next retry
            retry_in = None
            if msg.next_retry_at:
                delta = msg.next_retry_at - datetime.utcnow()
                if delta.total_seconds() > 0:
                    retry_in = self._format_timedelta(delta)
                else:
                    retry_in = "Overdue"

            formatted.append({
                "call_sid": msg.call_sid,
                "action": msg.action,
                "retry_status": f"{msg.retry_count}/{msg.max_retries}",
                "retry_count": msg.retry_count,
                "max_retries": msg.max_retries,
                "error_message": self._truncate_error(msg.error_message),
                "full_error": msg.error_message,
                "next_retry_at": msg.next_retry_at,
                "retry_in": retry_in,
                "is_final_failure": msg.retry_count >= msg.max_retries,
            })

        return formatted

    def _format_timedelta(self, delta: timedelta) -> str:
        """Format timedelta for display.

        Args:
            delta: Time delta

        Returns:
            str: Formatted string like "2m 30s" or "1h 15m"
        """
        total_seconds = int(delta.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def _truncate_error(self, error: str, max_length: int = 100) -> str:
        """Truncate error message for display.

        Args:
            error: Error message
            max_length: Maximum length

        Returns:
            str: Truncated error message
        """
        if not error:
            return ""

        if len(error) <= max_length:
            return error

        return error[:max_length] + "..."


def get_dlq_monitoring_service() -> DLQMonitoringService:
    """Get DLQ monitoring service instance.

    Returns:
        DLQMonitoringService: Service instance
    """
    return DLQMonitoringService()
