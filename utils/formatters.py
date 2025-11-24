"""
Formatting utilities for consistent data display across admin board.
"""
from decimal import Decimal
from datetime import datetime, timedelta
import pytz
import phonenumbers
from phonenumbers import NumberParseException
import humanize
from typing import Optional


def format_currency(amount: Optional[Decimal | float | int], currency: str = "USD", signed: bool = False) -> str:
    """
    Format number as currency with proper symbol and decimals.

    Args:
        amount: Amount to format (can be None)
        currency: Currency code (default: USD)
        signed: If True, always show sign (+ or -) for non-zero values

    Returns:
        Formatted string like "$1,234.56" or "$0.00" if None

    Examples:
        format_currency(1234.56) -> "$1,234.56"
        format_currency(None) -> "$0.00"
        format_currency(-50.25) -> "-$50.25"
        format_currency(1234.56, signed=True) -> "+$1,234.56"
        format_currency(-50.25, signed=True) -> "-$50.25"
    """
    if amount is None:
        return "$0.00"

    if currency == "USD":
        if amount >= 0:
            prefix = "+" if signed and amount > 0 else ""
            return f"{prefix}${abs(amount):,.2f}"
        else:
            return f"-${abs(amount):,.2f}"

    return f"{amount:,.2f} {currency}"


def format_datetime(
    dt: Optional[datetime],
    timezone: str = "America/Los_Angeles",
    format_str: str = "%Y-%m-%d %H:%M %Z"
) -> str:
    """
    Format datetime with timezone conversion.

    Args:
        dt: Datetime to format (can be None)
        timezone: IANA timezone name
        format_str: strftime format string

    Returns:
        Formatted datetime string or "N/A" if None

    Examples:
        format_datetime(datetime.now()) -> "2024-10-22 14:30 PDT"
    """
    if dt is None:
        return "N/A"

    # Ensure datetime is timezone-aware
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    # Convert to specified timezone
    tz = pytz.timezone(timezone)
    local_dt = dt.astimezone(tz)

    return local_dt.strftime(format_str)


def format_date(dt: Optional[datetime], format_str: str = "%Y-%m-%d") -> str:
    """
    Format datetime as date only.

    Args:
        dt: Datetime to format (can be None)
        format_str: strftime format string

    Returns:
        Formatted date string or "N/A" if None
    """
    if dt is None:
        return "N/A"
    return dt.strftime(format_str)


def format_phone(phone: Optional[str], country: str = "US") -> str:
    """
    Format phone number to display format.

    Args:
        phone: Phone number in E.164 or any format
        country: Country code for parsing

    Returns:
        Formatted phone like "+1 (555) 123-4567" or original if parse fails

    Examples:
        format_phone("+15551234567") -> "+1 (555) 123-4567"
        format_phone("5551234567") -> "+1 (555) 123-4567"
    """
    if not phone:
        return "N/A"

    try:
        parsed = phonenumbers.parse(phone, country)
        return phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )
    except Exception:
        return phone  # Return original if parsing fails


def format_duration(seconds: Optional[int | float]) -> str:
    """
    Format duration in seconds to HH:MM:SS.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration like "01:23:45" or "N/A" if None

    Examples:
        format_duration(3665) -> "01:01:05"
        format_duration(45) -> "00:00:45"
    """
    if seconds is None:
        return "N/A"

    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def humanize_datetime(dt: Optional[datetime]) -> str:
    """
    Convert datetime to human-readable relative time.

    Args:
        dt: Datetime to humanize

    Returns:
        Humanized string like "2 hours ago" or "in 3 days"

    Examples:
        humanize_datetime(datetime.now() - timedelta(hours=2)) -> "2 hours ago"
    """
    if dt is None:
        return "N/A"

    # Ensure both datetimes are timezone-aware for comparison
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    now = datetime.now(pytz.utc)
    return humanize.naturaltime(now - dt)


