"""
Scheduling service for managing appointment scheduling configurations.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session
from database.models import AppointmentSchedulingConfig, User
from typing import Optional
import logging
import uuid

logger = logging.getLogger(__name__)


def get_scheduling_config(session: Session, user_id: str) -> Optional[AppointmentSchedulingConfig]:
    """
    Get scheduling configuration for a user.

    Args:
        session: Database session
        user_id: User UUID as string

    Returns:
        AppointmentSchedulingConfig object or None if not found
    """
    try:
        query = select(AppointmentSchedulingConfig).where(
            AppointmentSchedulingConfig.user_id == uuid.UUID(user_id)
        )
        result = session.execute(query)
        config = result.scalar_one_or_none()
        return config

    except Exception as e:
        logger.error(f"Failed to get scheduling config for user {user_id}: {str(e)}")
        raise


def update_scheduling_config(
    session: Session,
    user_id: str,
    display_mode: str,
    window_minutes: int
) -> AppointmentSchedulingConfig:
    """
    Update scheduling configuration for a user.

    Args:
        session: Database session
        user_id: User UUID as string
        display_mode: "exact_time" or "time_range"
        window_minutes: Window duration in minutes (30, 60, 90, 120, 150, or 180)

    Returns:
        Updated AppointmentSchedulingConfig object

    Raises:
        ValueError: If display_mode or window_minutes is invalid
        Exception: If update fails
    """
    try:
        # Validate inputs
        valid_modes = ["exact_time", "time_range"]
        if display_mode not in valid_modes:
            raise ValueError(f"display_mode must be one of {valid_modes}")

        valid_durations = [30, 60, 90, 120, 150, 180]
        if window_minutes not in valid_durations:
            raise ValueError(f"window_minutes must be one of {valid_durations}")

        # Get existing config
        query = select(AppointmentSchedulingConfig).where(
            AppointmentSchedulingConfig.user_id == uuid.UUID(user_id)
        )
        result = session.execute(query)
        config = result.scalar_one_or_none()

        if not config:
            raise ValueError(f"No scheduling config found for user {user_id}")

        # Update fields
        config.appointment_time_display_mode = display_mode
        config.appointment_window_duration_minutes = window_minutes

        # Commit changes
        session.commit()
        session.refresh(config)

        logger.info(
            f"Updated scheduling config for user {user_id}: "
            f"display_mode={display_mode}, window_minutes={window_minutes}"
        )

        return config

    except ValueError:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to update scheduling config for user {user_id}: {str(e)}")
        raise


def get_user_id_from_agent(session: Session, agent_id: str) -> Optional[str]:
    """
    Get user_id from an AI agent configuration.

    Args:
        session: Database session
        agent_id: Agent UUID as string

    Returns:
        User UUID as string or None if not found
    """
    try:
        from database.models import AIAgentConfiguration

        query = select(AIAgentConfiguration).where(
            AIAgentConfiguration.id == uuid.UUID(agent_id)
        )
        result = session.execute(query)
        agent = result.scalar_one_or_none()

        if agent and agent.business_id:
            # Get user_id from business
            from database.models import Business

            business_query = select(Business).where(
                Business.id == agent.business_id
            )
            business_result = session.execute(business_query)
            business = business_result.scalar_one_or_none()

            if business:
                return str(business.user_id)

        return None

    except Exception as e:
        logger.error(f"Failed to get user_id from agent {agent_id}: {str(e)}")
        return None
