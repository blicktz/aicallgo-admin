"""
Call Logs - Browse call records filtered by business
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, timedelta
from config.auth import require_auth
from database.connection import get_session
from services.call_log_service import get_calls_by_business, count_calls_by_business
from services.business_service import get_businesses
from services.recording_service import get_recording_service
from utils.formatters import format_datetime, format_phone, format_duration, format_status_badge, parse_transcript_json
from components.call_monitoring_panel import render_monitoring_panel

# Auth check
if not require_auth():
    st.stop()

st.title("📞 Call Logs")
st.markdown("Browse call records by business")

# Real-Time Monitoring Panel (NEW)
try:
    render_monitoring_panel()
    st.divider()
except Exception as e:
    st.warning(f"⚠️ Monitoring panel unavailable: {str(e)}")
    st.divider()

# Top panel: Filters (4 columns)
col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

with col1:
    # Use correct call statuses from backend schema
    status_filter = st.selectbox(
        "Status",
        ["all", "completed", "failed", "hangup", "blocked_sales",
         "blocked_1800", "declined_no_credit", "in_progress", "forwarded"]
    )

with col2:
    business_name_search = st.text_input("🏢 Business Name", placeholder="Search business name...")

with col3:
    phone_search = st.text_input("📱 Phone Number", placeholder="Search phone...")

with col4:
    date_range = st.selectbox("Date Range", ["7 days", "30 days", "90 days", "All"])
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# Calculate date range
date_from = None
if date_range == "7 days":
    date_from = datetime.utcnow() - timedelta(days=7)
elif date_range == "30 days":
    date_from = datetime.utcnow() - timedelta(days=30)
elif date_range == "90 days":
    date_from = datetime.utcnow() - timedelta(days=90)

# Initialize session state for selected business and call
if "selected_business_id" not in st.session_state:
    st.session_state.selected_business_id = None
if "selected_call_id" not in st.session_state:
    st.session_state.selected_call_id = None

# Load businesses with filters
@st.cache_data(ttl=60)
def load_businesses(name_search, phone_search):
    """Load businesses with filters"""
    with get_session() as session:
        return get_businesses(
            session,
            limit=100,
            offset=0,
            search_query=name_search if name_search else None,
            phone_search=phone_search if phone_search else None
        )

# Load call logs for selected business
@st.cache_data(ttl=60)
def load_call_logs(business_id, status, date_from_str):
    """Load call logs with filters for a specific business"""
    with get_session() as session:
        # Convert date string back to datetime if needed
        date_from_dt = datetime.fromisoformat(date_from_str) if date_from_str else None

        calls = get_calls_by_business(
            session,
            business_id,
            limit=500,  # Load up to 500 calls for scrolling
            offset=0,
            status_filter=status if status != "all" else None,
            date_from=date_from_dt
        )

        # Get total count
        total_count = count_calls_by_business(
            session,
            business_id,
            status_filter=status if status != "all" else None,
            date_from=date_from_dt
        )

        return calls, total_count

# Main layout: 30% business list, 70% call logs
business_col, calls_col = st.columns([3, 7])

# LEFT COLUMN: Business List
with business_col:
    st.markdown("### Businesses")

    try:
        businesses = load_businesses(business_name_search, phone_search)

        if not businesses:
            st.info("No businesses found")
        else:
            # Convert to DataFrame for display
            businesses_df = pd.DataFrame([
                {
                    "Business Name": b.business_name or "Unnamed",
                    "Industry": b.industry or "N/A",
                    "Phone": format_phone(b.primary_business_phone_number) if b.primary_business_phone_number else "N/A",
                    "ID": str(b.id)
                }
                for b in businesses
            ])

            # Display scrollable business list
            st.markdown("*Click on a row to view call logs*")
            event = st.dataframe(
                businesses_df.drop(columns=["ID"]),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                height=600
            )

            # Update selected business ID if a row is selected
            if event and "selection" in event and "rows" in event["selection"]:
                if len(event["selection"]["rows"]) > 0:
                    selected_idx = event["selection"]["rows"][0]
                    selected_business_id = businesses_df.iloc[selected_idx]["ID"]
                    st.session_state.selected_business_id = selected_business_id
                    # Clear selected call when switching businesses
                    st.session_state.selected_call_id = None

            # Show count
            st.caption(f"Showing {len(businesses)} businesses")

    except Exception as e:
        st.error(f"Failed to load businesses: {str(e)}")

# RIGHT COLUMN: Call Logs
with calls_col:
    st.markdown("### Call Logs")

    if not st.session_state.selected_business_id:
        st.info("👈 Select a business from the list to view call logs")
    else:
        try:
            # Convert date to string for caching
            date_from_str = date_from.isoformat() if date_from else None

            # Load call logs for selected business
            call_logs, total_count = load_call_logs(
                st.session_state.selected_business_id,
                status_filter,
                date_from_str
            )

            if not call_logs:
                st.info("No call logs found for this business")
            else:
                # Display count and info
                showing = len(call_logs)
                if showing < total_count:
                    st.markdown(f"**Showing {showing} of {total_count} calls** (limited to 500 for performance)")
                else:
                    st.markdown(f"**Total: {total_count} calls**")

                # Create summary DataFrame for scrollable table
                calls_summary_df = pd.DataFrame([
                    {
                        "Caller": format_phone(call.caller_phone_number),
                        "Name": call.caller_name or "—",
                        "Direction": call.call_direction,
                        "Time": format_datetime(call.call_start_time, format_str='%Y-%m-%d %H:%M'),
                        "Status": call.call_status,
                        "Duration": format_duration(call.call_duration_seconds) if call.call_duration_seconds else "—",
                        "ID": str(call.id)
                    }
                    for call in call_logs
                ])

                # Scrollable summary table
                st.markdown("#### Call Summary")
                st.markdown("*Click a row to view full details below*")

                call_event = st.dataframe(
                    calls_summary_df.drop(columns=["ID"]),
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    height=400
                )

                # Update selected call ID
                if call_event and "selection" in call_event and "rows" in call_event["selection"]:
                    if len(call_event["selection"]["rows"]) > 0:
                        selected_idx = call_event["selection"]["rows"][0]
                        selected_call_id = calls_summary_df.iloc[selected_idx]["ID"]
                        st.session_state.selected_call_id = selected_call_id

                st.divider()

                # DETAIL PANEL: Show full details for selected call
                if st.session_state.selected_call_id:
                    # Find the selected call in the list
                    selected_call = next(
                        (call for call in call_logs if str(call.id) == st.session_state.selected_call_id),
                        None
                    )

                    if selected_call:
                        st.markdown("#### Call Details")

                        # Call info in columns
                        detail_col1, detail_col2, detail_col3 = st.columns(3)

                        with detail_col1:
                            st.markdown("**Call Info**")
                            st.markdown(f"**From:** {format_phone(selected_call.caller_phone_number)}")
                            if selected_call.to_phone_number:
                                st.markdown(f"**To:** {format_phone(selected_call.to_phone_number)}")
                            st.markdown(f"**Direction:** {selected_call.call_direction}")
                            st.markdown(f"**Status:** {format_status_badge(selected_call.call_status)}")

                        with detail_col2:
                            st.markdown("**Timing**")
                            st.markdown(f"**Started:** {format_datetime(selected_call.call_start_time)}")
                            if selected_call.call_end_time:
                                st.markdown(f"**Ended:** {format_datetime(selected_call.call_end_time)}")
                            if selected_call.call_duration_seconds:
                                st.markdown(f"**Duration:** {format_duration(selected_call.call_duration_seconds)}")

                        with detail_col3:
                            st.markdown("**Additional Info**")
                            if selected_call.caller_name:
                                st.markdown(f"**Caller Name:** {selected_call.caller_name}")
                            if selected_call.is_starred:
                                st.markdown("⭐ **Starred**")
                            if selected_call.is_archived:
                                st.markdown("📁 **Archived**")
                            if selected_call.twilio_call_sid:
                                st.caption(f"Twilio SID: {selected_call.twilio_call_sid}")

                        # AI Summary (expandable)
                        if selected_call.ai_summary:
                            with st.expander("🤖 AI Summary", expanded=True):
                                st.info(selected_call.ai_summary)

                        # Call Recording Player (expandable)
                        if selected_call.twilio_call_sid:
                            with st.expander("🎙️ Call Recording", expanded=True):
                                try:
                                    # Get recording service
                                    recording_service = get_recording_service()

                                    # Get recording playback info with presigned URL
                                    with get_session() as db_session:
                                        recording_info = recording_service.get_recording_playback_info(
                                            session=db_session,
                                            call_sid=selected_call.twilio_call_sid
                                        )

                                    if recording_info:
                                        # Show recording metadata
                                        meta_col1, meta_col2 = st.columns([3, 1])
                                        with meta_col1:
                                            if recording_info.get("duration_seconds"):
                                                st.markdown(
                                                    f"**Duration:** {format_duration(recording_info['duration_seconds'])}"
                                                )
                                        with meta_col2:
                                            st.markdown(
                                                f"**Format:** {recording_info['content_type'].split('/')[-1].upper()}"
                                            )

                                        # Streamlit native audio player
                                        st.audio(recording_info["url"])

                                        # Expiration notice
                                        try:
                                            expires_at = datetime.fromisoformat(
                                                recording_info["expires_at"].replace('Z', '+00:00')
                                            )
                                            st.caption(
                                                f"⏱️ Playback URL expires at {expires_at.strftime('%I:%M %p UTC')}"
                                            )
                                        except Exception:
                                            pass
                                    else:
                                        st.info("📭 No recording available for this call")

                                except ValueError as e:
                                    # Configuration errors (missing B2 credentials, etc.)
                                    st.warning(f"⚠️ Recording playback not configured: {str(e)}")
                                except Exception as e:
                                    # Other errors (B2 access issues, etc.)
                                    st.error(f"❌ Failed to load recording: {str(e)}")

                        # Full Transcript (expandable) - Chat Style
                        if selected_call.full_transcript:
                            with st.expander("📝 Full Transcript", expanded=False):
                                # Parse transcript JSON
                                transcript_data = parse_transcript_json(selected_call.full_transcript)

                                if transcript_data["messages"]:
                                    # Inline CSS for chat bubbles
                                    css_styles = """
                                    .chat-container {
                                        max-width: 100%;
                                        padding: 0.5rem 0;
                                        background-color: #ffffff;
                                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                    }
                                    .chat-message {
                                        display: flex;
                                        margin-bottom: 1rem;
                                        gap: 0.75rem;
                                        align-items: flex-start;
                                    }
                                    .chat-message.agent {
                                        flex-direction: row-reverse;
                                        justify-content: flex-start;
                                    }
                                    .chat-message.caller {
                                        flex-direction: row;
                                        justify-content: flex-start;
                                    }
                                    .chat-avatar {
                                        flex-shrink: 0;
                                        width: 36px;
                                        height: 36px;
                                        border-radius: 50%;
                                        display: flex;
                                        align-items: center;
                                        justify-content: center;
                                        font-weight: 600;
                                        font-size: 0.875rem;
                                        color: #ffffff;
                                    }
                                    .chat-avatar.agent {
                                        background-color: #456535;
                                    }
                                    .chat-avatar.caller {
                                        background-color: #4b5563;
                                    }
                                    .chat-bubble-wrapper {
                                        display: flex;
                                        flex-direction: column;
                                        max-width: 70%;
                                    }
                                    .chat-bubble {
                                        padding: 0.75rem 1rem;
                                        border-radius: 1rem;
                                        line-height: 1.5;
                                        font-size: 1rem;
                                        word-wrap: break-word;
                                    }
                                    .chat-message.agent .chat-bubble {
                                        background-color: #e5e7eb;
                                        color: #111827;
                                        border-bottom-right-radius: 0.25rem;
                                    }
                                    .chat-message.caller .chat-bubble {
                                        background-color: #456535;
                                        color: #ffffff;
                                        border-bottom-left-radius: 0.25rem;
                                    }
                                    .chat-timestamp {
                                        font-size: 0.75rem;
                                        color: #6b7280;
                                        margin-top: 0.25rem;
                                        padding: 0 0.5rem;
                                    }
                                    .chat-message.agent .chat-timestamp {
                                        text-align: right;
                                    }
                                    .chat-message.caller .chat-timestamp {
                                        text-align: left;
                                    }
                                    """

                                    # Build chat HTML
                                    chat_html = '<div class="chat-container">'

                                    for msg in transcript_data["messages"]:
                                        role = msg.get("role", "caller")
                                        content = msg.get("content", "").replace('<', '&lt;').replace('>', '&gt;')
                                        timestamp = msg.get("timestamp")

                                        # Get initial for avatar
                                        avatar_letter = "J" if role == "agent" else "P"

                                        # Format timestamp if available
                                        time_display = ""
                                        if timestamp:
                                            try:
                                                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                                time_display = dt.strftime("%I:%M %p")
                                            except:
                                                time_display = ""

                                        # Build chat message HTML
                                        chat_html += f'''
                                        <div class="chat-message {role}">
                                            <div class="chat-avatar {role}">{avatar_letter}</div>
                                            <div class="chat-bubble-wrapper">
                                                <div class="chat-bubble">{content}</div>
                                                {f'<div class="chat-timestamp">{time_display}</div>' if time_display else ''}
                                            </div>
                                        </div>
                                        '''

                                    chat_html += '</div>'

                                    # Build complete HTML with inline styles
                                    full_html = f"""
                                    <!DOCTYPE html>
                                    <html>
                                    <head>
                                        <style>{css_styles}</style>
                                    </head>
                                    <body style="margin: 0; padding: 0;">
                                        {chat_html}
                                    </body>
                                    </html>
                                    """

                                    # Calculate dynamic height based on message count
                                    message_count = len(transcript_data["messages"])
                                    height = min(600, max(300, message_count * 80))

                                    # Render with components.html for proper rendering
                                    components.html(full_html, height=height, scrolling=True)

                                    # Show metadata if JSON was parsed successfully
                                    if transcript_data["is_json"] and transcript_data["metadata"]:
                                        metadata = transcript_data["metadata"]
                                        st.caption(f"Total messages: {metadata.get('total_messages', len(transcript_data['messages']))}")
                                else:
                                    # Fallback: show plain text
                                    st.text_area(
                                        "Transcript",
                                        selected_call.full_transcript,
                                        height=200,
                                        disabled=True,
                                        label_visibility="collapsed"
                                    )
                        else:
                            st.caption("No transcript available")

                        # Call notes (expandable)
                        if selected_call.call_notes:
                            with st.expander("📋 Notes", expanded=False):
                                st.text_area(
                                    "Notes",
                                    selected_call.call_notes,
                                    height=100,
                                    disabled=True,
                                    key=f"notes_{selected_call.id}",
                                    label_visibility="collapsed"
                                )

                        # Transfer info (expandable)
                        if selected_call.transfer_attempted:
                            with st.expander("📞 Transfer Info", expanded=False):
                                st.markdown(f"**Transfer Status:** {selected_call.transfer_status or 'N/A'}")
                                st.markdown(f"**Agents Tried:** {selected_call.agents_tried_count}")
                                if selected_call.conference_id:
                                    st.caption(f"Conference ID: {selected_call.conference_id}")
                    else:
                        st.warning("Selected call not found")
                else:
                    st.info("👆 Select a call from the table above to view full details")

        except Exception as e:
            st.error(f"Failed to load call logs: {str(e)}")

# Export functionality
st.divider()
if st.button("📥 Export Current View to CSV", use_container_width=True):
    try:
        if not st.session_state.selected_business_id:
            st.warning("Please select a business first")
        else:
            date_from_str = date_from.isoformat() if date_from else None
            call_logs, _ = load_call_logs(
                st.session_state.selected_business_id,
                status_filter,
                date_from_str
            )

            if not call_logs:
                st.warning("No call logs to export")
            else:
                export_df = pd.DataFrame([
                    {
                        "Caller Phone": call.caller_phone_number,
                        "Caller Name": call.caller_name or "N/A",
                        "To Phone": call.to_phone_number or "N/A",
                        "Direction": call.call_direction,
                        "Status": call.call_status,
                        "Start Time": format_datetime(call.call_start_time),
                        "Duration (s)": call.call_duration_seconds or 0,
                        "AI Summary": call.ai_summary or "N/A",
                        "ID": str(call.id)
                    }
                    for call in call_logs
                ])

                csv = export_df.to_csv(index=False)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"call_logs_{timestamp}.csv",
                    mime="text/csv",
                    key='download-csv',
                    use_container_width=True
                )

                st.success(f"✓ Ready to export {len(export_df)} calls")

    except Exception as e:
        st.error(f"Failed to export: {str(e)}")
