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
    st.markdown("### ✏️ All Fields Are Editable")

    # Basic Information Section
    st.markdown("#### Basic Information")
    col1, col2 = st.columns(2)

    with col1:
        call_type_name = st.text_input(
            "Call Type Name",
            value=call_type.get("call_type_name", ""),
            key=f"{key_prefix}_name",
            help="Name of this call type"
        )

    with col2:
        urgency_level = st.selectbox(
            "Urgency Level",
            options=["emergency", "urgent", "routine"],
            index=["emergency", "urgent", "routine"].index(
                call_type.get("urgency_level", "routine")
            ) if call_type.get("urgency_level") in ["emergency", "urgent", "routine"] else 2,
            key=f"{key_prefix}_urgency",
            help="How urgent is this type of call?"
        )

    col3, col4 = st.columns(2)
    with col3:
        can_self_diagnose = st.checkbox(
            "Can Self Diagnose",
            value=call_type.get("can_self_diagnose", False),
            key=f"{key_prefix}_diagnose",
            help="Can the caller self-diagnose this issue?"
        )

    with col4:
        requires_same_day = st.checkbox(
            "Requires Same Day Service",
            value=call_type.get("requires_same_day", False),
            key=f"{key_prefix}_same_day",
            help="Does this typically require same-day service?"
        )

    st.markdown("---")

    # Intent and Goals Section
    st.markdown("#### Intent and Goals")

    caller_intent = st.text_area(
        "Caller Intent",
        value=call_type.get("caller_intent", ""),
        height=100,
        key=f"{key_prefix}_intent",
        help="What is the caller's intent when making this type of call?"
    )

    agent_primary_goal = st.text_area(
        "Agent Primary Goal",
        value=call_type.get("agent_primary_goal", ""),
        height=100,
        key=f"{key_prefix}_goal",
        help="What should the AI agent's primary goal be for this call type?"
    )

    desired_outcome = st.text_area(
        "Desired Outcome",
        value=call_type.get("desired_outcome", ""),
        height=100,
        key=f"{key_prefix}_outcome",
        help="What is the ideal outcome for this type of call?"
    )

    st.markdown("---")

    # Conversation Flow Section
    st.markdown("#### Conversation Flow")

    conversation_flow = call_type.get("conversation_flow", {})

    empathy_statement = st.text_area(
        "Empathy Statement",
        value=conversation_flow.get("empathy_statement", ""),
        height=80,
        key=f"{key_prefix}_empathy",
        help="Opening empathy statement the AI should use"
    )

    # Key Questions - Dynamic List
    st.markdown("**Key Questions**")
    st.caption("Questions the AI should ask during the call")

    # Initialize session state for key questions if not exists
    questions_key = f"{key_prefix}_questions"
    if questions_key not in st.session_state:
        st.session_state[questions_key] = conversation_flow.get("key_questions", [""])

    key_questions = []
    for i, question in enumerate(st.session_state[questions_key]):
        col_q, col_btn = st.columns([6, 1])
        with col_q:
            q_value = st.text_input(
                f"Question {i+1}",
                value=question,
                key=f"{key_prefix}_q_{i}",
                label_visibility="collapsed"
            )
            key_questions.append(q_value)
        with col_btn:
            if st.button("🗑️", key=f"{key_prefix}_del_{i}", help="Remove question"):
                st.session_state[questions_key].pop(i)
                st.rerun()

    if st.button("➕ Add Question", key=f"{key_prefix}_add_q"):
        st.session_state[questions_key].append("")
        st.rerun()

    # Filter out empty questions
    key_questions = [q for q in key_questions if q.strip()]

    col1, col2 = st.columns(2)

    with col1:
        information_to_provide = st.text_area(
            "Information to Provide",
            value=conversation_flow.get("information_to_provide", ""),
            height=150,
            key=f"{key_prefix}_info",
            help="Business-specific information the AI should share with callers"
        )

    with col2:
        fallback_procedure = st.text_area(
            "Fallback Procedure",
            value=call_type.get("fallback_procedure", ""),
            height=150,
            key=f"{key_prefix}_fallback",
            help="What to do when the AI cannot fully assist"
        )

    return {
        "call_type_name": call_type_name,
        "urgency_level": urgency_level,
        "can_self_diagnose": can_self_diagnose,
        "requires_same_day": requires_same_day,
        "caller_intent": caller_intent,
        "agent_primary_goal": agent_primary_goal,
        "desired_outcome": desired_outcome,
        "empathy_statement": empathy_statement,
        "key_questions": key_questions,
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
                        call_type_name = update["call_type_name"]

                        # Required text fields
                        if not call_type_name.strip():
                            validation_errors.append(f"Call Type #{i+1}: Call Type Name is required")
                        if not update["caller_intent"].strip():
                            validation_errors.append(f"'{call_type_name}': Caller Intent is required")
                        if not update["agent_primary_goal"].strip():
                            validation_errors.append(f"'{call_type_name}': Agent Primary Goal is required")
                        if not update["desired_outcome"].strip():
                            validation_errors.append(f"'{call_type_name}': Desired Outcome is required")
                        if not update["empathy_statement"].strip():
                            validation_errors.append(f"'{call_type_name}': Empathy Statement is required")
                        if not update["information_to_provide"].strip():
                            validation_errors.append(f"'{call_type_name}': Information to Provide is required")
                        if not update["fallback_procedure"].strip():
                            validation_errors.append(f"'{call_type_name}': Fallback Procedure is required")

                        # Key questions should have at least one
                        if not update["key_questions"] or len(update["key_questions"]) == 0:
                            validation_errors.append(f"'{call_type_name}': At least one Key Question is required")

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
