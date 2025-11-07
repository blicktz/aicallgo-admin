"""
Carrier Lookup Display Component

Displays carrier call forwarding information in an organized, flattened format.
All sections are visible (not collapsible) with clear visual organization.
"""
import streamlit as st
from typing import Dict, Any, Optional


def render_carrier_lookup_result(result: Dict[str, Any]) -> None:
    """
    Render carrier lookup results in a flattened, organized format.

    Args:
        result: Dictionary containing carrier information and instructions
    """
    if not result:
        st.info("No carrier information available.")
        return

    # Handle error responses
    if "error" in result:
        st.error(result["error"])
        return

    # Extract carrier information
    carrier_name = result.get("carrier_name", "Unknown")
    carrier_type = result.get("carrier_type", "unknown")
    carrier_key = result.get("carrier_key", "unknown")
    phone_number = result.get("phone_number", "")
    was_researched = result.get("was_researched", False)
    message = result.get("message", "")

    # Status message with research indicator
    if was_researched:
        st.success(f"✓ {message}")
        st.info("**Note**: This carrier was newly researched using AI. Instructions have been added to the database.")
    else:
        st.success(f"✓ {message}")

    # === CARRIER INFORMATION SECTION ===
    st.markdown("---")
    st.subheader("📱 Carrier Information")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Carrier Name", carrier_name)
    with col2:
        carrier_type_display = carrier_type.upper() if carrier_type else "UNKNOWN"
        st.metric("Carrier Type", carrier_type_display)
    with col3:
        st.metric("Carrier Key", carrier_key)

    if phone_number:
        st.info(f"**Phone Number Searched**: {phone_number}")

    # === SETUP INSTRUCTIONS SECTION ===
    setup_code = result.get("setup_code")
    setup_steps = result.get("setup_steps")

    if setup_code or setup_steps:
        st.markdown("---")
        st.subheader("🔧 Setup Instructions")

        if setup_code:
            st.markdown(f"**Dialer Code**:")
            st.code(setup_code, language=None)
            st.caption("Dial this code from your phone to enable call forwarding")

        if setup_steps:
            st.markdown("**Step-by-Step Instructions**:")
            for i, step in enumerate(setup_steps, 1):
                st.markdown(f"{i}. {step}")

    # === CONDITIONAL FORWARDING SECTION ===
    conditional_options = result.get("conditional_options")

    if conditional_options:
        st.markdown("---")
        st.subheader("🔀 Conditional Forwarding Options")

        st.markdown("Set up forwarding based on specific conditions:")

        # Busy forwarding
        if "busy" in conditional_options:
            busy = conditional_options["busy"]
            with st.container():
                st.markdown("**When Line is Busy**")
                if busy.get("supported"):
                    code = busy.get("code", "Not available")
                    st.code(code, language=None)
                else:
                    st.caption("❌ Not supported by this carrier")

        # No answer forwarding
        if "no_answer" in conditional_options:
            no_answer = conditional_options["no_answer"]
            with st.container():
                st.markdown("**When No Answer**")
                if no_answer.get("supported"):
                    code = no_answer.get("code", "Not available")
                    st.code(code, language=None)
                else:
                    st.caption("❌ Not supported by this carrier")

        # Unreachable forwarding
        if "unreachable" in conditional_options:
            unreachable = conditional_options["unreachable"]
            with st.container():
                st.markdown("**When Unreachable**")
                if unreachable.get("supported"):
                    code = unreachable.get("code", "Not available")
                    st.code(code, language=None)
                else:
                    st.caption("❌ Not supported by this carrier")

    # === DISABLE INSTRUCTIONS SECTION ===
    disable_code = result.get("disable_code")

    if disable_code:
        st.markdown("---")
        st.subheader("❌ Disable Call Forwarding")

        st.markdown(f"**Disable Code**:")
        st.code(disable_code, language=None)
        st.caption("Dial this code from your phone to turn off call forwarding")

    # === IMPORTANT NOTES SECTION ===
    notes = result.get("notes")

    if notes and len(notes) > 0:
        st.markdown("---")
        st.subheader("📋 Important Notes")

        for note in notes:
            st.warning(note)

    # === HELP & SUPPORT SECTION ===
    help_url = result.get("help_url")

    if help_url:
        st.markdown("---")
        st.subheader("🆘 Need Help?")

        st.markdown(f"For additional support, visit the carrier's help page:")
        st.markdown(f"[{carrier_name} Support]({help_url})")


def render_carrier_not_found() -> None:
    """Render message when carrier information is not found."""
    st.warning("Could not determine carrier for this phone number.")
    st.info(
        "This may occur if:\n"
        "- The phone number is invalid\n"
        "- The carrier lookup service is unavailable\n"
        "- The phone number is not in service"
    )


def render_loading_message() -> None:
    """Render loading message during carrier research."""
    with st.spinner("Researching carrier information..."):
        st.info(
            "**This may take up to 60 seconds**\n\n"
            "The system is:\n"
            "1. Looking up the carrier via Twilio\n"
            "2. Checking our database for instructions\n"
            "3. If needed, researching instructions using AI\n\n"
            "Please wait..."
        )
