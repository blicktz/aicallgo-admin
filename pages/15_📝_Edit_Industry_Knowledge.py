"""
Edit Industry Knowledge page for AI Agent configurations.
Allows editing of customized fields (information_to_provide, fallback_procedure)
while preserving template fields.
"""
import streamlit as st
from database.connection import get_session
from services.agent_service import get_agent_by_id, update_industry_knowledge
import logging

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Edit Industry Knowledge",
    page_icon="📝",
    layout="wide"
)

st.title("📝 Edit Industry Knowledge")


def render_breadcrumb(business_name: str):
    """Render breadcrumb navigation."""
    st.markdown(
        f"**Navigation:** [Agents](../4_🤖_Agents) → {business_name} → Edit Industry Knowledge"
    )
    st.markdown("---")


def render_call_type_form(call_type: dict, key_prefix: str):
    """
    Render form fields for a single call type.

    Args:
        call_type: Call type dictionary from industry knowledge
        key_prefix: Unique prefix for Streamlit widget keys

    Returns:
        Dictionary with updated values
    """
    call_type_name = call_type.get("call_type_name", "Unknown")

    st.subheader(f"📞 {call_type_name}")

    # Read-only sections (displayed as info)
    with st.expander("📋 Call Type Details (Template - Read Only)", expanded=False):
        st.markdown("**Caller Intent:**")
        st.info(call_type.get("caller_intent", "N/A"))

        st.markdown("**Agent Primary Goal:**")
        st.info(call_type.get("agent_primary_goal", "N/A"))

        # Conversation flow
        conversation_flow = call_type.get("conversation_flow", {})
        if conversation_flow:
            st.markdown("**Empathy Statement:**")
            st.info(conversation_flow.get("empathy_statement", "N/A"))

            st.markdown("**Key Questions:**")
            key_questions = conversation_flow.get("key_questions", [])
            if key_questions:
                for i, question in enumerate(key_questions, 1):
                    st.markdown(f"{i}. {question}")
            else:
                st.info("No key questions defined")

        st.markdown("**Desired Outcome:**")
        st.info(call_type.get("desired_outcome", "N/A"))

        # Urgency metadata (if present)
        urgency_level = call_type.get("urgency_level")
        requires_same_day = call_type.get("requires_same_day")
        can_self_diagnose = call_type.get("can_self_diagnose")

        if urgency_level or requires_same_day is not None or can_self_diagnose is not None:
            st.markdown("**Urgency Metadata:**")
            cols = st.columns(3)
            if urgency_level:
                cols[0].metric("Urgency Level", urgency_level.title())
            if requires_same_day is not None:
                cols[1].metric("Same Day Required", "Yes" if requires_same_day else "No")
            if can_self_diagnose is not None:
                cols[2].metric("Can Self Diagnose", "Yes" if can_self_diagnose else "No")

    st.markdown("---")

    # Editable fields
    st.markdown("### ✏️ Editable Fields")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Information to Provide** *(Customized for this business)*")
        # information_to_provide is nested inside conversation_flow
        conversation_flow = call_type.get("conversation_flow", {})
        information_to_provide = st.text_area(
            "What information should the agent provide to the caller?",
            value=conversation_flow.get("information_to_provide", ""),
            height=200,
            key=f"{key_prefix}_info",
            help="Business-specific information the AI should share with callers for this call type"
        )
        char_count_info = len(information_to_provide)
        st.caption(f"Characters: {char_count_info}")

    with col2:
        st.markdown("**Fallback Procedure** *(What to do when AI can't help)*")
        fallback_procedure = st.text_area(
            "What should happen if the agent cannot fully assist?",
            value=call_type.get("fallback_procedure", ""),
            height=200,
            key=f"{key_prefix}_fallback",
            help="Fallback steps when the AI cannot provide a complete solution"
        )
        char_count_fallback = len(fallback_procedure)
        st.caption(f"Characters: {char_count_fallback}")

    return {
        "call_type_name": call_type_name,
        "information_to_provide": information_to_provide,
        "fallback_procedure": fallback_procedure
    }


