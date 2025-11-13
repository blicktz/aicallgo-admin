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

# Import cold call components
from components.cold_call.csv_parser import (
    validate_csv,
    parse_contacts,
    update_contact_status,
    get_contact_by_index,
)
from components.cold_call.phone_validator import validate_and_format
from components.cold_call.api_client import ColdCallAPIClient

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

# Import logger
import logging
logger = logging.getLogger(__name__)

# ====================
# Helper Functions
# ====================
def render_webrtc_component(access_token: str, conference_name: str, client_id: str):
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
        <div style="padding: 20px; background: #f0f0f0; border-radius: 8px; text-align: center;">
            <p style="margin: 0; color: #333;">🎧 Browser audio active</p>
            <p style="margin: 5px 0 0 0; font-size: 0.9em; color: #666;">Speak into your microphone</p>
        </div>
    </div>
    """

    st.components.v1.html(html_code, height=150)


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

            # Display status UI
            st.markdown("### 📊 Real-Time Call Status")

            # Connection state display
            call_state = st.session_state.get('call_state', 'idle')
            state_config = {
                'idle': {'emoji': '⚪', 'label': 'Idle', 'color': 'gray'},
                'dialing': {'emoji': '📞', 'label': 'Dialing...', 'color': 'orange'},
                'ringing': {'emoji': '📳', 'label': 'Ringing...', 'color': 'blue'},
                'connected': {'emoji': '✅', 'label': 'Callee Connected', 'color': 'green'},
                'disconnected': {'emoji': '📴', 'label': 'Callee Disconnected', 'color': 'red'},
            }
            config = state_config.get(call_state, state_config['idle'])

            # Display connection status
            st.markdown(f"#### {config['emoji']} {config['label']}")

            # Display metrics in columns
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Conference Status", status_data.get('status', 'unknown').upper())
            with col_b:
                st.metric("Participants", participant_count)
            with col_c:
                # Calculate duration from timestamps if available
                if 'created_at' in status_data:
                    try:
                        from datetime import datetime
                        created = datetime.fromisoformat(status_data['created_at'].replace('Z', '+00:00'))
                        now = datetime.utcnow()
                        duration_secs = int((now - created).total_seconds())
                        duration_mins = duration_secs // 60
                        duration_secs = duration_secs % 60
                        st.metric("Duration", f"{duration_mins}m {duration_secs}s")
                    except:
                        st.metric("Duration", "N/A")
                else:
                    st.metric("Duration", "N/A")

            # Display last update time
            if 'updated_at' in status_data:
                st.caption(f"Last updated: {status_data['updated_at']}")

            # Display recent events (if available)
            if 'events' in status_data and status_data['events']:
                with st.expander("📜 Recent Events", expanded=False):
                    for event in reversed(status_data['events'][-5:]):  # Show last 5 events
                        event_type = event.get('type', 'unknown')
                        timestamp = event.get('timestamp', '')
                        st.text(f"• {event_type} at {timestamp}")
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
st.markdown("### Upload contacts and make calls directly from your browser")
st.markdown("---")

# ====================
# CSV Upload Section
# ====================
if not st.session_state.contacts:
    st.subheader("📤 Upload Contact List")

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

    col1, col2 = st.columns([3, 1])

    with col2:
        if st.button("🔄 Load New List", use_container_width=True):
            st.session_state.contacts = []
            st.session_state.current_call = None
            st.rerun()

    # Display contacts in table with dial buttons
    for idx, contact in enumerate(st.session_state.contacts):
        col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 1.5, 1.5, 1])

        with col1:
            st.text(contact['name'])

        with col2:
            st.text(contact['company'])

        with col3:
            st.text(contact['phone'])

        with col4:
            # Status badge
            status_color = {
                'pending': '🔵',
                'calling': '📞',
                'completed': '✅',
                'failed': '❌',
            }
            st.text(f"{status_color.get(contact['status'], '⚪')} {contact['status']}")

        with col5:
            if contact.get('call_outcome'):
                st.text(contact['call_outcome'])

        with col6:
            # Dial button (allow redialing completed/failed contacts)
            if contact['status'] in ['pending', 'completed', 'failed'] and st.session_state.dialer_state == 'idle':
                # Change button label based on status
                button_label = "📞 Dial" if contact['status'] == 'pending' else "🔁 Redial"
                if st.button(button_label, key=f"dial_{idx}", use_container_width=True):
                    # Validate and format phone number
                    is_valid, formatted_phone, error = validate_and_format(contact['phone'])

                    if not is_valid:
                        st.error(f"Invalid phone number: {error}")
                    else:
                        # Update contact with formatted phone
                        st.session_state.contacts[idx]['phone'] = formatted_phone

                        # Initiate call
                        st.session_state.current_call = {
                            'contact_idx': idx,
                            'contact': contact,
                            'formatted_phone': formatted_phone,
                            'start_time': datetime.now(),
                        }
                        st.session_state.dialer_state = 'dialing'
                        st.session_state.is_muted = False  # Reset mute state for new call
                        update_contact_status(st.session_state.contacts, idx, 'calling')
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

        # Display contact info
        st.markdown(f"### Calling: {contact['name']}")
        st.markdown(f"**Company:** {contact['company']}")
        st.markdown(f"**Phone:** {call['formatted_phone']}")

        # Call state display
        state_messages = {
            'dialing': '📞 Initiating call...',
            'connecting': '🔗 Connecting to conference...',
            'connected': '✅ Connected',
            'ended': '📴 Call ended',
        }

        st.info(state_messages.get(st.session_state.dialer_state, 'Unknown state'))

        # Initiate call if in dialing state
        if st.session_state.dialer_state == 'dialing':
            with st.spinner("Creating conference and dialing..."):
                try:
                    # Call the initiate endpoint
                    response = api_client.initiate_call_sync(
                        to_phone=call['formatted_phone'],
                        provider='twilio',
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
                    update_contact_status(
                        st.session_state.contacts,
                        call['contact_idx'],
                        'failed',
                        'failed',
                        f"Error: {str(e)}",
                    )
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
                    )

                    # Store WebRTC details
                    st.session_state.current_call['access_token'] = webrtc_response['access_token']
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
            st.success("✅ Call connected! Browser audio active.")

            # Render WebRTC component
            render_webrtc_component(
                st.session_state.current_call['access_token'],
                st.session_state.current_call['conference_sid'],
                st.session_state.current_call['client_id']
            )

            # Call timer
            elapsed = (datetime.now() - call['start_time']).total_seconds()
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            st.metric("Call Duration", f"{minutes:02d}:{seconds:02d}")

            # Microphone status indicator
            mic_status = "🔇 Muted" if st.session_state.is_muted else "🎤 Active"
            mic_color = "red" if st.session_state.is_muted else "green"
            st.markdown(f"**Microphone:** :{mic_color}[{mic_status}]")

            # Call controls
            col1, col2, col3 = st.columns(3)

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

            # Always-visible real-time status panel
            st.markdown("---")

            # Use the new fragment-based real-time status display
            # This auto-refreshes every 2 seconds without manual polling
            render_realtime_call_status()

            # Display called number info
            st.markdown("**📱 Called Number:**")
            st.code(call['formatted_phone'])

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

            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Save & Close", use_container_width=True, type="primary"):
                    # Update contact
                    update_contact_status(
                        st.session_state.contacts,
                        call['contact_idx'],
                        'completed',
                        outcome,
                        notes,
                    )

                    # Save to history
                    st.session_state.call_history.append({
                        'contact': contact,
                        'outcome': outcome,
                        'notes': notes,
                        'timestamp': datetime.now(),
                        'duration': (datetime.now() - call['start_time']).total_seconds(),
                    })

                    # Clear current call
                    st.session_state.current_call = None
                    st.session_state.dialer_state = 'idle'
                    st.rerun()

            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    # Mark as failed
                    update_contact_status(
                        st.session_state.contacts,
                        call['contact_idx'],
                        'pending',
                        '',
                        '',
                    )

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
