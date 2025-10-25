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
