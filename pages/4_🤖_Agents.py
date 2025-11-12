"""
Agents - AI Agent configuration browsing with search and detail view
"""
import streamlit as st
import pandas as pd
import json
from config.auth import require_auth
from database.connection import get_session
from services.agent_service import get_agents, get_agent_by_id
from components.tables import render_dataframe
from utils.formatters import (
    format_datetime,
    format_phone,
    format_tone_badge,
    format_features_list,
    format_enabled_disabled,
    format_yes_no
)

# Auth check
if not require_auth():
    st.stop()

st.title("🤖 AI Agents")
st.markdown("Browse and manage AI agent configurations")

# Search and filters
search_query = st.text_input(
    "🔍 Search by agent or business name",
    placeholder="Enter agent or business name..."
)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    tone_filter = st.selectbox("Tone", ["all", "casual", "cheerful", "formal"])
with col2:
    # In the future, we can add business filter here
    pass
with col3:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# Initialize session state for selected agent
if "selected_agent_id" not in st.session_state:
    st.session_state.selected_agent_id = None

# Load agents
def load_agents(search, tone, page_num, per_page):
    """Load agents with filters"""
    with get_session() as session:
        offset = page_num * per_page
        return get_agents(
            session,
            limit=per_page,
            offset=offset,
            search_query=search if search else None,
            tone_filter=tone if tone != "all" else None
        )

# Main layout: table + detail panel (30% list, 70% details)
table_col, detail_col = st.columns([3, 7])

with table_col:
    st.markdown("### Agent List")

    try:
        agents = load_agents(search_query, tone_filter, 0, 50)

        if not agents:
            st.info("No agents found matching your criteria")
        else:
            # Convert to DataFrame
            agents_df = pd.DataFrame([
                {
                    "Agent Name": a.agent_name,
                    "Business": a.business.business_name if a.business else "N/A",
                    "Tone": a.tone.title() if a.tone else "N/A",
                    "ID": str(a.id)
                }
                for a in agents
            ])

            # Add selection handler
            st.markdown("*Click on a row to view details*")

            # Display DataFrame with row selection
            event = st.dataframe(
                agents_df.drop(columns=["ID"]),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                height=600
            )

            # Update selected agent ID if a row is selected
            if event and "selection" in event and "rows" in event["selection"]:
                if len(event["selection"]["rows"]) > 0:
                    selected_idx = event["selection"]["rows"][0]
                    selected_agent_id = agents_df.iloc[selected_idx]["ID"]
                    st.session_state.selected_agent_id = selected_agent_id

            # Show count
            st.caption(f"Showing {len(agents)} agents")

    except Exception as e:
        st.error(f"Failed to load agents: {str(e)}")

