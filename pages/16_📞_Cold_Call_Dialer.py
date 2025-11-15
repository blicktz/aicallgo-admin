"""
Cold Call Dialer - Hidden Page
Browser-based cold calling with WebRTC integration

This page is NOT listed in the main navigation sidebar.
Access via direct URL: /16_📞_Cold_Call_Dialer
"""
import asyncio
import streamlit as st
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import time

# Import authentication
from config.auth import require_auth
from config.settings import settings

# Get provider from environment (deployment config)
PROVIDER = settings.COLD_CALL_PROVIDER.lower()  # 'twilio' or 'telnyx'

# Import cold call components
from components.cold_call.csv_parser import (
    validate_csv,
    parse_contacts,
    update_contact_status,
    get_contact_by_index,
)
from components.cold_call.phone_validator import validate_and_format
from components.cold_call.api_client import ColdCallAPIClient

# Import Odoo integration
from components.cold_call.odoo_integration import get_odoo_integration

# Import Redis service for real-time status
from services.redis_service import get_redis_service

# Page configuration
st.set_page_config(
    page_title="Cold Call Dialer - AICallGO",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS
try:
    with open("static/custom.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# Authentication
if not require_auth():
    st.stop()

# Initialize session state
if 'contacts' not in st.session_state:
    st.session_state.contacts = []

if 'current_call' not in st.session_state:
    st.session_state.current_call = None

if 'call_history' not in st.session_state:
    st.session_state.call_history = []

if 'dialer_state' not in st.session_state:
    st.session_state.dialer_state = 'idle'  # idle, dialing, connected, ended

if 'previous_participant_count' not in st.session_state:
    st.session_state.previous_participant_count = 0

if 'call_state' not in st.session_state:
    st.session_state.call_state = 'idle'  # idle, dialing, ringing, connected, disconnected

if 'play_ringtone' not in st.session_state:
    st.session_state.play_ringtone = False

if 'play_chime' not in st.session_state:
    st.session_state.play_chime = False

if 'play_beep' not in st.session_state:
    st.session_state.play_beep = False

if 'is_muted' not in st.session_state:
    st.session_state.is_muted = False

# Initialize API client
api_client = ColdCallAPIClient()

# Initialize Odoo integration
odoo = get_odoo_integration()

# Initialize session state for Odoo
if 'odoo_filters' not in st.session_state:
    st.session_state.odoo_filters = []

if 'selected_filter_id' not in st.session_state:
    st.session_state.selected_filter_id = None

if 'odoo_pagination' not in st.session_state:
    st.session_state.odoo_pagination = {
        'page': 1,
        'page_size': 50,
        'total': 0,
        'total_pages': 0,
        'filter_name': ''
    }

if 'odoo_status_options' not in st.session_state:
    if odoo.is_available():
        st.session_state.odoo_status_options = odoo.get_status_display_names()
    else:
        st.session_state.odoo_status_options = []

# Import logger
import logging
logger = logging.getLogger(__name__)

# ====================
# Helper Functions
# ====================
def render_twilio_webrtc_component(access_token: str, conference_name: str, client_id: str):
    """Render Twilio WebRTC component for browser audio.

    Args:
        access_token: Twilio access token for WebRTC authentication
        conference_name: Conference SID/name to join
        client_id: Client identifier for participant labeling
    """
    html_code = f"""
    <div id="webrtc-container">
        <script src="https://cdn.jsdelivr.net/npm/@twilio/voice-sdk@2.16.0/dist/twilio.min.js"></script>
        <script>
            // Wait for SDK to load
            window.addEventListener('load', function() {{
                try {{
                    // Verify Twilio SDK is available
                    if (typeof Twilio === 'undefined' || typeof Twilio.Device === 'undefined') {{
                        throw new Error('Twilio Voice SDK not loaded');
                    }}

                    console.log('Twilio Voice SDK loaded successfully');

                    // Initialize Twilio Device with Voice SDK 2.x
                    const device = new Twilio.Device('{access_token}', {{
                        logLevel: 1,
                        codecPreferences: ['opus', 'pcmu'],
                        enableImprovedSignalingErrorPrecision: true
                    }});

                    // Register the device
                    device.register();

                    device.on('registered', function() {{
                        console.log('Twilio Device Ready and Registered');
                        // Auto-connect to conference with conference name and client ID
                        const call = device.connect({{
                            params: {{
                                conference_name: '{conference_name}',
                                client_id: '{client_id}'
                            }}
                        }});
                        console.log('Connecting to conference: {conference_name} as {client_id}');
                    }});

                    device.on('connect', function(connection) {{
                        console.log('Connected to conference!');
                        console.log('Connection parameters:', connection.parameters);
                    }});

                    device.on('disconnect', function(connection) {{
                        console.log('Disconnected from conference');
                    }});

                    device.on('error', function(error) {{
                        console.error('Twilio Device Error:', {{
                            code: error.code,
                            message: error.message,
                            twilioError: error
                        }});
                        alert('WebRTC Error: ' + error.message + ' (Code: ' + error.code + ')');
                    }});

                    device.on('tokenWillExpire', function() {{
                        console.warn('Token will expire soon - should refresh');
                        // TODO: Implement token refresh logic here
                    }});

                }} catch (error) {{
                    console.error('Failed to initialize Twilio Device:', error);
                    alert('Failed to load Twilio Voice SDK: ' + error.message);
                }}
            }});
        </script>
        <div style="padding: 5px; text-align: center; font-size: 0.8em; color: #666;">
            🎧 Audio active
        </div>
    </div>
    """

    st.components.v1.html(html_code, height=40)


def render_telnyx_webrtc_component(sip_username: str, sip_password: str, conference_id: str, client_id: str):
    """Render Telnyx WebRTC component for browser audio.

    Args:
        sip_username: Telnyx SIP username from backend
        sip_password: Telnyx SIP password from backend
        conference_id: Conference ID to join
        client_id: Client identifier for participant labeling
    """
    html_code = f"""
    <div id="telnyx-webrtc-container">
        <script type="text/javascript" src="https://unpkg.com/@telnyx/webrtc@2/lib/bundle.js"></script>
        <script>
            window.addEventListener('load', function() {{
                try {{
                    if (typeof TelnyxRTC === 'undefined') {{
                        throw new Error('Telnyx WebRTC SDK not loaded');
                    }}

                    console.log('Telnyx WebRTC SDK loaded successfully');

                    const client = new TelnyxRTC({{
                        login: '{sip_username}',
                        password: '{sip_password}',
                        ringbackFile: null,
                        ringtoneFile: null,
                    }});

                    client.connect();

                    client.on('telnyx.ready', function() {{
                        console.log('Telnyx WebRTC Ready');
                        const call = client.newCall({{
                            destinationNumber: '{conference_id}',
                            callerName: '{client_id}',
                            audio: true,
                            video: false
                        }});
                        console.log('Calling conference:', '{conference_id}');
                        window.telnyxCall = call;
                    }});

                    client.on('telnyx.socket.error', function(error) {{
                        console.error('WebSocket error:', error);
                        alert('Connection error: ' + (error.message || 'Unknown error'));
                    }});

                    client.on('telnyx.error', function(error) {{
                        console.error('Telnyx error:', error);
                        alert('Telnyx error: ' + (error.message || 'Unknown error'));
                    }});

                    window.telnyxClient = client;

                }} catch (error) {{
                    console.error('Failed to initialize Telnyx WebRTC:', error);
                    alert('Failed to load Telnyx WebRTC: ' + error.message);
                }}
            }});
        </script>
        <div style="padding: 5px; text-align: center; font-size: 0.8em; color: #666;">
            🎧 Telnyx audio active
        </div>
    </div>
    """

    st.components.v1.html(html_code, height=40)


def render_audio_player(play_ringtone: bool = False, play_chime: bool = False, play_beep: bool = False):
    """Render audio player with sound effects.

    Args:
        play_ringtone: Play ringtone sound (looping while dialing)
        play_chime: Play chime sound (when callee connects)
        play_beep: Play beep sound (when callee disconnects)
    """
    # Using simple data URIs for audio to avoid external dependencies
    # Ringtone: 440Hz tone (A4 note) repeating
    # Chime: Pleasant ascending tones (C-E-G major chord)
    # Beep: Short 880Hz tone (A5 note)

    ringtone_cmd = "document.getElementById('ringtone').play();" if play_ringtone else "document.getElementById('ringtone').pause();"
    chime_cmd = "document.getElementById('chime').play();" if play_chime else ""
    beep_cmd = "document.getElementById('beep').play();" if play_beep else ""

    html_code = f"""
    <div id="audio-player" style="display:none;">
        <!-- Ringtone: Looping ring sound (non-preview version) -->
        <audio id="ringtone" loop>
            <source src="https://assets.mixkit.co/active_storage/sfx/2869/2869.mp3" type="audio/mpeg">
        </audio>

        <!-- Chime: Pleasant notification for callee connected (play once, non-preview) -->
        <audio id="chime">
            <source src="https://assets.mixkit.co/active_storage/sfx/2354/2354.mp3" type="audio/mpeg">
        </audio>

        <!-- Beep: Short beep for callee disconnected (play once, non-preview) -->
        <audio id="beep">
            <source src="https://assets.mixkit.co/active_storage/sfx/2870/2870.mp3" type="audio/mpeg">
        </audio>

        <script>
            // Execute audio commands
            {ringtone_cmd}
            {chime_cmd}
            {beep_cmd}
        </script>
    </div>
    """

    st.components.v1.html(html_code, height=0)


def fetch_call_status() -> Optional[Dict[str, Any]]:
    """Fetch call status and detect state transitions.

    Returns:
        Status data dict or None if fetch fails
    """
    if not st.session_state.current_call:
        return None

    # Initialize error counter if not exists
    if 'status_fetch_errors' not in st.session_state:
        st.session_state.status_fetch_errors = 0

    try:
        conf_sid = st.session_state.current_call['conference_sid']
        status_data = api_client.get_status_sync(conference_sid=conf_sid)

        # Reset error counter on success
        st.session_state.status_fetch_errors = 0

        # Detect state transitions
        participant_count = status_data.get('participant_count', 0)
        prev_count = st.session_state.previous_participant_count

        # Detect callee joined (participant count increased to 2+)
        if prev_count < 2 and participant_count >= 2:
            st.session_state.call_state = 'connected'
            st.session_state.play_chime = True  # Trigger chime sound
            logger.info(f"[STATE TRANSITION] Callee connected! Participant count: {participant_count}")

        # Detect callee left (participant count decreased)
        elif prev_count >= 2 and participant_count < 2:
            st.session_state.call_state = 'disconnected'
            st.session_state.play_beep = True  # Trigger beep sound
            logger.info(f"[STATE TRANSITION] Callee disconnected! Participant count: {participant_count}")

        # Detect dialing/ringing (1 participant - just you)
        elif participant_count == 1:
            if st.session_state.call_state == 'idle':
                st.session_state.call_state = 'dialing'

        st.session_state.previous_participant_count = participant_count

        return status_data

    except Exception as e:
        st.session_state.status_fetch_errors += 1
        logger.error(f"[STATUS FETCH ERROR] Attempt {st.session_state.status_fetch_errors}: {str(e)}", exc_info=True)

        # Stop polling after 3 consecutive errors
        if st.session_state.status_fetch_errors >= 3:
            logger.error("[STATUS POLLING] Too many errors, stopping auto-polling")
            st.session_state.polling_active = False

        return None


@st.fragment(run_every="2s")
def render_realtime_call_status():
    """Auto-refreshing fragment that displays real-time call status from Redis.

    This fragment auto-refreshes every 2 seconds to show updated call status
    without requiring manual polling or full page reruns.
    """
    if not st.session_state.get('current_call'):
        return

    conference_sid = st.session_state.current_call.get('conference_sid')
    if not conference_sid:
        return

    try:
        # Get Redis service
        redis_service = get_redis_service()

        # Fetch status from Redis (single source of truth)
        # Uses dedicated synchronous client for reliable reads
        status_data = redis_service.get_cold_call_status_sync(conference_sid)

        if status_data:
            # Update state transitions
            participant_count = status_data.get('participant_count', 0)
            prev_count = st.session_state.get('previous_participant_count', 0)

            # DEBUG: Log what we're reading from Redis
            logger.info(f"[DEBUG FRONTEND] Conference: {conference_sid}, participant_count from Redis: {participant_count}, prev_count: {prev_count}, full_data_keys: {list(status_data.keys())}")

            # Detect state transitions
            if prev_count < 2 and participant_count >= 2:
                st.session_state.call_state = 'connected'
                st.session_state.play_chime = True
                logger.info(f"[REALTIME STATUS] Callee connected! Participants: {participant_count}")
            elif prev_count >= 2 and participant_count < 2:
                st.session_state.call_state = 'disconnected'
                st.session_state.play_beep = True
                logger.info(f"[REALTIME STATUS] Callee disconnected! Participants: {participant_count}")
            elif participant_count == 1 and st.session_state.call_state == 'idle':
                st.session_state.call_state = 'dialing'

            st.session_state.previous_participant_count = participant_count

            # Compact status bar (single row with all key info)
            call_state = st.session_state.get('call_state', 'idle')
            state_config = {
                'idle': {'emoji': '⚪', 'label': 'Idle'},
                'dialing': {'emoji': '📞', 'label': 'Dialing...'},
                'ringing': {'emoji': '📳', 'label': 'Ringing...'},
                'connected': {'emoji': '✅', 'label': 'Connected'},
                'disconnected': {'emoji': '📴', 'label': 'Disconnected'},
            }
            config = state_config.get(call_state, state_config['idle'])

            # Single-row status bar
            status_col1, status_col2, status_col3, status_col4 = st.columns([3, 1, 1, 0.5])

            with status_col1:
                # Conference status + Callee status
                conf_status = status_data.get('status', 'unknown').upper()
                st.markdown(f"📞 **{conf_status}** • {config['emoji']} {config['label']}")

            with status_col2:
                # Participant count
                st.markdown(f"👥 **{participant_count}**")

            with status_col3:
                # Duration timer
                if 'created_at' in status_data:
                    try:
                        from datetime import datetime
                        created = datetime.fromisoformat(status_data['created_at'].replace('Z', '+00:00'))
                        now = datetime.utcnow()
                        duration_secs = int((now - created).total_seconds())
                        duration_mins = duration_secs // 60
                        duration_rem_secs = duration_secs % 60
                        st.markdown(f"⏱️ **{duration_mins:02d}:{duration_rem_secs:02d}**")
                    except:
                        st.markdown("⏱️ **--:--**")
                else:
                    st.markdown("⏱️ **--:--**")

            with status_col4:
                # Mic indicator
                mic_icon = "🔇" if st.session_state.is_muted else "🎤"
                st.markdown(mic_icon)

            # Collapsible details section
            with st.expander("📊 Call Details", expanded=False):
                # Recent events (if available)
                if 'events' in status_data and status_data['events']:
                    st.markdown("**Recent Events:**")
                    for event in reversed(status_data['events'][-5:]):  # Show last 5 events
                        event_type = event.get('type', 'unknown')
                        timestamp = event.get('timestamp', '')
                        st.text(f"• {event_type} at {timestamp}")
                else:
                    st.text("No events yet")

                # Last update timestamp
                if 'updated_at' in status_data:
                    st.caption(f"Last updated: {status_data['updated_at']}")
        else:
            # No data in Redis yet - show waiting message
            st.info("⏳ Waiting for call status... (Connecting to Twilio)")

    except Exception as e:
        logger.error(f"[REALTIME STATUS ERROR] {str(e)}", exc_info=True)
        st.error(f"Status update error: {str(e)}")


# ====================
# Header
# ====================
st.title("📞 Cold Call Dialer")
st.caption(f"Using {PROVIDER.title()} • Configured in deployment")
st.markdown("### Upload contacts and make calls directly from your browser")
st.markdown("---")

# ====================
# Contact Loading Section
# ====================
if not st.session_state.contacts:
    st.subheader("📤 Load Contact List")

    # Create tabs for CSV upload and Odoo loading
    if odoo.is_available():
        tab1, tab2 = st.tabs(["📊 Load from Odoo", "📄 Upload CSV"])
    else:
        tab1, tab2 = st.tabs(["📄 Upload CSV", "ℹ️ Odoo Not Available"])
        # Swap tabs if Odoo not available
        tab2, tab1 = tab1, tab2

    # Odoo Filter Loading Tab
    with tab1:
        if odoo.is_available():
            st.markdown("### Load contacts from Odoo CRM saved search")

            # Fetch filters button
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button("🔄 Refresh Filters", use_container_width=True):
                    with st.spinner("Fetching filters from Odoo..."):
                        st.session_state.odoo_filters = odoo.get_available_filters()
                    if st.session_state.odoo_filters:
                        st.success(f"Found {len(st.session_state.odoo_filters)} filters")
                    else:
                        st.warning("No filters found")

            # Auto-fetch on first load
            if not st.session_state.odoo_filters:
                with st.spinner("Fetching filters from Odoo..."):
                    st.session_state.odoo_filters = odoo.get_available_filters()

            if st.session_state.odoo_filters:
                # Filter selection
                filter_names = [f['name'] for f in st.session_state.odoo_filters]
                selected_filter_name = st.selectbox(
                    "Select a saved search",
                    options=filter_names,
                    help="Choose one of your Odoo favorite filters"
                )

                # Get selected filter ID
                selected_filter = next(
                    (f for f in st.session_state.odoo_filters if f['name'] == selected_filter_name),
                    None
                )

                if selected_filter:
                    filter_id = selected_filter['id']

                    # Get total count
                    total_contacts = odoo.get_filter_contact_count(filter_id)
                    st.info(f"📊 This filter contains **{total_contacts}** contacts")

                    # Load contacts button (always loads page 1)
                    if st.button("📥 Load Contacts", type="primary", use_container_width=True):
                        with st.spinner(f"Loading contacts from '{selected_filter_name}'..."):
                            # Always load page 1 with default page size (reduced from 50 to 20 for better performance)
                            default_page_size = 20
                            result = odoo.load_contacts_from_filter(filter_id, page=1, page_size=default_page_size)

                            if 'error' in result:
                                st.error(f"❌ Error: {result['error']}")
                            elif result['contacts']:
                                st.session_state.contacts = result['contacts']
                                st.session_state.odoo_pagination = {
                                    'page': result['page'],
                                    'page_size': result['page_size'],
                                    'total': result['total'],
                                    'total_pages': result['total_pages'],
                                    'filter_name': result['filter_name'],
                                    'filter_id': filter_id  # Store filter_id for navigation
                                }
                                st.success(
                                    f"✅ Loaded {len(result['contacts'])} contacts "
                                    f"from '{result['filter_name']}' "
                                    f"(page {result['page']}/{result['total_pages']})"
                                )
                                st.rerun()
                            else:
                                st.warning("No contacts found with phone numbers")
            else:
                st.info("No saved searches found in Odoo. Create filters in Odoo CRM first.")
        else:
            st.warning("""
            **Odoo integration not available**

            To enable Odoo integration, configure the following environment variables:
            - `ODOO_URL` - Odoo instance URL
            - `ODOO_DB` - Database name
            - `ODOO_USERNAME` - Username
            - `ODOO_PASSWORD` - Password
            """)

    # CSV Upload Tab
    with tab2:
        st.markdown("### Upload CSV file with contacts")

        col1, col2 = st.columns([2, 1])

        with col1:
            uploaded_file = st.file_uploader(
                "Upload CSV file with contacts",
                type=['csv'],
                help="CSV must contain columns: name, company, phone (optional: title)",
            )

        with col2:
            st.markdown("**Required columns:**")
            st.markdown("- `name` - Contact name")
            st.markdown("- `company` - Company name")
            st.markdown("- `phone` - Phone number")
            st.markdown("- `title` - Job title (optional)")

        if uploaded_file is not None:
            with st.spinner("Validating CSV..."):
                is_valid, error = validate_csv(uploaded_file)

            if is_valid:
                st.success("✅ CSV validation passed")

                try:
                    contacts = parse_contacts(uploaded_file)
                    st.session_state.contacts = contacts
                    st.session_state.odoo_pagination = {
                        'page': 1,
                        'page_size': len(contacts),
                        'total': len(contacts),
                        'total_pages': 1,
                        'filter_name': 'CSV Upload'
                    }
                    st.success(f"✅ Loaded {len(contacts)} contacts")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error parsing CSV: {str(e)}")
            else:
                st.error(f"❌ CSV validation failed: {error}")

        # Example CSV format
        with st.expander("📋 Example CSV Format"):
            st.code("""name,company,phone,title
John Doe,Acme Corp,+15551234567,Sales Manager
Jane Smith,Tech Inc,(555) 987-6543,CEO
Bob Johnson,Widget Co,555-111-2222,Director""", language="csv")

else:
    # ====================
    # Contact List Section
    # ====================
    st.subheader(f"📋 Contact List ({len(st.session_state.contacts)} contacts)")

    # Show pagination info if from Odoo
    if st.session_state.odoo_pagination.get('filter_name'):
        pagination = st.session_state.odoo_pagination
        if pagination['filter_name'] != 'CSV Upload':
            st.info(
                f"📊 Showing page {pagination['page']}/{pagination['total_pages']} "
                f"from Odoo filter '{pagination['filter_name']}' "
                f"({pagination['total']} total contacts)"
            )

    col1, col2 = st.columns([3, 1])

    with col2:
        if st.button("🔄 Load New List", use_container_width=True):
            st.session_state.contacts = []
            st.session_state.current_call = None
            st.session_state.odoo_pagination = {
                'page': 1,
                'page_size': 50,
                'total': 0,
                'total_pages': 0,
                'filter_name': ''
            }
            st.rerun()

    # Display contacts in table with dial buttons
    # Header row
    header_cols = st.columns([2.5, 1.5, 1, 1.5, 0.8, 1.5, 1.5, 1])
    header_cols[0].markdown("**Name/Company**")
    header_cols[1].markdown("**Phone**")
    header_cols[2].markdown("**Carrier**")
    header_cols[3].markdown("**Status**")
    header_cols[4].markdown("**Lead/ICP**")
    header_cols[5].markdown("**Google**")
    header_cols[6].markdown("**Outbound**")
    header_cols[7].markdown("")  # Dial button column

    st.markdown("---")

    for idx, contact in enumerate(st.session_state.contacts):
        # Main row
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([2.5, 1.5, 1, 1.5, 0.8, 1.5, 1.5, 1])

        with col1:
            # Smart display: combine name and company
            name = (contact.get('name') or '').strip()
            company = (contact.get('company') or '').strip()

            if name and company:
                # Both exist - check if identical (case-insensitive)
                if name.lower() == company.lower():
                    # Identical - show only one
                    st.text(name)
                else:
                    # Different - show both
                    st.text(f"{name}, {company}")
            elif name:
                # Only name
                st.text(name)
            elif company:
                # Only company
                st.text(company)
            else:
                # Neither
                st.text("(No name)")

        with col2:
            st.text(contact['phone'])

        with col3:
            # Show carrier type
            carrier = (contact.get('carrier_type') or '').strip()
            st.text(carrier if carrier else '-')

        with col4:
            # Show Odoo cold call status
            odoo_status = (contact.get('current_odoo_status') or '').strip()
            st.text(odoo_status if odoo_status else "Not Started")

        with col5:
            # Show Lead/ICP status (Valid Lead | Julya ICP)
            valid_lead = contact.get('is_valid_lead', '-')
            julya_icp = contact.get('is_julya_icp', '-')
            st.text(f"{valid_lead}|{julya_icp}")

        with col6:
            # Show Google rating and reviews
            rating = contact.get('google_rating', 0)
            review_count = contact.get('google_review_count', 0)
            if rating and rating > 0:
                st.text(f"★ {rating:.1f} ({review_count})")
            else:
                st.text("-")

        with col7:
            # Show outbound status (only non-zero fields, names only)
            outbound_fields = []
            if contact.get('outbound_ivr', 0) > 0:
                outbound_fields.append('IVR')
            if contact.get('outbound_live', 0) > 0:
                outbound_fields.append('Live')
            if contact.get('outbound_no_answer', 0) > 0:
                outbound_fields.append('No Answer')
            if contact.get('outbound_voicemail', 0) > 0:
                outbound_fields.append('Voicemail')

            if outbound_fields:
                st.text(', '.join(outbound_fields))
            else:
                st.text('-')

        with col8:
            # Dial button (always available when not in a call)
            if st.session_state.dialer_state == 'idle':
                # Show "Dial" or "Redial" based on Odoo status
                odoo_status = (contact.get('current_odoo_status') or '').strip()
                button_label = "🔁 Redial" if odoo_status else "📞 Dial"

                if st.button(button_label, key=f"dial_{idx}", use_container_width=True):
                    # Validate and format phone number
                    is_valid, formatted_phone, error = validate_and_format(contact['phone'])

                    if not is_valid:
                        st.error(f"Invalid phone number: {error}")
                    else:
                        # Initiate call (formatted_phone is used for dialing, original preserved for display)
                        st.session_state.current_call = {
                            'contact_idx': idx,
                            'contact': contact,
                            'formatted_phone': formatted_phone,
                            'start_time': datetime.now(),
                        }
                        st.session_state.dialer_state = 'dialing'
                        st.session_state.is_muted = False  # Reset mute state for new call
                        st.rerun()

        # Expandable Business Insights section
        if contact.get('comment'):
            with st.expander("📋 Business Insights", expanded=False):
                comment_text = contact['comment']

                # Use scrollable container for long content (>2000 chars ≈ 400 words)
                if len(comment_text) > 2000:
                    with st.container(height=400):
                        st.markdown(comment_text, unsafe_allow_html=True)
                    st.caption("↑ Scroll for more ↑")
                else:
                    # Show full content if not too long
                    st.markdown(comment_text, unsafe_allow_html=True)

    # ====================
    # Pagination Controls (for Odoo loaded contacts)
    # ====================
    if (st.session_state.contacts and
        st.session_state.odoo_pagination.get('filter_name') and
        st.session_state.odoo_pagination['filter_name'] != 'CSV Upload'):

        st.markdown("---")
        st.markdown("### 📄 Page Navigation")

        pagination = st.session_state.odoo_pagination
        current_page = pagination['page']
        total_pages = pagination['total_pages']
        filter_id = pagination.get('filter_id')

        # Create columns for pagination controls
        col1, col2, col3, col4, col5 = st.columns([1, 1.5, 1, 2, 1.5])

        with col1:
            # Previous button
            if st.button("◀ Previous", disabled=(current_page <= 1), use_container_width=True):
                with st.spinner("Loading previous page..."):
                    result = odoo.load_contacts_from_filter(
                        filter_id,
                        page=current_page - 1,
                        page_size=pagination['page_size']
                    )
                    if result['contacts']:
                        st.session_state.contacts = result['contacts']
                        st.session_state.odoo_pagination.update({
                            'page': result['page'],
                            'total': result['total'],
                            'total_pages': result['total_pages']
                        })
                        st.rerun()

        with col2:
            # Page indicator
            st.markdown(f"**Page {current_page} of {total_pages}**")

        with col3:
            # Next button
            if st.button("Next ▶", disabled=(current_page >= total_pages), use_container_width=True):
                with st.spinner("Loading next page..."):
                    result = odoo.load_contacts_from_filter(
                        filter_id,
                        page=current_page + 1,
                        page_size=pagination['page_size']
                    )
                    if result['contacts']:
                        st.session_state.contacts = result['contacts']
                        st.session_state.odoo_pagination.update({
                            'page': result['page'],
                            'total': result['total'],
                            'total_pages': result['total_pages']
                        })
                        st.rerun()

        with col4:
            # Jump to page
            jump_col1, jump_col2 = st.columns([2, 1])
            with jump_col1:
                jump_page = st.number_input(
                    "Jump to:",
                    min_value=1,
                    max_value=total_pages,
                    value=current_page,
                    key="jump_page_input",
                    label_visibility="collapsed"
                )
            with jump_col2:
                if st.button("Go", use_container_width=True):
                    if jump_page != current_page:
                        with st.spinner(f"Loading page {jump_page}..."):
                            result = odoo.load_contacts_from_filter(
                                filter_id,
                                page=jump_page,
                                page_size=pagination['page_size']
                            )
                            if result['contacts']:
                                st.session_state.contacts = result['contacts']
                                st.session_state.odoo_pagination.update({
                                    'page': result['page'],
                                    'total': result['total'],
                                    'total_pages': result['total_pages']
                                })
                                st.rerun()

        with col5:
            # Page size selector
            page_size_options = [20, 25, 50, 100, 200]
            # Find current page size index, default to 20 if not found
            try:
                current_index = page_size_options.index(pagination['page_size'])
            except ValueError:
                current_index = 0  # Default to 20

            new_page_size = st.selectbox(
                "Per page:",
                options=page_size_options,
                index=current_index,
                key="pagination_page_size",
                label_visibility="collapsed"
            )

            # Reload if page size changed
            if new_page_size != pagination['page_size']:
                with st.spinner(f"Reloading with {new_page_size} contacts per page..."):
                    # Calculate which page to show (try to keep roughly same position)
                    old_first_contact = (current_page - 1) * pagination['page_size']
                    new_page = max(1, (old_first_contact // new_page_size) + 1)

                    result = odoo.load_contacts_from_filter(
                        filter_id,
                        page=new_page,
                        page_size=new_page_size
                    )
                    if result['contacts']:
                        st.session_state.contacts = result['contacts']
                        st.session_state.odoo_pagination.update({
                            'page': result['page'],
                            'page_size': result['page_size'],
                            'total': result['total'],
                            'total_pages': result['total_pages']
                        })
                        st.rerun()

    # ====================
    # Dialer Modal
    # ====================
    @st.dialog("📞 Call in Progress", width="large")
    def show_dialer():
        """Display the dialer modal during an active call."""
        if not st.session_state.current_call:
            st.error("No active call")
            return

        call = st.session_state.current_call
        contact = call['contact']

        # Initialize call state if not set
        if st.session_state.dialer_state == 'connected' and 'call_state' not in st.session_state:
            st.session_state.call_state = 'dialing'  # Initial state

        # Display contact info (compact 3-line format)
        st.markdown(f"## {contact['name']}")
        st.caption(f"{contact['company']} • {call['formatted_phone']}")

        # Add address line (compact)
        address_parts = []
        if contact.get('street'):
            address_parts.append(contact['street'])
        if contact.get('city'):
            address_parts.append(contact['city'])
        if contact.get('state'):
            address_parts.append(contact['state'])

        if address_parts:
            st.caption(", ".join(address_parts))

        st.markdown("---")

        # Initiate call if in dialing state
        if st.session_state.dialer_state == 'dialing':
            with st.spinner("Creating conference and dialing..."):
                try:
                    # Call the initiate endpoint with configured provider
                    response = api_client.initiate_call_sync(
                        to_phone=call['formatted_phone'],
                        provider=PROVIDER,
                    )

                    # Store conference details
                    st.session_state.current_call['conference_sid'] = response['conference_sid']
                    st.session_state.current_call['conference_id'] = response['conference_id']
                    st.session_state.current_call['call_sid'] = response['call_sid']

                    # Update state
                    st.session_state.dialer_state = 'connecting'
                    st.rerun()

                except Exception as e:
                    st.error(f"Failed to initiate call: {str(e)}")
                    st.session_state.dialer_state = 'ended'
                    return

        # Join WebRTC if in connecting state
        if st.session_state.dialer_state == 'connecting':
            with st.spinner("Connecting your browser to the call..."):
                try:
                    # Generate client ID
                    client_id = f"admin-{uuid.uuid4().hex[:8]}"

                    # Join WebRTC
                    webrtc_response = api_client.join_webrtc_sync(
                        conference_id=st.session_state.current_call['conference_sid'],
                        client_id=client_id,
                        provider=PROVIDER,  # Pass provider (telnyx or twilio)
                    )

                    # Store provider-specific WebRTC credentials
                    if PROVIDER == 'twilio':
                        st.session_state.current_call['access_token'] = webrtc_response['access_token']
                    elif PROVIDER == 'telnyx':
                        st.session_state.current_call['sip_username'] = webrtc_response['sip_username']
                        st.session_state.current_call['sip_password'] = webrtc_response['sip_password']

                    st.session_state.current_call['participant_sid'] = webrtc_response['participant_sid']
                    st.session_state.current_call['client_id'] = client_id

                    # Update state
                    st.session_state.dialer_state = 'connected'
                    st.rerun()

                except Exception as e:
                    st.error(f"Failed to connect WebRTC: {str(e)}")
                    st.session_state.dialer_state = 'ended'
                    return

        # Show WebRTC component if connected
        if st.session_state.dialer_state == 'connected':
            # Render provider-specific WebRTC component
            if PROVIDER == 'twilio':
                render_twilio_webrtc_component(
                    st.session_state.current_call['access_token'],
                    st.session_state.current_call['conference_sid'],
                    st.session_state.current_call['client_id']
                )
            elif PROVIDER == 'telnyx':
                render_telnyx_webrtc_component(
                    st.session_state.current_call['sip_username'],
                    st.session_state.current_call['sip_password'],
                    st.session_state.current_call['conference_id'],
                    st.session_state.current_call['client_id']
                )

            # Status bar with real-time data (will be rendered by fragment below)
            # This section intentionally left minimal - fragment provides live status

            # Call controls
            col1, col2 = st.columns(2)

            with col1:
                # Single toggle button for mute/unmute
                btn_label = "🔊 Unmute Mic" if st.session_state.is_muted else "🔇 Mute Mic"
                btn_type = "secondary" if st.session_state.is_muted else "primary"

                if st.button(btn_label, use_container_width=True, type=btn_type, key="toggle_mute_btn"):
                    try:
                        # Toggle the mute state
                        new_mute_state = not st.session_state.is_muted

                        api_client.mute_participant_sync(
                            conference_sid=st.session_state.current_call['conference_sid'],
                            participant_sid=st.session_state.current_call['participant_sid'],
                            muted=new_mute_state,
                        )

                        # Update state only after successful API call
                        st.session_state.is_muted = new_mute_state

                        # Force rerun to sync button label with actual state
                        st.rerun()

                    except Exception as e:
                        st.error(f"Mute toggle failed: {str(e)}")

            with col2:
                if st.button("📴 End Call", use_container_width=True, type="primary", key="end_call_btn"):
                    try:
                        api_client.end_call_sync(
                            conference_sid=st.session_state.current_call['conference_sid'],
                        )
                        st.session_state.dialer_state = 'ended'
                        st.rerun()
                    except Exception as e:
                        st.error(f"End call failed: {str(e)}")

            st.markdown("---")

            # Real-time status panel with compact display
            render_realtime_call_status()

            # Audio feedback based on call state
            play_ringtone = st.session_state.call_state in ['dialing', 'ringing']
            play_chime = st.session_state.get('play_chime', False)
            play_beep = st.session_state.get('play_beep', False)

            # Render audio player
            render_audio_player(
                play_ringtone=play_ringtone,
                play_chime=play_chime,
                play_beep=play_beep
            )

            # Reset one-shot audio triggers after playing
            if st.session_state.get('play_chime'):
                st.session_state.play_chime = False
            if st.session_state.get('play_beep'):
                st.session_state.play_beep = False

        # Post-call logging
        if st.session_state.dialer_state == 'ended':
            st.markdown("---")
            st.subheader("📝 Log Call Outcome")

            # Use dynamic Odoo status options if available, otherwise fallback
            if st.session_state.odoo_status_options:
                outcome = st.selectbox(
                    "Call Outcome",
                    st.session_state.odoo_status_options,
                    key="call_outcome",
                    help="Status options from Odoo CRM"
                )
            else:
                outcome = st.selectbox(
                    "Call Outcome",
                    ["Connected", "Voicemail", "No Answer", "Busy", "Wrong Number", "Callback Requested"],
                    key="call_outcome",
                )

            notes = st.text_area(
                "Notes",
                height=150,
                placeholder="Add notes about this call...",
                key="call_notes",
            )

            # Show Odoo sync option if contact has odoo_id
            save_to_odoo = False
            if contact.get('odoo_id') and odoo.is_available():
                save_to_odoo = st.checkbox(
                    "📊 Save to Odoo CRM",
                    value=True,
                    help="Update contact status and create activity note in Odoo"
                )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Save & Close", use_container_width=True, type="primary"):
                    # Calculate duration
                    duration = int((datetime.now() - call['start_time']).total_seconds())

                    # Save to history
                    st.session_state.call_history.append({
                        'contact': contact,
                        'outcome': outcome,
                        'notes': notes,
                        'timestamp': datetime.now(),
                        'duration': duration,
                    })

                    # Save to Odoo if enabled
                    if save_to_odoo and contact.get('odoo_id'):
                        with st.spinner("Saving to Odoo..."):
                            result = odoo.complete_call(
                                odoo_id=contact['odoo_id'],
                                status_name=outcome,
                                duration=duration,
                                notes=notes
                            )

                            if result['success']:
                                # Update local contact's Odoo status to reflect the change
                                if result['status_updated']:
                                    st.session_state.contacts[call['contact_idx']]['current_odoo_status'] = outcome

                                st.success("✅ Saved to Odoo CRM")
                                if not result['status_updated']:
                                    st.warning("⚠️ Status field not updated (check field mapping)")
                                if not result['note_created']:
                                    st.warning("⚠️ Note not created (check Odoo permissions)")
                            else:
                                st.error(f"❌ Failed to save to Odoo: {result.get('error', 'Unknown error')}")
                                time.sleep(2)  # Show error briefly

                    # Clear current call
                    st.session_state.current_call = None
                    st.session_state.dialer_state = 'idle'
                    st.rerun()

            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    # Clear current call
                    st.session_state.current_call = None
                    st.session_state.dialer_state = 'idle'
                    st.rerun()

    # Show dialer modal if there's an active call
    if st.session_state.current_call and st.session_state.dialer_state != 'idle':
        show_dialer()

# ====================
# Call History Section
# ====================
if st.session_state.call_history:
    st.markdown("---")
    st.subheader("📊 Call History")

    for idx, call in enumerate(reversed(st.session_state.call_history)):
        with st.expander(f"{call['contact']['name']} - {call['outcome']} ({call['timestamp'].strftime('%H:%M:%S')})"):
            st.markdown(f"**Company:** {call['contact']['company']}")
            st.markdown(f"**Phone:** {call['contact']['phone']}")
            st.markdown(f"**Duration:** {int(call['duration'])} seconds")
            st.markdown(f"**Outcome:** {call['outcome']}")
            if call['notes']:
                st.markdown(f"**Notes:** {call['notes']}")
