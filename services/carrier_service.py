"""
Carrier service for fetching call forwarding instructions.
Communicates with web-backend internal API.
"""
import requests
import logging
from typing import Optional, Dict, Any
from config.settings import settings

logger = logging.getLogger(__name__)


def get_carrier_instructions(business_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch carrier call forwarding instructions for a business's primary phone number.

    Args:
        business_id: UUID of the business

    Returns:
        Dict containing formatted carrier instructions, or None if not available

    The returned dict contains:
        - carrier_name: Display name of the carrier
        - carrier_type: "cellular", "voip", or "landline"
        - setup_code: Dialer code with phone number populated (e.g., "*72 +1-888-123-4567")
        - setup_steps: List of manual setup steps
        - disable_code: Code to disable forwarding
        - conditional_options: Dict with busy/no_answer/unreachable forwarding options
        - notes: List of important notes
        - help_url: Link to carrier support
    """
    try:
        # Construct API URL
        api_url = f"{settings.WEB_BACKEND_URL}/api/v1/internal/businesses/{business_id}/carrier-instructions"

        # Make request with internal API key auth
        headers = {
            "X-API-Key": settings.INTERNAL_API_KEY,
            "Content-Type": "application/json"
        }

        logger.info(
            f"Fetching carrier instructions for business {business_id}",
            extra={"business_id": business_id}
        )

        response = requests.get(
            api_url,
            headers=headers,
            timeout=30  # 30 second timeout (Twilio lookup can be slow)
        )

        # Check if request was successful
        if response.status_code == 200:
            instructions = response.json()
            logger.info(
                f"Successfully fetched carrier instructions",
                extra={
                    "business_id": business_id,
                    "carrier_name": instructions.get("carrier_name")
                }
            )
            return instructions

        elif response.status_code == 404:
            logger.warning(
                f"Carrier instructions not found for business",
                extra={"business_id": business_id, "status_code": 404}
            )
            return None

        elif response.status_code == 400:
            # Business doesn't have primary phone number
            logger.warning(
                f"Business does not have primary phone number configured",
                extra={"business_id": business_id}
            )
            return None

        else:
            logger.error(
                f"Failed to fetch carrier instructions",
                extra={
                    "business_id": business_id,
                    "status_code": response.status_code,
                    "response": response.text
                }
            )
            return None

    except requests.exceptions.Timeout:
        logger.error(
            f"Timeout fetching carrier instructions",
            extra={"business_id": business_id}
        )
        return None

    except requests.exceptions.RequestException as e:
        logger.error(
            f"Request error fetching carrier instructions: {e}",
            extra={"business_id": business_id},
            exc_info=True
        )
        return None

    except Exception as e:
        logger.error(
            f"Unexpected error fetching carrier instructions: {e}",
            extra={"business_id": business_id},
            exc_info=True
        )
        return None


def research_carrier_for_business(business_id: str) -> Optional[Dict[str, Any]]:
    """
    Trigger carrier research for a business's primary phone number.

    This function:
    1. Calls the web-backend internal API to research the carrier
    2. Backend performs Twilio lookup
    3. Checks if carrier instructions exist in database
    4. If not, triggers AI research using Perplexity Sonar (can take 30+ seconds)
    5. Returns status of the operation

    Args:
        business_id: UUID of the business

    Returns:
        Dict containing research status, or None if request failed

    The returned dict contains:
        - carrier_found: Boolean indicating if instructions exist/were created
        - carrier_name: Name of the carrier
        - carrier_key: Carrier key (if found)
        - carrier_type: Type of carrier (cellular, voip, landline)
        - was_researched: True if new research was performed
        - message: Status message for display
    """
    try:
        # Construct API URL
        api_url = f"{settings.WEB_BACKEND_URL}/api/v1/internal/businesses/{business_id}/research-carrier"

        # Make request with internal API key auth
        headers = {
            "X-API-Key": settings.INTERNAL_API_KEY,
            "Content-Type": "application/json"
        }

        logger.info(
            f"Triggering carrier research for business {business_id}",
            extra={"business_id": business_id}
        )

        # Use longer timeout for research (can take 30+ seconds)
        response = requests.post(
            api_url,
            headers=headers,
            timeout=60  # 60 second timeout for AI research
        )

        # Check if request was successful
        if response.status_code == 200:
            result = response.json()
            logger.info(
                f"Carrier research completed successfully",
                extra={
                    "business_id": business_id,
                    "carrier_name": result.get("carrier_name"),
                    "was_researched": result.get("was_researched")
                }
            )
            return result

        elif response.status_code == 404:
            logger.warning(
                f"Business not found or no primary phone number",
                extra={"business_id": business_id, "status_code": 404}
            )
            return None

        elif response.status_code == 400:
            # Business doesn't have primary phone number
            logger.warning(
                f"Business does not have primary phone number configured",
                extra={"business_id": business_id}
            )
            return None

        else:
            logger.error(
                f"Failed to research carrier",
                extra={
                    "business_id": business_id,
                    "status_code": response.status_code,
                    "response": response.text
                }
            )
            return None

    except requests.exceptions.Timeout:
        logger.error(
            f"Timeout researching carrier (operation took >60 seconds)",
            extra={"business_id": business_id}
        )
        return None

    except requests.exceptions.RequestException as e:
        logger.error(
            f"Request error researching carrier: {e}",
            extra={"business_id": business_id},
            exc_info=True
        )
        return None

    except Exception as e:
        logger.error(
            f"Unexpected error researching carrier: {e}",
            extra={"business_id": business_id},
            exc_info=True
        )
        return None
