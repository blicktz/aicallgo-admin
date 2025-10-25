"""
Businesses - Browse business profiles with filtering
"""
import streamlit as st
import pandas as pd
import logging
from datetime import datetime
from config.auth import require_auth
from database.connection import get_session
from services.business_service import get_businesses, get_business_by_id, get_industries
from services.user_service import get_user_by_id
from services.call_log_service import get_calls_by_business
from utils.formatters import format_datetime, format_phone, format_status_badge
from components.carrier_instructions import render_carrier_instructions

# Auth check
if not require_auth():
    st.stop()

st.title("🏢 Businesses")
st.markdown("Browse and search business profiles")

# Search and filters
search_query = st.text_input("🔍 Search by business name", placeholder="Enter business name...")

col1, col2 = st.columns([2, 2])
with col1:
    # Load industries for filter
    @st.cache_data(ttl=300)
    def load_industries():
        with get_session() as session:
            industries = get_industries(session)
            return ["all"] + list(industries)

    try:
        industries_list = load_industries()
        industry_filter = st.selectbox("Industry", industries_list)
    except:
        industry_filter = st.selectbox("Industry", ["all"])

with col2:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# Initialize session state for selected business
if "selected_business_id" not in st.session_state:
    st.session_state.selected_business_id = None

# Load businesses
@st.cache_data(ttl=60)
def load_businesses(search, industry):
    """Load businesses with filters"""
    with get_session() as session:
        return get_businesses(
            session,
            limit=100,
            offset=0,
            search_query=search if search else None,
            industry_filter=industry if industry != "all" else None
        )

# Main layout: table + detail panel (30% list, 70% details)
table_col, detail_col = st.columns([3, 7])

with table_col:
    st.markdown("### Business List")

    try:
        businesses = load_businesses(search_query, industry_filter)

        if not businesses:
            st.info("No businesses found matching your criteria")
        else:
            # Convert to DataFrame
            businesses_df = pd.DataFrame([
                {
                    "Business Name": b.business_name or "Unnamed",
                    "Industry": b.industry or "N/A",
                    "Phone": format_phone(b.primary_business_phone_number) if b.primary_business_phone_number else "N/A",
                    "ID": str(b.id)
                }
                for b in businesses
            ])

            # Add selection handler
            st.markdown("*Click on a row to view details*")

            # Display DataFrame with row selection
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

            # Show count
            st.caption(f"Showing {len(businesses)} businesses")

    except Exception as e:
        st.error(f"Failed to load businesses: {str(e)}")

with detail_col:
    st.markdown("### Business Details")

    if st.session_state.selected_business_id:
        # Load full business details
        @st.cache_data(ttl=60)
        def load_business_details(business_id):
            """Load business details with related data"""
            with get_session() as session:
                business = get_business_by_id(session, business_id)
                if not business:
                    return None

                user = get_user_by_id(session, str(business.user_id))
                recent_calls = get_calls_by_business(session, business_id, limit=5)

                return {
                    "business": business,
                    "user": user,
                    "recent_calls": recent_calls
                }

        try:
            details = load_business_details(st.session_state.selected_business_id)

            if not details or not details["business"]:
                st.warning("Business not found")
            else:
                business = details["business"]

                # Business info card
                st.markdown("#### Basic Info")
                st.markdown(f"**Name:** {business.business_name or 'Unnamed'}")
                st.markdown(f"**Business ID:** {business.id}")
                st.markdown(f"**Industry:** {business.industry or 'N/A'}")
                if business.primary_business_phone_number:
                    st.markdown(f"**Phone:** {format_phone(business.primary_business_phone_number)}")
                if business.primary_address:
                    st.markdown(f"**Address:** {business.primary_address}")
                if business.website_url:
                    st.markdown(f"**Website:** [{business.website_url}]({business.website_url})")
                st.markdown(f"**Timezone:** {business.timezone or 'N/A'}")
                st.markdown(f"**Created:** {format_datetime(business.created_at)}")

                st.divider()

                # Carrier Call Forwarding Instructions
                render_carrier_instructions(business)

                st.divider()

                # Owner info
                st.markdown("#### Owner")
                if details["user"]:
                    user = details["user"]
                    st.markdown(f"**Email:** {user.email}")
                    st.markdown(f"**Name:** {user.full_name or 'N/A'}")
                else:
                    st.caption("Owner not found")

                st.divider()

                # Twilio Phone Number info
                st.markdown("#### Twilio Phone Number")
                if business.twilio_phone_number:
                    phone_number = business.twilio_phone_number
                    st.markdown(f"**Phone Number:** {format_phone(phone_number.phone_number)}")
                    st.markdown(f"**Status:** {format_status_badge(phone_number.status)}")
                    if phone_number.assigned_at:
                        st.markdown(f"**Assigned Date:** {format_datetime(phone_number.assigned_at)}")
                else:
                    st.caption("Not Assigned")

                st.divider()

                # Business overview
                if business.business_overview:
                    st.markdown("#### Overview")
                    st.text_area("Business Overview", business.business_overview, height=100, disabled=True)
                    st.divider()

                # Recent calls
                st.markdown("#### Recent Calls")
                if details["recent_calls"]:
                    for call in details["recent_calls"]:
                        st.markdown(f"- **{format_phone(call.caller_phone_number)}** - {call.call_status}")
                        st.caption(f"  {format_datetime(call.call_start_time)}")
                else:
                    st.caption("No recent calls")

                st.divider()

                # Quick Actions
                st.markdown("#### Quick Actions")
                st.button("📞 View All Calls", disabled=True, help="Go to Call Logs page")
                st.button("🤖 View Agent Details", disabled=True, help="Go to Agents page to see full configuration")

        except Exception as e:
            st.error(f"Failed to load business details: {str(e)}")

    else:
        st.info("Select a business from the table to view details")

# Export functionality
st.divider()
if st.button("📥 Export to CSV", use_container_width=True):
    try:
        logger = logging.getLogger(__name__)

        with st.spinner("Exporting businesses..."):
            businesses = load_businesses(search_query, industry_filter)

            if not businesses:
                st.warning("No businesses to export")
            else:
                export_df = pd.DataFrame([
                    {
                        "Business Name": b.business_name or "Unnamed",
                        "Industry": b.industry or "N/A",
                        "Phone": format_phone(b.primary_business_phone_number) if b.primary_business_phone_number else "N/A",
                        "Address": b.primary_address or "N/A",
                        "Website": b.website_url or "N/A",
                        "Timezone": b.timezone or "N/A",
                        "Created At": format_datetime(b.created_at) if b.created_at else "N/A",
                        "Business ID": str(b.id)
                    }
                    for b in businesses
                ])

                csv = export_df.to_csv(index=False)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"businesses_{timestamp}.csv",
                    mime="text/csv",
                    key='download-csv',
                    use_container_width=True
                )

                st.success(f"✓ Exported {len(export_df)} businesses")

                if len(businesses) >= 100:
                    st.warning("⚠️ Export limited to 100 businesses. Use filters to export specific businesses.")

    except Exception as e:
        logger.error(f"CSV export failed: {e}", exc_info=True)
        st.error(f"❌ Failed to export: {str(e)}")
