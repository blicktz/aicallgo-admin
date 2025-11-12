"""
Agent service for database operations.
Provides read-only operations for Phase 2.
"""
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import Session, selectinload
from database.models import AIAgentConfiguration, Business, CustomQuestion, FAQ
from typing import Optional, List, Dict, Any
import logging
import requests
import os

logger = logging.getLogger(__name__)


def get_agents(
    session: Session,
    limit: int = 50,
    offset: int = 0,
    search_query: Optional[str] = None,
    tone_filter: Optional[str] = None,
    business_id: Optional[str] = None
) -> List[AIAgentConfiguration]:
    """
    Get AI agents with pagination and filters.

    Args:
        session: Database session
        limit: Maximum number of results
        offset: Pagination offset
        search_query: Search in agent name or business name
        tone_filter: Filter by agent tone (casual/cheerful/formal)
        business_id: Filter by business ID

    Returns:
        List of AIAgentConfiguration objects with business relationship loaded
    """
    try:
        query = select(AIAgentConfiguration).options(
            selectinload(AIAgentConfiguration.business)
        )

        # Apply search filter (search both agent name and business name)
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.join(Business).where(
                or_(
                    AIAgentConfiguration.agent_name.ilike(search_pattern),
                    Business.business_name.ilike(search_pattern)
                )
            )

        # Apply tone filter
        if tone_filter and tone_filter.lower() != "all":
            query = query.where(AIAgentConfiguration.tone == tone_filter.lower())

        # Apply business filter
        if business_id:
            query = query.where(AIAgentConfiguration.business_id == business_id)

        # Order by updated date (most recently updated first)
        query = query.order_by(desc(AIAgentConfiguration.updated_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = session.execute(query)
        agents = result.scalars().all()

        return list(agents)

    except Exception as e:
        logger.error(f"Error fetching agents: {e}")
        raise


def get_agent_by_id(
    session: Session,
    agent_id: str
) -> Optional[AIAgentConfiguration]:
    """
    Get agent by ID with all relationships loaded.

    Args:
        session: Database session
        agent_id: AIAgentConfiguration UUID

    Returns:
        AIAgentConfiguration object with relationships or None if not found
    """
    try:
        query = (
            select(AIAgentConfiguration)
            .options(
                selectinload(AIAgentConfiguration.business).selectinload(
                    Business.business_hours
                ),
                selectinload(AIAgentConfiguration.business).selectinload(
                    Business.core_services
                ),
                selectinload(AIAgentConfiguration.custom_questions),
                selectinload(AIAgentConfiguration.faq_list),
            )
            .where(AIAgentConfiguration.id == agent_id)
        )
        result = session.execute(query)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching agent {agent_id}: {e}")
        raise


def get_agent_by_business_id(
    session: Session,
    business_id: str
) -> Optional[AIAgentConfiguration]:
    """
    Get agent by business ID with relationships loaded.

    Args:
        session: Database session
        business_id: Business UUID

    Returns:
        AIAgentConfiguration object or None if not found
    """
    try:
        query = (
            select(AIAgentConfiguration)
            .options(
                selectinload(AIAgentConfiguration.business),
                selectinload(AIAgentConfiguration.custom_questions),
                selectinload(AIAgentConfiguration.faq_list),
            )
            .where(AIAgentConfiguration.business_id == business_id)
        )
        result = session.execute(query)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching agent for business {business_id}: {e}")
        raise


def get_agent_stats(session: Session) -> Dict[str, Any]:
    """
    Get agent statistics for dashboard.

    Returns:
        Dict with agent metrics:
        - total_agents: Total agent count
        - agents_with_faq: Agents with at least one FAQ
        - agents_with_custom_questions: Agents with custom questions
        - avg_faq_count: Average number of FAQs per agent
        - agents_with_call_transfer: Agents with call transfer enabled
    """
    try:
        # Total agents
        total_query = select(func.count(AIAgentConfiguration.id))
        total_result = session.execute(total_query)
        total_agents = total_result.scalar() or 0

        # Agents with FAQs (count distinct agent IDs that have FAQs)
        agents_with_faq_query = (
            select(func.count(func.distinct(FAQ.ai_agent_configuration_id)))
        )
        agents_with_faq_result = session.execute(agents_with_faq_query)
        agents_with_faq = agents_with_faq_result.scalar() or 0

        # Agents with custom questions
        agents_with_questions_query = (
            select(func.count(func.distinct(CustomQuestion.ai_agent_configuration_id)))
        )
        agents_with_questions_result = session.execute(agents_with_questions_query)
        agents_with_custom_questions = agents_with_questions_result.scalar() or 0

        # Average FAQ count per agent
        if total_agents > 0:
            avg_faq_query = select(func.count(FAQ.id))
            avg_faq_result = session.execute(avg_faq_query)
            total_faqs = avg_faq_result.scalar() or 0
            avg_faq_count = round(total_faqs / total_agents, 1)
        else:
            avg_faq_count = 0

        # Agents with call transfer enabled
        call_transfer_query = select(func.count(AIAgentConfiguration.id)).where(
            AIAgentConfiguration.enable_call_transfer == True
        )
        call_transfer_result = session.execute(call_transfer_query)
        agents_with_call_transfer = call_transfer_result.scalar() or 0

        return {
            "total_agents": total_agents,
            "agents_with_faq": agents_with_faq,
            "agents_with_custom_questions": agents_with_custom_questions,
            "avg_faq_count": avg_faq_count,
            "agents_with_call_transfer": agents_with_call_transfer,
        }

    except Exception as e:
        logger.error(f"Error fetching agent stats: {e}")
        raise


def get_recent_agent_updates(
    session: Session,
    limit: int = 10
) -> List[AIAgentConfiguration]:
    """
    Get most recently updated agents.

    Args:
        session: Database session
        limit: Number of recent agents to fetch

    Returns:
        List of recently updated AIAgentConfiguration objects with business loaded
    """
    try:
        query = (
            select(AIAgentConfiguration)
            .options(selectinload(AIAgentConfiguration.business))
            .order_by(desc(AIAgentConfiguration.updated_at))
            .limit(limit)
        )
        result = session.execute(query)
        return list(result.scalars().all())

    except Exception as e:
        logger.error(f"Error fetching recent agent updates: {e}")
        raise


def get_agent_count(session: Session) -> int:
    """
    Get total count of configured agents.

    Args:
        session: Database session

    Returns:
        Total number of agents
    """
    try:
        query = select(func.count(AIAgentConfiguration.id))
        result = session.execute(query)
        return result.scalar() or 0

    except Exception as e:
        logger.error(f"Error counting agents: {e}")
        raise


def update_industry_knowledge(
    agent_id: str,
    call_types_updates: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Update industry knowledge for an AI agent via admin API.

    Args:
        agent_id: UUID of the AI agent configuration
        call_types_updates: List of dictionaries with call_type_name and editable fields
            Example: [
                {
                    "call_type_name": "Emergency/Urgent Dental Pain",
                    "information_to_provide": "Updated info...",
                    "fallback_procedure": "Updated procedure..."
                }
            ]

    Returns:
        API response dictionary with updated industry knowledge

    Raises:
        Exception if API call fails
    """
    try:
        # Get API configuration from environment
        api_base_url = os.getenv("WEB_BACKEND_URL", "http://localhost:8000")
        internal_api_key = os.getenv("INTERNAL_API_KEY")

        if not internal_api_key:
            raise ValueError("INTERNAL_API_KEY environment variable not set")

        # Prepare API request
        url = f"{api_base_url}/api/v1/internal/admin/agents/{agent_id}/industry-knowledge"
        headers = {
            "Authorization": f"Bearer {internal_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "call_types": call_types_updates
        }

        logger.info(
            f"Updating industry knowledge for agent {agent_id} with {len(call_types_updates)} call types"
        )

        # Make PATCH request
        response = requests.patch(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        result = response.json()
        logger.info(f"Successfully updated industry knowledge for agent {agent_id}")

        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise Exception(f"Failed to update industry knowledge: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating industry knowledge: {e}")
        raise
