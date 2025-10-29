"""
Call monitoring service for active call health tracking.

Provides enriched active call data with business information and health metrics.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select

from services.redis_service import get_redis_service, ActiveCall
from database.models import Business

logger = logging.getLogger(__name__)


class CallMonitoringService:
    """Service for monitoring active calls with enriched data."""

    def __init__(self):
        """Initialize call monitoring service."""
        self.redis_service = get_redis_service()

    async def get_active_calls_with_business(
        self, db_session: Session
    ) -> List[Dict[str, Any]]:
        """Get active calls enriched with business data.

        Args:
            db_session: Database session for business lookups

        Returns:
            List[Dict]: Active calls with business names and health status
        """
        try:
            # Get active calls from Redis
            active_calls = await self.redis_service.get_active_calls()

            if not active_calls:
                return []

            # Enrich with business data
            enriched_calls = []

            for call in active_calls:
                # Look up business name
                business_name = await self._get_business_name(
                    db_session, call.business_id
                )

                enriched_call = {
                    "call_sid": call.call_sid,
                    "from_phone": call.from_phone_number,
                    "to_phone": call.to_phone_number,
                    "business_id": call.business_id,
                    "business_name": business_name or "Unknown Business",
                    "start_time": call.start_time,
                    "duration_seconds": call.duration_seconds,
                    "last_heartbeat": call.last_heartbeat,
                    "heartbeat_age_seconds": call.heartbeat_age_seconds,
                    "health_status": call.health_status,
                    "call_log_id": call.call_log_id,
                }

                enriched_calls.append(enriched_call)

            return enriched_calls

        except Exception as e:
            logger.error(f"Error getting active calls: {str(e)}", exc_info=True)
            return []

    async def get_active_calls_count(self) -> int:
        """Get count of active calls.

        Returns:
            int: Number of active calls
        """
        try:
            active_calls = await self.redis_service.get_active_calls()
            return len(active_calls)
        except Exception as e:
            logger.error(f"Error getting active calls count: {str(e)}", exc_info=True)
            return 0

    async def get_stale_calls(self) -> List[ActiveCall]:
        """Get calls with stale heartbeats (> 2 minutes).

        Returns:
            List[ActiveCall]: Calls with stale heartbeats
        """
        try:
            active_calls = await self.redis_service.get_active_calls()
            stale_calls = [call for call in active_calls if call.health_status == "stale"]
            return stale_calls
        except Exception as e:
            logger.error(f"Error getting stale calls: {str(e)}", exc_info=True)
            return []

    async def get_health_summary(self) -> Dict[str, int]:
        """Get summary of call health status.

        Returns:
            Dict with counts: {"healthy": 5, "warning": 2, "stale": 1}
        """
        try:
            active_calls = await self.redis_service.get_active_calls()

            summary = {"healthy": 0, "warning": 0, "stale": 0}

            for call in active_calls:
                status = call.health_status
                if status in summary:
                    summary[status] += 1

            return summary

        except Exception as e:
            logger.error(f"Error getting health summary: {str(e)}", exc_info=True)
            return {"healthy": 0, "warning": 0, "stale": 0}

    async def _get_business_name(
        self, db_session: Session, business_id: str
    ) -> Optional[str]:
        """Look up business name from database.

        Args:
            db_session: Database session
            business_id: Business UUID string

        Returns:
            str: Business name or None
        """
        try:
            # Query business by ID
            stmt = select(Business).where(Business.id == business_id)
            result = db_session.execute(stmt)
            business = result.scalar_one_or_none()

            if business:
                return business.business_name or business.primary_business_phone_number

            return None

        except Exception as e:
            logger.warning(
                f"Error looking up business {business_id}: {str(e)}"
            )
            return None


def get_call_monitoring_service() -> CallMonitoringService:
    """Get call monitoring service instance.

    Returns:
        CallMonitoringService: Service instance
    """
    return CallMonitoringService()