def format_number_abbrev(num: Optional[int | float], decimals: int = 1) -> str:
    """
    Format large numbers with abbreviations (K, M, B).

    Args:
        num: Number to format
        decimals: Number of decimal places

    Returns:
        Abbreviated string like "1.2K", "3.4M", "5.6B"

    Examples:
        format_number_abbrev(1234) -> "1.2K"
        format_number_abbrev(1234567) -> "1.2M"
        format_number_abbrev(123) -> "123"
    """
    if num is None:
        return "0"

    num = float(num)

    if num < 1000:
        return f"{int(num)}"
    elif num < 1_000_000:
        return f"{num/1000:.{decimals}f}K"
    elif num < 1_000_000_000:
        return f"{num/1_000_000:.{decimals}f}M"
    else:
        return f"{num/1_000_000_000:.{decimals}f}B"


def format_percentage(value: Optional[float], decimals: int = 1) -> str:
    """
    Format number as percentage.

    Args:
        value: Value to format (0.25 = 25%)
        decimals: Number of decimal places

    Returns:
        Formatted percentage like "25.0%"
    """
    if value is None:
        return "0.0%"

    return f"{value * 100:.{decimals}f}%"


def format_status_badge(status: str) -> str:
    """
    Get emoji for common status values.

    Args:
        status: Status string

    Returns:
        Status with emoji prefix

    Examples:
        format_status_badge("active") -> "✅ Active"
        format_status_badge("failed") -> "❌ Failed"
    """
    status_map = {
        "active": "✅",
        "inactive": "⏸️",
        "trialing": "🎯",
        "past_due": "⚠️",
        "canceled": "❌",
        "unpaid": "💳",
        "answered_by_ai": "🤖",
        "forwarded": "📞",
        "missed": "📵",
        "voicemail": "📧",
    }

    emoji = status_map.get(status.lower(), "ℹ️")
    return f"{emoji} {status.title()}"


def format_tone_badge(tone: str) -> str:
    """
    Format agent tone with emoji.

    Args:
        tone: Agent tone (casual/cheerful/formal)

    Returns:
        Tone with emoji prefix

    Examples:
        format_tone_badge("casual") -> "😎 Casual"
        format_tone_badge("cheerful") -> "😊 Cheerful"
        format_tone_badge("formal") -> "🎩 Formal"
    """
    if not tone:
        return "N/A"

    tone_map = {
        "casual": "😎",
        "cheerful": "😊",
        "formal": "🎩",
    }

    emoji = tone_map.get(tone.lower(), "ℹ️")
    return f"{emoji} {tone.title()}"


def format_features_list(
    enable_1800_blocking: bool,
    enable_sales_detection: bool,
    enable_call_transfer: bool
) -> str:
    """
    Format enabled features as comma-separated list.

    Args:
        enable_1800_blocking: Whether 1-800 blocking is enabled
        enable_sales_detection: Whether sales detection is enabled
        enable_call_transfer: Whether call transfer is enabled

    Returns:
        Comma-separated list of enabled features or "None"

    Examples:
        format_features_list(True, True, False) -> "1-800 Blocking, Sales Detection"
        format_features_list(False, False, False) -> "None"
    """
    features = []
    if enable_1800_blocking:
        features.append("1-800 Blocking")
    if enable_sales_detection:
        features.append("Sales Detection")
    if enable_call_transfer:
        features.append("Call Transfer")

    return ", ".join(features) if features else "None"


def format_yes_no(value: Optional[bool]) -> str:
    """
    Format boolean as Yes/No with emoji.

    Args:
        value: Boolean value

    Returns:
        "✅ Yes" or "❌ No"

    Examples:
        format_yes_no(True) -> "✅ Yes"
        format_yes_no(False) -> "❌ No"
        format_yes_no(None) -> "❌ No"
    """
    if value is None:
        return "❌ No"
    return "✅ Yes" if value else "❌ No"


