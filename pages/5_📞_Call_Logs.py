"""
Call Logs - Browse call records with transcript viewer
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from config.auth import require_auth
from database.connection import get_session
from services.call_log_service import get_call_logs
from utils.formatters import format_datetime, format_phone, format_duration, format_status_badge

# Auth check
if not require_auth():
    st.stop()

st.title("📞 Call Logs")
st.markdown("Browse and search call records")

# Filters
col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

with col1:
    status_filter = st.selectbox(
        "Status",
        ["all", "answered_by_ai", "forwarded", "missed", "voicemail"]
    )

with col2:
    phone_search = st.text_input("📱 Phone Number", placeholder="Search phone...")

with col3:
    date_range = st.selectbox("Date Range", ["7 days", "30 days", "90 days", "All"])

with col4:
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

# Load call logs
@st.cache_data(ttl=60)
def load_call_logs(status, phone, date_from_str):
    """Load call logs with filters"""
    with get_session() as session:
        # Convert date string back to datetime if needed
        date_from_dt = datetime.fromisoformat(date_from_str) if date_from_str else None
        return get_call_logs(
            session,
            limit=100,
            offset=0,
            status_filter=status if status != "all" else None,
            phone_search=phone if phone else None,
            date_from=date_from_dt
        )

try:
    # Convert datetime to string for caching
    date_from_str = date_from.isoformat() if date_from else None
    call_logs = load_call_logs(status_filter, phone_search, date_from_str)

    if not call_logs:
        st.info("No call logs found matching your criteria")
    else:
        st.markdown(f"### Call Logs ({len(call_logs)} records)")

        # Display call logs with expandable transcripts
        for call in call_logs:
            with st.expander(
                f"📞 {format_phone(call.caller_phone_number)} - {call.call_status} - {format_datetime(call.call_start_time, format_str='%Y-%m-%d %H:%M')}"
            ):
                # Call details in columns
                detail_col1, detail_col2, detail_col3 = st.columns(3)

                with detail_col1:
                    st.markdown("**Call Info**")
                    st.markdown(f"**From:** {format_phone(call.caller_phone_number)}")
                    if call.to_phone_number:
                        st.markdown(f"**To:** {format_phone(call.to_phone_number)}")
                    st.markdown(f"**Direction:** {call.call_direction}")
                    st.markdown(f"**Status:** {format_status_badge(call.call_status)}")

                with detail_col2:
                    st.markdown("**Timing**")
                    st.markdown(f"**Started:** {format_datetime(call.call_start_time)}")
                    if call.call_end_time:
                        st.markdown(f"**Ended:** {format_datetime(call.call_end_time)}")
                    if call.call_duration_seconds:
                        st.markdown(f"**Duration:** {format_duration(call.call_duration_seconds)}")

                with detail_col3:
                    st.markdown("**Additional Info**")
                    if call.caller_name:
                        st.markdown(f"**Caller Name:** {call.caller_name}")
                    if call.is_starred:
                        st.markdown("⭐ **Starred**")
                    if call.is_archived:
                        st.markdown("📁 **Archived**")
                    if call.twilio_call_sid:
                        st.caption(f"Twilio SID: {call.twilio_call_sid}")

                # AI Summary
                if call.ai_summary:
                    st.markdown("**🤖 AI Summary**")
                    st.info(call.ai_summary)

                # Full Transcript
                if call.full_transcript:
                    st.markdown("**📝 Full Transcript**")
                    st.text_area(
                        "Transcript",
                        call.full_transcript,
                        height=200,
                        disabled=True,
                        key=f"transcript_{call.id}"
                    )
                else:
                    st.caption("No transcript available")

                # Call notes
                if call.call_notes:
                    st.markdown("**📋 Notes**")
                    st.text_area(
                        "Notes",
                        call.call_notes,
                        height=100,
                        disabled=True,
                        key=f"notes_{call.id}"
                    )

                # Transfer info
                if call.transfer_attempted:
                    st.markdown("**📞 Transfer Info**")
                    st.markdown(f"**Transfer Status:** {call.transfer_status or 'N/A'}")
                    st.markdown(f"**Agents Tried:** {call.agents_tried_count}")

except Exception as e:
    st.error(f"Failed to load call logs: {str(e)}")

# Export functionality
st.divider()
if st.button("📥 Export to CSV", use_container_width=True):
    try:
        date_from_str = date_from.isoformat() if date_from else None
        call_logs = load_call_logs(status_filter, phone_search, date_from_str)

        call_logs_df = pd.DataFrame([
            {
                "Caller Phone": call.caller_phone_number,
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

        csv = call_logs_df.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            "call_logs.csv",
            "text/csv",
            key='download-csv'
        )
    except Exception as e:
        st.error(f"Failed to export: {str(e)}")