with detail_col:
    st.markdown("### Agent Details")

    if st.session_state.selected_agent_id:
        # Load full agent details
        def load_agent_details(agent_id):
            """Load agent details with related data"""
            with get_session() as session:
                agent = get_agent_by_id(session, agent_id)
                return agent

        try:
            agent = load_agent_details(st.session_state.selected_agent_id)

            if not agent:
                st.warning("Agent not found")
            else:
                # Basic Settings
                st.markdown("#### Basic Settings")
                st.markdown(f"**Agent Name:** {agent.agent_name}")
                st.markdown(f"**Tone:** {format_tone_badge(agent.tone)}")
                st.markdown(f"**Business:** {agent.business.business_name if agent.business else 'N/A'}")
                st.markdown(f"**Max Call Duration:** {agent.max_call_duration_minutes} minutes")

                st.divider()

                # Messages
                st.markdown("#### Messages")
                with st.expander("📝 Greeting Message", expanded=False):
                    st.text_area(
                        "",
                        agent.greeting_message,
                        disabled=True,
                        key="greeting",
                        height=100
                    )

                with st.expander("📧 Voicemail Instructions", expanded=False):
                    st.text_area(
                        "",
                        agent.voicemail_instructions,
                        disabled=True,
                        key="voicemail",
                        height=100
                    )

                with st.expander("⚖️ Legal Disclaimer", expanded=False):
                    st.text_area(
                        "",
                        agent.legal_disclaimer_template,
                        disabled=True,
                        key="disclaimer",
                        height=100
                    )

                st.divider()

                # Features
                st.markdown("#### Features")
                st.markdown(f"**1-800 Blocking:** {format_enabled_disabled(agent.enable_1800_blocking)}")
                st.markdown(f"**Sales Detection:** {format_enabled_disabled(agent.enable_sales_detection)}")
                st.markdown(f"**Call Transfer:** {format_enabled_disabled(agent.enable_call_transfer)}")

                st.divider()

                # Call Forwarding
                st.markdown("#### Call Forwarding")
                st.markdown(f"**Status:** {format_enabled_disabled(agent.call_forwarding_enabled)}")
                if agent.call_forwarding_number:
                    st.markdown(f"**Number:** {format_phone(agent.call_forwarding_number)}")

                st.divider()

                # Custom Questions
                st.markdown("#### Custom Questions")
                if agent.custom_questions and len(agent.custom_questions) > 0:
                    for idx, q in enumerate(agent.custom_questions, 1):
                        question_preview = q.question_text[:50] + "..." if len(q.question_text) > 50 else q.question_text
                        with st.expander(f"Question {idx}: {question_preview}", expanded=False):
                            st.markdown(f"**Question:** {q.question_text}")
                            st.markdown(f"**Type:** {q.expected_answer_type}")
                            st.markdown(f"**Required:** {format_yes_no(q.is_required)}")
                            st.markdown(f"**Display Order:** {q.display_order}")
                else:
                    st.info("No custom questions configured")

                st.divider()

                # FAQ Items
                st.markdown("#### FAQ Items")
                if agent.faq_list and len(agent.faq_list) > 0:
                    st.caption(f"Total FAQs: {len(agent.faq_list)}")
                    for idx, faq in enumerate(agent.faq_list, 1):
                        question_preview = faq.question[:50] + "..." if len(faq.question) > 50 else faq.question
                        with st.expander(f"FAQ {idx}: {question_preview}", expanded=False):
                            st.markdown(f"**Q:** {faq.question}")
                            st.markdown(f"**A:** {faq.answer}")
                            st.markdown(f"**Display Order:** {faq.display_order}")
                else:
                    st.info("No FAQs configured")

                st.divider()

                # Notification Preferences
                st.markdown("#### Notification Preferences")
                if agent.message_taking_preference:
                    prefs = agent.message_taking_preference
                    st.markdown(f"**Email Notifications:** {format_enabled_disabled(prefs.get('email_notifications_enabled', False))}")
                    st.markdown(f"**SMS Notifications:** {format_enabled_disabled(prefs.get('sms_notifications_enabled', False))}")
                    if prefs.get('sms_notification_phone_number'):
                        st.markdown(f"**SMS Number:** {format_phone(prefs['sms_notification_phone_number'])}")
                else:
                    st.info("Default notification preferences")

                st.divider()

                # Industry Knowledge
                if agent.customized_industry_knowledge:
                    st.markdown("#### Customized Industry Knowledge")

                    # Edit button at the top
                    if st.button(
                        "📝 Edit Industry Knowledge",
                        type="primary",
                        use_container_width=True,
                        help="Edit customized fields for each call type"
                    ):
                        business_name = agent.business.business_name if agent.business else "Unknown Business"
                        # Use session_state to pass data (query_params are cleared by st.switch_page bug)
                        st.session_state.edit_agent_id = str(agent.id)
                        st.session_state.edit_business_name = business_name
                        st.switch_page("pages/15_📝_Edit_Industry_Knowledge.py")

                    st.markdown("")  # Add spacing

                    # Read-only JSON viewer
                    with st.expander("📚 View Industry Knowledge (JSON)", expanded=False):
                        st.json(agent.customized_industry_knowledge)
                else:
                    st.markdown("#### Customized Industry Knowledge")
                    st.info("No industry knowledge configured for this agent.")

                st.divider()

                # Metadata
                st.markdown("#### Metadata")
                st.markdown(f"**Created:** {format_datetime(agent.created_at)}")
                st.markdown(f"**Updated:** {format_datetime(agent.updated_at)}")
                st.markdown(f"**Agent ID:** `{agent.id}`")
                st.markdown(f"**Business ID:** `{agent.business_id}`")

                st.divider()

                # Quick Actions
                st.markdown("#### Quick Actions")
                st.button("⚡ Edit Configuration", disabled=True, help="Coming in Phase 3", use_container_width=True)
                if agent.business:
                    st.button("🏢 View Business", disabled=True, help="Coming in Phase 3", use_container_width=True)

        except Exception as e:
            st.error(f"Failed to load agent details: {str(e)}")

    else:
        st.info("Select an agent from the table to view details")

# Export section
st.divider()
st.markdown("### Export")

col1, col2 = st.columns([1, 3])
with col1:
    if st.button("📥 Export to CSV", use_container_width=True):
        try:
            agents = load_agents(search_query, tone_filter, 0, 1000)  # Get more for export
            if agents:
                export_df = pd.DataFrame([
                    {
                        "Agent ID": str(a.id),
                        "Agent Name": a.agent_name,
                        "Business Name": a.business.business_name if a.business else "N/A",
                        "Business ID": str(a.business_id),
                        "Tone": a.tone,
                        "Max Call Duration (min)": a.max_call_duration_minutes,
                        "1-800 Blocking": a.enable_1800_blocking,
                        "Sales Detection": a.enable_sales_detection,
                        "Call Transfer": a.enable_call_transfer,
                        "Call Forwarding Enabled": a.call_forwarding_enabled,
                        "Call Forwarding Number": a.call_forwarding_number or "",
                        "FAQ Count": len(a.faq_list) if a.faq_list else 0,
                        "Custom Questions Count": len(a.custom_questions) if a.custom_questions else 0,
                        "Created": a.created_at,
                        "Updated": a.updated_at
                    }
                    for a in agents
                ])
                csv = export_df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    "agents.csv",
                    "text/csv",
                    key='download-csv',
                    use_container_width=True
                )
            else:
                st.warning("No agents to export")
        except Exception as e:
            st.error(f"Failed to export: {str(e)}")