def format_enabled_disabled(value: Optional[bool]) -> str:
    """
    Format boolean as Enabled/Disabled with emoji.

    Args:
        value: Boolean value

    Returns:
        "✅ Enabled" or "❌ Disabled"

    Examples:
        format_enabled_disabled(True) -> "✅ Enabled"
        format_enabled_disabled(False) -> "❌ Disabled"
    """
    if value is None:
        return "❌ Disabled"
    return "✅ Enabled" if value else "❌ Disabled"


def parse_transcript_json(transcript_str: Optional[str]) -> dict:
    """
    Parse JSON transcript into structured format for chat display.

    Args:
        transcript_str: JSON string with transcript data or plain text

    Returns:
        Dict with:
            - messages: List of {role, content, timestamp} dicts
            - metadata: Call metadata dict
            - is_json: Boolean indicating if parsing succeeded

    Examples:
        >>> parse_transcript_json('{"messages": [...]}')
        {
            "messages": [
                {"role": "agent", "content": "Hello!", "timestamp": "2025-01-20T10:30:05Z"},
                {"role": "caller", "content": "Hi", "timestamp": "2025-01-20T10:30:12Z"}
            ],
            "metadata": {"call_sid": "CA123", "total_messages": 2},
            "is_json": True
        }
    """
    import json

    if not transcript_str:
        return {
            "messages": [],
            "metadata": {},
            "is_json": False
        }

    # Try to parse as JSON first
    try:
        data = json.loads(transcript_str)

        # Validate structure
        if isinstance(data, dict) and "messages" in data:
            messages = data.get("messages", [])
            metadata = data.get("call_metadata", {})

            return {
                "messages": messages,
                "metadata": metadata,
                "is_json": True
            }
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: treat as plain text transcript
    # Try to split by common patterns like "Agent:" or "Caller:"
    messages = []
    lines = transcript_str.split('\n')

    current_role = None
    current_content = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect role changes
        if line.lower().startswith(('agent:', 'ai:', 'assistant:')):
            # Save previous message
            if current_role and current_content:
                messages.append({
                    "role": "agent",
                    "content": ' '.join(current_content),
                    "timestamp": None
                })
            current_role = "agent"
            current_content = [line.split(':', 1)[1].strip()] if ':' in line else []

        elif line.lower().startswith(('caller:', 'user:', 'customer:')):
            # Save previous message
            if current_role and current_content:
                messages.append({
                    "role": "caller" if current_role == "caller" else "agent",
                    "content": ' '.join(current_content),
                    "timestamp": None
                })
            current_role = "caller"
            current_content = [line.split(':', 1)[1].strip()] if ':' in line else []

        else:
            # Continue current message
            if current_role:
                current_content.append(line)
            else:
                # No role detected yet, assume it's a caller message
                messages.append({
                    "role": "caller",
                    "content": line,
                    "timestamp": None
                })

    # Add final message
    if current_role and current_content:
        messages.append({
            "role": current_role,
            "content": ' '.join(current_content),
            "timestamp": None
        })

    # If no structured messages found, return the whole text as one message
    if not messages:
        messages = [{
            "role": "agent",
            "content": transcript_str,
            "timestamp": None
        }]

    return {
        "messages": messages,
        "metadata": {},
        "is_json": False
    }


def normalize_phone_number(phone_input: str, country: str = "US") -> Optional[str]:
    """
    Normalize phone number to E.164 format for exact matching.

    Args:
        phone_input: Phone number in any format
        country: Country code for parsing (default: US)

    Returns:
        E.164 formatted phone number (e.g., "+15551234567") or None if invalid

    Examples:
        normalize_phone_number("(555) 123-4567") -> "+15551234567"
        normalize_phone_number("+1 555-123-4567") -> "+15551234567"
        normalize_phone_number("invalid") -> None
    """
    if not phone_input or not phone_input.strip():
        return None

    try:
        # Parse the phone number
        parsed = phonenumbers.parse(phone_input, country)

        # Validate before formatting
        if not phonenumbers.is_valid_number(parsed):
            return None

        # Format to E.164
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

    except NumberParseException:
        return None
    except Exception:
        return None
