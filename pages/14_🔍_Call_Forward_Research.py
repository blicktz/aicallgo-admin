"""
Call Forward Research Page

Allows administrators to research carrier call forwarding instructions
for any phone number, independent of business records.
"""
import streamlit as st
import phonenumbers
from config.auth import require_auth
from services.carrier_service import research_carrier_by_phone
from components.carrier_lookup_display import (
    render_carrier_lookup_result,
    render_carrier_not_found,
    render_loading_message
)

# Auth check
if not require_auth():
    st.stop()

# Page config
st.title("🔍 Call Forward Research")
st.markdown(
    """
    Research carrier call forwarding instructions for any phone number.
    This tool performs a Twilio carrier lookup and retrieves (or researches)
    step-by-step instructions for setting up call forwarding.
    """
)

# Phone number normalization helper
def normalize_us_phone(phone: str) -> tuple[str | None, str]:
    """
    Normalize US phone number to E.164 format.

    Args:
        phone: Phone number in any US format

    Returns:
        Tuple of (normalized_e164, error_message)
        If successful, error_message is empty
        If failed, normalized_e164 is None
    """
    if not phone:
        return None, "Phone number is required"

    try:
        # Parse as US phone number
        parsed = phonenumbers.parse(phone, "US")

        # Validate it's a valid number
        if not phonenumbers.is_valid_number(parsed):
            return None, "Invalid US phone number"

        # Check it's actually a US number (country code 1)
        if parsed.country_code != 1:
            return None, "Only US phone numbers are supported"

        # Convert to E.164 format
        e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

        return e164, ""

    except phonenumbers.NumberParseException as e:
        return None, f"Could not parse phone number: {str(e)}"
    except Exception as e:
        return None, f"Error processing phone number: {str(e)}"


# === PHONE NUMBER INPUT SECTION ===
st.markdown("---")
st.subheader("📞 Enter Phone Number")

# Input field for phone number
phone_number_input = st.text_input(
    "Phone Number",
    placeholder="(408) 649-7070 or 408-649-7070 or 4086497070",
    help="Enter US phone number in any format - will be automatically converted to E.164",
    key="phone_number_input"
)

# Auto-normalize and display
normalized_phone = None
if phone_number_input:
    normalized_phone, error_msg = normalize_us_phone(phone_number_input)
    if normalized_phone:
        st.success(f"✓ Normalized to: **{normalized_phone}**")
    else:
        st.error(f"❌ {error_msg}")


# Format helper text
with st.expander("ℹ️ Phone Number Format Help"):
    st.markdown(
        """
        **Automatic Format Conversion:**

        Enter US phone numbers in any format - the system will automatically convert them to E.164 format.

        **Accepted US Formats:**
        - ✅ `4086497070` → converts to `+14086497070`
        - ✅ `408-649-7070` → converts to `+14086497070`
        - ✅ `(408) 649-7070` → converts to `+14086497070`
        - ✅ `+1 408-649-7070` → converts to `+14086497070`
        - ✅ `1-408-649-7070` → converts to `+14086497070`
        - ✅ `+14086497070` → already E.164, no change

        **Note:**
        - Only US phone numbers (country code +1) are supported
        - International numbers will be rejected
        """
    )

# Research button
research_button = st.button(
    "🔍 Research Carrier",
    type="primary",
    use_container_width=True,
    disabled=not normalized_phone  # Button only enabled if normalization successful
)

# === RESULTS SECTION ===
st.markdown("---")

# Initialize session state for results
if 'lookup_result' not in st.session_state:
    st.session_state.lookup_result = None
if 'last_searched_number' not in st.session_state:
    st.session_state.last_searched_number = None

# Handle research button click
if research_button and normalized_phone:
    # Clear previous results if searching a different number
    if st.session_state.last_searched_number != normalized_phone:
        st.session_state.lookup_result = None

    st.session_state.last_searched_number = normalized_phone

    # Show loading message
    with st.spinner("Researching carrier information..."):
        st.info(
            "**This may take up to 60 seconds**\n\n"
            "The system is:\n"
            "1. Looking up the carrier via Twilio\n"
            "2. Checking our database for instructions\n"
            "3. If needed, researching instructions using AI\n\n"
            "Please wait..."
        )

        # Perform carrier lookup with normalized E.164 phone number
        result = research_carrier_by_phone(normalized_phone)

        # Store result in session state
        st.session_state.lookup_result = result

# Display results if available
if st.session_state.lookup_result is not None:
    result = st.session_state.lookup_result

    if result:
        # Check if carrier was found
        if result.get("carrier_found"):
            st.subheader("📊 Carrier Information & Instructions")
            render_carrier_lookup_result(result)
        else:
            render_carrier_not_found()
    else:
        render_carrier_not_found()

    # Clear results button
    st.markdown("---")
    if st.button("🔄 Clear Results"):
        st.session_state.lookup_result = None
        st.session_state.last_searched_number = None
        st.rerun()
