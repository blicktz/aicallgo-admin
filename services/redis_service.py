"""
Redis service for real-time call monitoring.

Provides async Redis client for subscribing to call logging channels
and querying active call data.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import redis.asyncio as aioredis
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ActiveCall:
    """Active call data structure."""
    call_sid: str
    business_id: str
    from_phone_number: str
    to_phone_number: str
    start_time: datetime
    last_heartbeat: Optional[datetime]
    call_log_id: Optional[str]
    health_status: str  # "healthy", "warning", "stale"

    @property
    def duration_seconds(self) -> int:
        """Calculate call duration in seconds."""
        return int((datetime.utcnow() - self.start_time).total_seconds())

    @property
    def heartbeat_age_seconds(self) -> Optional[int]:
        """Calculate seconds since last heartbeat."""
        if not self.last_heartbeat:
            return None
        return int((datetime.utcnow() - self.last_heartbeat).total_seconds())


@dataclass
class DLQMessage:
    """Dead letter queue message structure."""
    call_sid: str
    action: str
    retry_count: int
    max_retries: int
    error_message: str
    next_retry_at: Optional[datetime]
    original_data: Dict[str, Any]


@dataclass
class ChannelStats:
    """Redis channel statistics."""
    channel_name: str
    is_connected: bool
    messages_received: int
    last_message_at: Optional[datetime]


class RedisService:
    """Redis service for call monitoring.

    Manages connections to Redis channels and provides methods to:
    - Get active calls from Redis context keys
    - Subscribe to heartbeat, call_logs, and DLQ channels
    - Query channel statistics
    """

    # Health status thresholds (seconds)
    HEALTHY_THRESHOLD = 60
    WARNING_THRESHOLD = 120

    # Channel names (matching web-backend)
    CHANNEL_CALL_LOGS = "call_logs"
    CHANNEL_HEARTBEAT = "call_heartbeat"
    CHANNEL_DLQ = "call_logs_dlq"

    def __init__(self):
        """Initialize Redis service."""
        self.redis_client: Optional[aioredis.Redis] = None
        self.is_connected = False
        self._connection_pool: Optional[aioredis.ConnectionPool] = None

    async def connect(self) -> bool:
        """Connect to Redis.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if not self._connection_pool:
                self._connection_pool = aioredis.ConnectionPool.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    max_connections=10,
                )

            if not self.redis_client:
                self.redis_client = aioredis.Redis(connection_pool=self._connection_pool)

            # Test connection
            await self.redis_client.ping()
            self.is_connected = True
            logger.info("Connected to Redis successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}", exc_info=True)
            self.is_connected = False
            return False

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

        if self._connection_pool:
            await self._connection_pool.disconnect()
            self._connection_pool = None

        self.is_connected = False
        logger.info("Disconnected from Redis")

    async def get_active_calls(self) -> List[ActiveCall]:
        """Get all active calls from Redis context keys.

        Scans for call_ctx:* keys and parses call data.

        Returns:
            List[ActiveCall]: List of active calls with health status
        """
        if not self.redis_client or not self.is_connected:
            await self.connect()

        if not self.is_connected:
            return []

        try:
            active_calls = []

            # Scan for call_ctx:* keys
            async for key in self.redis_client.scan_iter(match="call_ctx:*", count=100):
                call_sid = key.replace("call_ctx:", "")

                # Get call context data
                ctx_data = await self.redis_client.hgetall(key)

                if not ctx_data:
                    continue

                # Parse timestamps
                start_time = None
                if "start_time" in ctx_data:
                    try:
                        start_time = datetime.fromisoformat(ctx_data["start_time"])
                    except (ValueError, TypeError):
                        start_time = None

                # Get last heartbeat from separate key
                heartbeat_key = f"call_heartbeat:{call_sid}"
                last_heartbeat = None
                heartbeat_data = await self.redis_client.get(heartbeat_key)
                if heartbeat_data:
                    try:
                        heartbeat_timestamp = float(heartbeat_data)
                        last_heartbeat = datetime.fromtimestamp(heartbeat_timestamp)
                    except (ValueError, TypeError):
                        pass

                # Calculate health status
                health_status = self._calculate_health_status(last_heartbeat)

                # Create ActiveCall object
                active_call = ActiveCall(
                    call_sid=call_sid,
                    business_id=ctx_data.get("business_id", ""),
                    from_phone_number=ctx_data.get("from_phone_number", ""),
                    to_phone_number=ctx_data.get("to_phone_number", ""),
                    start_time=start_time or datetime.utcnow(),
                    last_heartbeat=last_heartbeat,
                    call_log_id=ctx_data.get("call_log_id"),
                    health_status=health_status,
                )

                active_calls.append(active_call)

            # Sort by start time (newest first)
            active_calls.sort(key=lambda x: x.start_time, reverse=True)

            logger.debug(f"Found {len(active_calls)} active calls")
            return active_calls

        except Exception as e:
            logger.error(f"Error getting active calls: {str(e)}", exc_info=True)
            return []

    async def get_dlq_messages(self, limit: int = 10) -> List[DLQMessage]:
        """Get messages from dead letter queue.

        Args:
            limit: Maximum number of messages to retrieve

        Returns:
            List[DLQMessage]: List of DLQ messages
        """
        if not self.redis_client or not self.is_connected:
            await self.connect()

        if not self.is_connected:
            return []

        try:
            messages = []

            # Get messages from DLQ list
            dlq_key = "call_logs_dlq_list"  # Assuming messages stored in a list
            raw_messages = await self.redis_client.lrange(dlq_key, 0, limit - 1)

            for raw_msg in raw_messages:
                try:
                    msg_data = json.loads(raw_msg)

                    # Parse next retry time
                    next_retry_at = None
                    if "next_retry_at" in msg_data:
                        try:
                            next_retry_at = datetime.fromisoformat(msg_data["next_retry_at"])
                        except (ValueError, TypeError):
                            pass

                    dlq_msg = DLQMessage(
                        call_sid=msg_data.get("call_sid", "unknown"),
                        action=msg_data.get("action", "unknown"),
                        retry_count=msg_data.get("retry_count", 0),
                        max_retries=msg_data.get("max_retries", 3),
                        error_message=msg_data.get("error", ""),
                        next_retry_at=next_retry_at,
                        original_data=msg_data.get("original_data", {}),
                    )

                    messages.append(dlq_msg)

                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse DLQ message: {raw_msg}")
                    continue

            return messages

        except Exception as e:
            logger.error(f"Error getting DLQ messages: {str(e)}", exc_info=True)
            return []

    async def get_dlq_depth(self) -> int:
        """Get number of messages in DLQ.

        Returns:
            int: Number of messages in queue
        """
        if not self.redis_client or not self.is_connected:
            await self.connect()

        if not self.is_connected:
            return 0

        try:
            dlq_key = "call_logs_dlq_list"
            depth = await self.redis_client.llen(dlq_key)
            return depth or 0

        except Exception as e:
            logger.error(f"Error getting DLQ depth: {str(e)}", exc_info=True)
            return 0

    async def get_channel_stats(self) -> Dict[str, ChannelStats]:
        """Get statistics for all monitored channels.

        Returns:
            Dict[str, ChannelStats]: Channel statistics keyed by channel name
        """
        # For now, return basic connection status
        # In a full implementation, we'd track message counts via subscribers
        stats = {
            self.CHANNEL_CALL_LOGS: ChannelStats(
                channel_name=self.CHANNEL_CALL_LOGS,
                is_connected=self.is_connected,
                messages_received=0,
                last_message_at=None,
            ),
            self.CHANNEL_HEARTBEAT: ChannelStats(
                channel_name=self.CHANNEL_HEARTBEAT,
                is_connected=self.is_connected,
                messages_received=0,
                last_message_at=None,
            ),
            self.CHANNEL_DLQ: ChannelStats(
                channel_name=self.CHANNEL_DLQ,
                is_connected=self.is_connected,
                messages_received=0,
                last_message_at=None,
            ),
        }

        return stats

    def _calculate_health_status(self, last_heartbeat: Optional[datetime]) -> str:
        """Calculate health status based on last heartbeat time.

        Args:
            last_heartbeat: Last heartbeat timestamp

        Returns:
            str: "healthy", "warning", or "stale"
        """
        if not last_heartbeat:
            return "warning"

        age_seconds = (datetime.utcnow() - last_heartbeat).total_seconds()

        if age_seconds < self.HEALTHY_THRESHOLD:
            return "healthy"
        elif age_seconds < self.WARNING_THRESHOLD:
            return "warning"
        else:
            return "stale"


# Singleton instance
_redis_service: Optional[RedisService] = None


def get_redis_service() -> RedisService:
    """Get or create Redis service singleton.

    Returns:
        RedisService: Singleton instance
    """
    global _redis_service

    if _redis_service is None:
        _redis_service = RedisService()

    return _redis_service