def main():
    """Main function for Edit Industry Knowledge page."""

    # Get agent_id from session_state (fallback to query_params for direct URL access)
    # Note: st.switch_page() clears query_params, so we use session_state
    # Move temporary session state to persistent session state for this page
    if "edit_agent_id" in st.session_state:
        st.session_state.current_edit_agent_id = st.session_state.edit_agent_id
        st.session_state.current_edit_business_name = st.session_state.edit_business_name
        del st.session_state.edit_agent_id
        del st.session_state.edit_business_name

    # Read from persistent session state (survives page reruns)
    agent_id = st.session_state.get("current_edit_agent_id") or st.query_params.get("agent_id")
    business_name = st.session_state.get("current_edit_business_name") or st.query_params.get("business_name", "Agent")

    if not agent_id:
        st.error("⚠️ No agent ID provided. Please navigate from the Agents page.")
        st.info("👈 Use the Agents page in the sidebar to select an agent.")
        return

    # Render breadcrumb
    render_breadcrumb(business_name)

    # Fetch agent data
    with st.spinner("Loading agent configuration..."):
        try:
            with get_session() as session:
                agent = get_agent_by_id(session, agent_id)

                if not agent:
                    st.error(f"❌ Agent not found with ID: {agent_id}")
                    return

                if not agent.customized_industry_knowledge:
                    st.warning("⚠️ This agent does not have industry knowledge configured.")
                    st.info("Industry knowledge is automatically generated when a business completes onboarding.")
                    return

                # Display business info header
                st.info(f"**Business:** {business_name} | **Agent:** {agent.agent_name}")

                industry_knowledge = agent.customized_industry_knowledge
                industry_name = industry_knowledge.get("display_name", industry_knowledge.get("industry", "Unknown"))
                call_types = industry_knowledge.get("call_types", [])

                st.markdown(f"**Industry:** {industry_name}")
                st.markdown(f"**Call Types:** {len(call_types)}")

                if not call_types:
                    st.warning("No call types defined in industry knowledge.")
                    return

                # Initialize session state for form data
                if "form_data" not in st.session_state:
                    st.session_state.form_data = {}

                if "unsaved_changes" not in st.session_state:
                    st.session_state.unsaved_changes = False

                # Create tabs for each call type
                tab_names = [ct.get("call_type_name", f"Call Type {i+1}") for i, ct in enumerate(call_types)]
                tabs = st.tabs(tab_names)

                # Collect updates from all tabs
                updates = []

                for i, (tab, call_type) in enumerate(zip(tabs, call_types)):
                    with tab:
                        key_prefix = f"ct_{i}"
                        update_data = render_call_type_form(call_type, key_prefix)
                        updates.append(update_data)

                st.markdown("---")

                # Action buttons
                col1, col2, col3 = st.columns([2, 1, 1])

                with col2:
                    cancel_button = st.button(
                        "❌ Cancel",
                        use_container_width=True,
                        help="Return to Agents page without saving"
                    )

                with col3:
                    save_button = st.button(
                        "💾 Save Changes",
                        type="primary",
                        use_container_width=True,
                        help="Save all changes to industry knowledge"
                    )

                # Handle cancel button
                if cancel_button:
                    st.info("Changes discarded. Redirecting to Agents page...")
                    st.session_state.unsaved_changes = False
                    # Note: Streamlit doesn't support redirect, user needs to click Agents page
                    st.markdown("👈 Click **Agents** in the sidebar to return.")

                # Handle save button
                if save_button:
                    # Validate required fields
                    validation_errors = []
                    for i, update in enumerate(updates):
                        if not update["information_to_provide"].strip():
                            validation_errors.append(f"'{update['call_type_name']}': Information to Provide is required")
                        if not update["fallback_procedure"].strip():
                            validation_errors.append(f"'{update['call_type_name']}': Fallback Procedure is required")

                    if validation_errors:
                        st.error("❌ Validation Errors:")
                        for error in validation_errors:
                            st.error(f"  • {error}")
                    else:
                        # Save changes
                        with st.spinner("Saving changes..."):
                            try:
                                result = update_industry_knowledge(
                                    agent_id=agent_id,
                                    call_types_updates=updates
                                )

                                st.session_state.unsaved_changes = False

                                # Update session state with fresh data from API response
                                if result and "customized_industry_knowledge" in result:
                                    st.session_state.fresh_industry_knowledge = result["customized_industry_knowledge"]
                                    logger.info(f"Updated session state with fresh data for agent {agent_id}")

                                logger.info(f"Successfully updated industry knowledge for agent {agent_id}")

                                # Clear all caches to ensure fresh data on navigation
                                st.cache_data.clear()

                                # Redirect to Agents page after successful save
                                st.switch_page("pages/4_🤖_Agents.py")

                            except Exception as e:
                                st.toast(f"❌ Failed to save changes: {str(e)}", icon="❌")
                                st.error(f"❌ Failed to save changes: {str(e)}")
                                logger.error(f"Failed to update industry knowledge: {e}", exc_info=True)

        except Exception as e:
            st.error(f"❌ Error loading agent: {str(e)}")
            logger.error(f"Error in Edit Industry Knowledge page: {e}", exc_info=True)


if __name__ == "__main__":
    main()
