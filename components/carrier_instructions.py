"""
Carrier instructions component for displaying call forwarding setup.
"""
import streamlit as st
from typing import Dict, Any
import logging
import time

logger = logging.getLogger(__name__)


def render_carrier_research_section(business: Any):
    """
    Render carrier research/verification section with button to trigger research.

    Args:
        business: Business object with id and primary_business_phone_number

    Displays:
        - Status indicator (carrier status)
        - Button to research/verify carrier
        - Loading state during research (30+ seconds possible)
        - Success/warning/error messages
    """
    from services.carrier_service import research_carrier_for_business

    # Check if business has primary phone number
    if not business.primary_business_phone_number:
        return  # Don't show anything if no phone number

    st.markdown("### 🔍 Carrier Verification")

    # Create columns for status and button
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("**Verify that carrier instructions are available in the database**")
        st.caption("This ensures call forwarding instructions can be displayed correctly")

    with col2:
        # Research button
        if st.button("Research Carrier", use_container_width=True, type="primary"):
            # Store button click in session state
            st.session_state['research_clicked'] = True
            st.session_state['research_result'] = None

    # Handle research action
    if st.session_state.get('research_clicked', False):
        # Show loading state
        with st.spinner("🔬 Researching carrier instructions... This may take up to 60 seconds"):
            start_time = time.time()

            # Call research endpoint
            result = research_carrier_for_business(str(business.id))

            elapsed_time = time.time() - start_time

            # Store result in session state
            st.session_state['research_result'] = result
            st.session_state['research_elapsed_time'] = elapsed_time

        # Clear the clicked state
        st.session_state['research_clicked'] = False

        # Force rerun to show result
        st.rerun()

    # Display research result if available
    if st.session_state.get('research_result') is not None:
        result = st.session_state['research_result']
        elapsed_time = st.session_state.get('research_elapsed_time', 0)

        if result:
            # Success
            carrier_name = result.get("carrier_name", "Unknown")
            was_researched = result.get("was_researched", False)
            message = result.get("message", "")

            if was_researched:
                # New research was performed
                st.success(
                    f"✓ {message}\n\n"
                    f"**Carrier:** {carrier_name}\n\n"
                    f"**Research time:** {elapsed_time:.1f} seconds"
                )
            else:
                # Instructions already existed
                st.info(
                    f"ℹ️ {message}\n\n"
                    f"**Carrier:** {carrier_name}"
                )

            # Add clear button
            if st.button("Clear Result", use_container_width=True):
                st.session_state['research_result'] = None
                st.rerun()

        else:
            # Error or no result
            st.error(
                "❌ Failed to research carrier instructions.\n\n"
                "Possible reasons:\n"
                "- Business does not have a primary phone number configured\n"
                "- Carrier lookup failed\n"
                "- AI research service unavailable\n"
                "- Request timeout"
            )

            # Add retry button
            if st.button("Retry", use_container_width=True):
                st.session_state['research_clicked'] = True
                st.session_state['research_result'] = None
                st.rerun()


def render_carrier_instructions(business: Any):
    """
    Render carrier call forwarding instructions in a collapsible expander.

    Args:
        business: Business object with id and primary_business_phone_number

    Displays:
        - Carrier name and type
        - Primary dialer code (with copy button)
        - Detailed setup steps (collapsible)
        - Important notes (collapsible)
        - Conditional forwarding options (collapsible)
        - Disable methods (collapsible)
        - Help link to carrier support
    """
    from services.carrier_service import get_carrier_instructions
    from utils.formatters import format_phone

    # Check if business has primary phone number
    if not business.primary_business_phone_number:
        return  # Don't show anything if no phone number

    # Use expander (collapsed by default)
    with st.expander("📞 Call Forwarding Instructions", expanded=False):
        with st.spinner("Loading carrier instructions..."):
            instructions = get_carrier_instructions(str(business.id))

        if not instructions:
            st.warning(
                "⚠️ Could not load call forwarding instructions. "
                "This may be because the carrier could not be determined or instructions are not available."
            )
            return

        # Display carrier name and type
        carrier_name = instructions.get("carrier_name", "Unknown Carrier")
        carrier_type = instructions.get("carrier_type", "")

        st.markdown(f"**Carrier:** {carrier_name}")
        if carrier_type:
            # Display carrier type as a badge-like element
            type_colors = {
                "cellular": "🔵 Cellular",
                "voip": "🟢 VoIP",
                "landline": "🟡 Landline"
            }
            st.caption(type_colors.get(carrier_type, f"• {carrier_type.title()}"))

        st.markdown("---")

        # Primary setup method
        st.markdown("### Primary Setup Method")

        setup_code = instructions.get("setup_code")
        setup_steps = instructions.get("setup_steps")

        if setup_code:
            # Display dialer code prominently
            st.markdown("**Dial this code from the business phone:**")
            st.code(setup_code, language=None)
            st.caption("☝️ This code will forward calls to the AICallGO number")

        elif setup_steps:
            # Display manual steps
            st.markdown("**Follow these steps:**")
            for i, step in enumerate(setup_steps, 1):
                st.markdown(f"{i}. {step}")
        else:
            st.info("No setup instructions available for this carrier.")

        # Important notes (collapsible)
        notes = instructions.get("notes", [])
        if notes:
            with st.expander("⚠️ Important Notes", expanded=False):
                for note in notes:
                    st.markdown(f"- {note}")

        # Conditional forwarding options (collapsible)
        conditional = instructions.get("conditional_options")
        if conditional:
            has_conditional = any([
                conditional.get("busy", {}).get("supported"),
                conditional.get("no_answer", {}).get("supported"),
                conditional.get("unreachable", {}).get("supported")
            ])

            if has_conditional:
                with st.expander("🔀 Advanced: Conditional Forwarding", expanded=False):
                    st.caption("Forward calls only in specific scenarios:")

                    if conditional.get("busy", {}).get("supported"):
                        code = conditional["busy"].get("code")
                        st.markdown("**When Busy:**")
                        if code:
                            st.code(code, language=None)
                        else:
                            st.caption("Supported (check carrier for code)")

                    if conditional.get("no_answer", {}).get("supported"):
                        code = conditional["no_answer"].get("code")
                        st.markdown("**When No Answer:**")
                        if code:
                            st.code(code, language=None)
                        else:
                            st.caption("Supported (check carrier for code)")

                    if conditional.get("unreachable", {}).get("supported"):
                        code = conditional["unreachable"].get("code")
                        st.markdown("**When Unreachable:**")
                        if code:
                            st.code(code, language=None)
                        else:
                            st.caption("Supported (check carrier for code)")

        # Disable forwarding (collapsible)
        disable_code = instructions.get("disable_code")
        if disable_code:
            with st.expander("🚫 Disable Call Forwarding", expanded=False):
                st.markdown("To turn off call forwarding, dial:")
                st.code(disable_code, language=None)

        # Help link
        help_url = instructions.get("help_url")
        if help_url:
            st.markdown("---")
            st.markdown(f"📚 [Carrier Support Documentation]({help_url})")

        # Success message at the bottom
        st.success(
            "✓ After setting up call forwarding, test by calling your business number "
            "to ensure calls are being forwarded to AICallGO."
        )
