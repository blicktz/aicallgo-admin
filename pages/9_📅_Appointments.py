"""
Appointments - Appointment viewing and search
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from config.auth import require_auth
from database.connection import get_session
from services.appointment_service import (
    get_appointments_by_business,
    count_appointments_by_business,
    get_appointment_by_id
)
from services.business_service import get_businesses
from utils.formatters import format_datetime, format_phone, format_status_badge
import logging

logger = logging.getLogger(__name__)

# Auth check
if not require_auth():
    st.stop()

st.title("📅 Appointments")
st.markdown("Browse appointments by business")

# Top panel: Filters (3 columns)
col1, col2, col3 = st.columns([2, 2, 2])

with col1:
    business_name_search = st.text_input("🏢 Business Name", placeholder="Search business name...")

with col2:
    phone_search = st.text_input("📱 Phone Number", placeholder="Search phone...")

with col3:
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

# Initialize session state for selected business and appointment
if "selected_business_id" not in st.session_state:
    st.session_state.selected_business_id = None
if "selected_appointment_id" not in st.session_state:
    st.session_state.selected_appointment_id = None

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

# Load appointments for selected business
@st.cache_data(ttl=60)
def load_appointments(business_id, date_from_str):
    """Load appointments with filters for a specific business"""
    with get_session() as session:
        # Convert date string back to datetime if needed
        date_from_dt = datetime.fromisoformat(date_from_str) if date_from_str else None

        appointments = get_appointments_by_business(
            session,
            business_id,
            limit=500,  # Load up to 500 appointments for scrolling
            offset=0,
            date_from=date_from_dt
        )

        # Get total count
        total_count = count_appointments_by_business(
            session,
            business_id,
            date_from=date_from_dt
        )

        return appointments, total_count

# Main layout: 30% business list, 70% appointments
business_col, appointments_col = st.columns([3, 7])

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
            st.markdown("*Click on a row to view appointments*")
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
                    # Clear selected appointment when switching businesses
                    st.session_state.selected_appointment_id = None

            # Show count
            st.caption(f"Showing {len(businesses)} businesses")

    except Exception as e:
        st.error(f"Failed to load businesses: {str(e)}")

# RIGHT COLUMN: Appointments
with appointments_col:
    st.markdown("### Appointments")

    if not st.session_state.selected_business_id:
        st.info("👈 Select a business from the list to view appointments")
    else:
        try:
            # Convert date to string for caching
            date_from_str = date_from.isoformat() if date_from else None

            # Load appointments for selected business
            appointments, total_count = load_appointments(
                st.session_state.selected_business_id,
                date_from_str
            )

            if not appointments:
                st.info("No appointments found for this business")
            else:
                # Display count and info
                showing = len(appointments)
                if showing < total_count:
                    st.markdown(f"**Showing {showing} of {total_count} appointments** (limited to 500 for performance)")
                else:
                    st.markdown(f"**Total: {total_count} appointments**")

                # Create summary DataFrame for scrollable table
                appointments_summary_df = pd.DataFrame([
                    {
                        "Start Time": format_datetime(apt.start_time, format_str='%Y-%m-%d %H:%M'),
                        "Title": apt.title[:40] if apt.title else "—",
                        "End User": apt.end_user.full_name if apt.end_user else "—",
                        "Duration": f"{int((apt.end_time - apt.start_time).total_seconds() / 60)} min",
                        "Status": apt.status.replace("_", " ").title(),
                        "ID": str(apt.id)
                    }
                    for apt in appointments
                ])

                # Scrollable summary table
                st.markdown("#### Appointment Summary")
                st.markdown("*Click a row to view full details below*")

                apt_event = st.dataframe(
                    appointments_summary_df.drop(columns=["ID"]),
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    height=400
                )

                # Update selected appointment ID
                if apt_event and "selection" in apt_event and "rows" in apt_event["selection"]:
                    if len(apt_event["selection"]["rows"]) > 0:
                        selected_idx = apt_event["selection"]["rows"][0]
                        selected_apt_id = appointments_summary_df.iloc[selected_idx]["ID"]
                        st.session_state.selected_appointment_id = selected_apt_id

                st.divider()

                # DETAIL PANEL: Show full details for selected appointment
                if st.session_state.selected_appointment_id:
                    # Find the selected appointment in the list
                    selected_appointment = next(
                        (apt for apt in appointments if str(apt.id) == st.session_state.selected_appointment_id),
                        None
                    )

                    if selected_appointment:
                        st.markdown("#### Appointment Details")

                        # Basic info
                        st.markdown("**Basic Info**")
                        st.markdown(f"**Title:** {selected_appointment.title}")
                        if selected_appointment.description:
                            st.markdown(f"**Description:** {selected_appointment.description}")
                        st.markdown(f"**Start:** {format_datetime(selected_appointment.start_time)}")
                        st.markdown(f"**End:** {format_datetime(selected_appointment.end_time)}")

                        # Calculate duration
                        duration = selected_appointment.end_time - selected_appointment.start_time
                        duration_minutes = int(duration.total_seconds() / 60)
                        st.markdown(f"**Duration:** {duration_minutes} minutes")
                        st.markdown(f"**Timezone:** {selected_appointment.timezone}")
                        st.markdown(f"**Status:** {format_status_badge(selected_appointment.status)}")
                        st.markdown(f"**Source:** {selected_appointment.booking_source.replace('_', ' ').title()}")

                        st.divider()

                        # Parties
                        st.markdown("**Parties**")
                        if selected_appointment.user:
                            st.markdown(f"**User:** {selected_appointment.user.email}")

                        if selected_appointment.business:
                            st.markdown(f"**Business:** {selected_appointment.business.business_name}")

                        if selected_appointment.end_user:
                            st.markdown("**End User (Caller):**")
                            st.markdown(f"  - Name: {selected_appointment.end_user.full_name}")
                            st.markdown(f"  - Phone: {selected_appointment.end_user.phone_number}")
                            if selected_appointment.end_user.email:
                                st.markdown(f"  - Email: {selected_appointment.end_user.email}")

                        st.divider()

                        # Tracking
                        st.markdown("**Tracking**")
                        if selected_appointment.confirmation_sent_at:
                            st.markdown(f"**Confirmation Sent:** {format_datetime(selected_appointment.confirmation_sent_at)}")
                        else:
                            st.caption("No confirmation sent")

                        if selected_appointment.reminder_sent_at:
                            st.markdown(f"**Reminder Sent:** {format_datetime(selected_appointment.reminder_sent_at)}")
                        else:
                            st.caption("No reminder sent")

                        if selected_appointment.cancelled_at:
                            st.markdown(f"**Cancelled At:** {format_datetime(selected_appointment.cancelled_at)}")
                            if selected_appointment.cancellation_reason:
                                st.markdown(f"**Reason:** {selected_appointment.cancellation_reason}")

                        st.divider()

                        # Linked call log
                        st.markdown("**Linked Call Log**")
                        if selected_appointment.call_log:
                            st.markdown(f"**Call ID:** {selected_appointment.call_log.id}")
                            st.markdown(f"**Call Status:** {selected_appointment.call_log.call_status}")
                            if selected_appointment.call_log.call_start_time:
                                st.markdown(f"**Call Time:** {format_datetime(selected_appointment.call_log.call_start_time)}")
                        else:
                            st.caption("No linked call log")

                        # Extra data
                        if selected_appointment.extra_data and selected_appointment.extra_data != {}:
                            st.divider()
                            st.markdown("**Extra Data**")
                            st.json(selected_appointment.extra_data)
                    else:
                        st.warning("Selected appointment not found")
                else:
                    st.info("👆 Select an appointment from the table above to view full details")

        except Exception as e:
            st.error(f"Failed to load appointments: {str(e)}")

# Export functionality
st.divider()
if st.button("📥 Export Current View to CSV", use_container_width=True):
    try:
        if not st.session_state.selected_business_id:
            st.warning("Please select a business first")
        else:
            date_from_str = date_from.isoformat() if date_from else None
            appointments, _ = load_appointments(
                st.session_state.selected_business_id,
                date_from_str
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
