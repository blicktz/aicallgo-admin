"""Phone number validation and E.164 formatting utilities."""
from typing import Tuple, Optional
import phonenumbers
from phonenumbers import NumberParseException


def validate_phone(phone: str, default_region: str = 'US') -> Tuple[bool, Optional[str]]:
    """Validate a phone number.

    Args:
        phone: Phone number string to validate
        default_region: Default country code for parsing (default: US)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone or not phone.strip():
        return False, "Phone number is empty"

    try:
        # Parse the phone number
        parsed = phonenumbers.parse(phone, default_region)

        # Check if valid
        if not phonenumbers.is_valid_number(parsed):
            return False, "Invalid phone number format"

        # Check if it's a possible number for the region
        if not phonenumbers.is_possible_number(parsed):
            return False, "Phone number is not possible for this region"

        return True, None

    except NumberParseException as e:
        error_messages = {
            NumberParseException.INVALID_COUNTRY_CODE: "Invalid country code",
            NumberParseException.NOT_A_NUMBER: "Not a valid phone number",
            NumberParseException.TOO_SHORT_NSN: "Phone number too short",
            NumberParseException.TOO_SHORT_AFTER_IDD: "Phone number too short",
            NumberParseException.TOO_LONG: "Phone number too long",
        }
        return False, error_messages.get(e.error_type, f"Invalid phone number: {str(e)}")
    except Exception as e:
        return False, f"Error validating phone: {str(e)}"


def format_e164(phone: str, default_region: str = 'US') -> Optional[str]:
    """Format phone number to E.164 format (+1234567890).

    Args:
        phone: Phone number string to format
        default_region: Default country code for parsing (default: US)

    Returns:
        E.164 formatted phone number or None if invalid
    """
    try:
        # Parse the phone number
        parsed = phonenumbers.parse(phone, default_region)

        # Validate before formatting
        if not phonenumbers.is_valid_number(parsed):
            return None

        # Format to E.164
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

    except NumberParseException:
        return None
    except Exception:
        return None


def format_international(phone: str, default_region: str = 'US') -> Optional[str]:
    """Format phone number to international format.

    Args:
        phone: Phone number string to format
        default_region: Default country code for parsing (default: US)

    Returns:
        International formatted phone number or None if invalid
    """
    try:
        parsed = phonenumbers.parse(phone, default_region)

        if not phonenumbers.is_valid_number(parsed):
            return None

        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)

    except NumberParseException:
        return None
    except Exception:
        return None


def format_national(phone: str, default_region: str = 'US') -> Optional[str]:
    """Format phone number to national format.

    Args:
        phone: Phone number string to format
        default_region: Default country code for parsing (default: US)

    Returns:
        National formatted phone number or None if invalid
    """
    try:
        parsed = phonenumbers.parse(phone, default_region)

        if not phonenumbers.is_valid_number(parsed):
            return None

        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)

    except NumberParseException:
        return None
    except Exception:
        return None


def get_country_code(phone: str, default_region: str = 'US') -> Optional[str]:
    """Extract country code from phone number.

    Args:
        phone: Phone number string
        default_region: Default country code for parsing (default: US)

    Returns:
        Country code (e.g., 'US', 'GB') or None if invalid
    """
    try:
        parsed = phonenumbers.parse(phone, default_region)

        if not phonenumbers.is_valid_number(parsed):
            return None

        return phonenumbers.region_code_for_number(parsed)

    except NumberParseException:
        return None
    except Exception:
        return None


def validate_and_format(phone: str, default_region: str = 'US') -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate and format phone number in one call.

    Args:
        phone: Phone number string to validate and format
        default_region: Default country code for parsing (default: US)

    Returns:
        Tuple of (is_valid, formatted_e164, error_message)
    """
    is_valid, error = validate_phone(phone, default_region)

    if not is_valid:
        return False, None, error

    formatted = format_e164(phone, default_region)

    if not formatted:
        return False, None, "Failed to format phone number"

    return True, formatted, None
