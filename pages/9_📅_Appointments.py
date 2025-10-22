"""
Appointments - Appointment viewing and search
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from config.auth import require_auth
from database.connection import get_session
from services.appointment_service import (
    get_appointments,
    get_appointment_by_id,
    get_appointment_stats
)
from utils.formatters import format_datetime, format_status_badge
import logging

logger = logging.getLogger(__name__)

# Auth check
if not require_auth():
    st.stop()

st.title("📅 Appointments")
st.markdown("View and search appointments")

# Search and filters
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
with col1:
    search_query = st.text_input(
        "🔍 Search",
        placeholder="User email, end user name, or title...",
        help="Search by user email, end user name/email, or appointment title"
    )
with col2:
    status_filter = st.selectbox(
        "Status",
        ["all", "confirmed", "cancelled", "completed", "no_show"],
        help="Filter by appointment status"
    )
with col3:
    source_filter = st.selectbox(
        "Source",
        ["all", "ai_call", "manual"],
        help="Filter by booking source"
    )
with col4:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Date range filter
date_col1, date_col2 = st.columns(2)
with date_col1:
    start_date = st.date_input(
        "Start Date",
        value=datetime.now() - timedelta(days=30),
        help="Filter appointments from this date"
    )
with date_col2:
    end_date = st.date_input(
        "End Date",
        value=datetime.now() + timedelta(days=30),
        help="Filter appointments until this date"
    )

# Convert dates to datetime
start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None

# Load statistics
@st.cache_data(ttl=60)
def load_stats(start_dt, end_dt):
    """Load appointment statistics"""
    try:
        with get_session() as session:
            return get_appointment_stats(session, start_date=start_dt, end_date=end_dt)
    except Exception as e:
        logger.error(f"Error loading stats: {e}", exc_info=True)
        return None

# Display statistics cards
try:
    stats = load_stats(start_datetime, end_datetime)
    if stats:
        st.markdown("### Statistics")
        stat_col1, stat_col2, stat_col3, stat_col4, stat_col5 = st.columns(5)

        with stat_col1:
            st.metric("Total", stats.get("total_appointments", 0))

        by_status = stats.get("by_status", {})
        with stat_col2:
            st.metric("Confirmed", by_status.get("confirmed", 0))
        with stat_col3:
            st.metric("Completed", by_status.get("completed", 0))
        with stat_col4:
            st.metric("Cancelled", by_status.get("cancelled", 0))
        with stat_col5:
            st.metric("No-show", by_status.get("no_show", 0))

        # Booking source breakdown
        by_source = stats.get("by_booking_source", {})
        if by_source:
            source_col1, source_col2 = st.columns(2)
            with source_col1:
                st.metric("AI Call Bookings", by_source.get("ai_call", 0))
            with source_col2:
                st.metric("Manual Bookings", by_source.get("manual", 0))

        st.divider()

except Exception as e:
    logger.error(f"Failed to load statistics: {e}", exc_info=True)
    st.warning("Unable to load statistics")

# Initialize session state for selected appointment
if "selected_appointment_id" not in st.session_state:
    st.session_state.selected_appointment_id = None

# Load appointments
@st.cache_data(ttl=60)
def load_appointments(search, status, source, start_dt, end_dt, page_num, per_page):
    """Load appointments with filters"""
    try:
        with get_session() as session:
            offset = page_num * per_page
            return get_appointments(
                session,
                limit=per_page,
                offset=offset,
                search_query=search if search else None,
                status=status if status != "all" else None,
                booking_source=source if source != "all" else None,
                start_date=start_dt,
                end_date=end_dt
            )
    except Exception as e:
        logger.error(f"Error loading appointments: {e}", exc_info=True)
        raise

# Main layout: table + detail panel
table_col, detail_col = st.columns([6, 4])

with table_col:
    st.markdown("### Appointments")

    try:
        appointments = load_appointments(
            search_query,
            status_filter,
            source_filter,
            start_datetime,
            end_datetime,
            0,
            50
        )

        if not appointments:
            st.info("No appointments found matching your criteria")
        else:
            # Convert to DataFrame
            appts_df = pd.DataFrame([
                {
                    "Start Time": format_datetime(a.start_time, format_str='%Y-%m-%d %H:%M'),
                    "User": a.user.email if a.user else "N/A",
                    "Title": a.title[:50] if a.title else "N/A",
                    "End User": a.end_user.full_name if a.end_user else "N/A",
                    "Status": a.status.replace("_", " ").title(),
                    "Source": a.booking_source.replace("_", " ").title(),
                    "ID": str(a.id)
                }
                for a in appointments
            ])

            # Display DataFrame with row selection
            st.markdown("*Click on a row to view details*")

            event = st.dataframe(
                appts_df.drop(columns=["ID"]),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                height=500
            )

            # Update selected appointment ID if a row is selected
            if event and "selection" in event and "rows" in event["selection"]:
                if len(event["selection"]["rows"]) > 0:
                    selected_idx = event["selection"]["rows"][0]
                    selected_apt_id = appts_df.iloc[selected_idx]["ID"]
                    st.session_state.selected_appointment_id = selected_apt_id

            # Show count
            st.caption(f"Showing {len(appointments)} appointments")

    except Exception as e:
        logger.error(f"Failed to load appointments: {e}", exc_info=True)
        st.error(f"❌ Failed to load appointments: {str(e)}")

with detail_col:
    st.markdown("### Appointment Details")

    if st.session_state.selected_appointment_id:
        # Load full appointment details
        @st.cache_data(ttl=60)
        def load_appointment_details(apt_id):
            """Load appointment details"""
            try:
                with get_session() as session:
                    return get_appointment_by_id(session, apt_id)
            except Exception as e:
                logger.error(f"Error loading appointment details: {e}", exc_info=True)
                raise

        try:
            appointment = load_appointment_details(st.session_state.selected_appointment_id)

            if not appointment:
                st.warning("Appointment not found")
            else:
                # Basic info
                st.markdown("#### Basic Info")
                st.markdown(f"**Title:** {appointment.title}")
                if appointment.description:
                    st.markdown(f"**Description:** {appointment.description}")
                st.markdown(f"**Start:** {format_datetime(appointment.start_time)}")
                st.markdown(f"**End:** {format_datetime(appointment.end_time)}")
                st.markdown(f"**Timezone:** {appointment.timezone}")

                # Calculate duration
                duration = appointment.end_time - appointment.start_time
                duration_minutes = int(duration.total_seconds() / 60)
                st.markdown(f"**Duration:** {duration_minutes} minutes")

                # Status
                status_color = {
                    "confirmed": "success",
                    "cancelled": "danger",
                    "completed": "info",
                    "no_show": "warning"
                }.get(appointment.status, "secondary")
                st.markdown(f"**Status:** {format_status_badge(appointment.status)}")
                st.markdown(f"**Source:** {appointment.booking_source.replace('_', ' ').title()}")

                st.divider()

                # Parties
                st.markdown("#### Parties")
                if appointment.user:
                    st.markdown(f"**User:** {appointment.user.email}")

                if appointment.business:
                    st.markdown(f"**Business:** {appointment.business.business_name}")

                if appointment.end_user:
                    st.markdown("**End User (Caller):**")
                    st.markdown(f"  - Name: {appointment.end_user.full_name}")
                    st.markdown(f"  - Phone: {appointment.end_user.phone_number}")
                    if appointment.end_user.email:
                        st.markdown(f"  - Email: {appointment.end_user.email}")

                st.divider()

                # Tracking
                st.markdown("#### Tracking")
                if appointment.confirmation_sent_at:
                    st.markdown(f"**Confirmation Sent:** {format_datetime(appointment.confirmation_sent_at)}")
                else:
                    st.caption("No confirmation sent")

                if appointment.reminder_sent_at:
                    st.markdown(f"**Reminder Sent:** {format_datetime(appointment.reminder_sent_at)}")
                else:
                    st.caption("No reminder sent")

                if appointment.cancelled_at:
                    st.markdown(f"**Cancelled At:** {format_datetime(appointment.cancelled_at)}")
                    if appointment.cancellation_reason:
                        st.markdown(f"**Reason:** {appointment.cancellation_reason}")

                st.divider()

                # Linked call log
                st.markdown("#### Linked Call Log")
                if appointment.call_log:
                    st.markdown(f"**Call ID:** {appointment.call_log.id}")
                    st.markdown(f"**Call Status:** {appointment.call_log.status}")
                    if hasattr(appointment.call_log, 'created_at'):
                        st.markdown(f"**Call Time:** {format_datetime(appointment.call_log.created_at)}")
                else:
                    st.caption("No linked call log")

                # Extra data
                if appointment.extra_data and appointment.extra_data != {}:
                    st.divider()
                    st.markdown("#### Extra Data")
                    st.json(appointment.extra_data)

        except Exception as e:
            logger.error(f"Failed to load appointment details: {e}", exc_info=True)
            st.error(f"❌ Failed to load appointment details: {str(e)}")

    else:
        st.info("Select an appointment from the table to view details")

# Export functionality
st.divider()

if st.button("📥 Export to CSV", use_container_width=True):
    try:
        with st.spinner("Exporting appointments..."):
            appointments = load_appointments(
                search_query,
                status_filter,
                source_filter,
                start_datetime,
                end_datetime,
                0,
                1000  # Load more for export
            )

            if not appointments:
                st.warning("No appointments to export")
            else:
                export_df = pd.DataFrame([
                    {
                        "Start Time": format_datetime(a.start_time),
                        "End Time": format_datetime(a.end_time),
                        "Duration (min)": int((a.end_time - a.start_time).total_seconds() / 60),
                        "User Email": a.user.email if a.user else "N/A",
                        "Business Name": a.business.business_name if a.business else "N/A",
                        "Title": a.title,
                        "Description": a.description or "N/A",
                        "End User Name": a.end_user.full_name if a.end_user else "N/A",
                        "End User Phone": a.end_user.phone_number if a.end_user else "N/A",
                        "End User Email": a.end_user.email if a.end_user else "N/A",
                        "Status": a.status,
                        "Booking Source": a.booking_source,
                        "Timezone": a.timezone,
                        "Confirmation Sent": format_datetime(a.confirmation_sent_at) if a.confirmation_sent_at else "N/A",
                        "Reminder Sent": format_datetime(a.reminder_sent_at) if a.reminder_sent_at else "N/A",
                        "Cancelled At": format_datetime(a.cancelled_at) if a.cancelled_at else "N/A",
                        "Cancellation Reason": a.cancellation_reason or "N/A",
                        "Call Log ID": str(a.call_log.id) if a.call_log else "N/A",
                        "Appointment ID": str(a.id)
                    }
                    for a in appointments
                ])

                csv = export_df.to_csv(index=False)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"appointments_{timestamp}.csv",
                    mime="text/csv",
                    key='download-csv',
                    use_container_width=True
                )

                st.success(f"✓ Exported {len(export_df)} appointments")

                if len(appointments) >= 1000:
                    st.warning("⚠️ Export limited to 1000 appointments. Use filters to export specific appointments.")

    except Exception as e:
        logger.error(f"CSV export failed: {e}", exc_info=True)
        st.error(f"❌ Failed to export: {str(e)}")

# Last updated timestamp
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
