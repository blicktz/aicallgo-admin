"""
Cold Call Dialer - Hidden Page
Browser-based cold calling with WebRTC integration

This page is NOT listed in the main navigation sidebar.
Access via direct URL: /16_📞_Cold_Call_Dialer
"""
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

# Initialize API client
api_client = ColdCallAPIClient()

# ====================
# Helper Functions
# ====================
def render_webrtc_component(access_token: str, conference_name: str):
    """Render Twilio WebRTC component for browser audio.

    Args:
        access_token: Twilio access token for WebRTC authentication
        conference_name: Conference SID/name to join
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
                        // Auto-connect to conference with conference name parameter
                        const call = device.connect({{
                            params: {{
                                conference_name: '{conference_name}'
                            }}
                        }});
                        console.log('Connecting to conference: {conference_name}');
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
            # Dial button
            if contact['status'] == 'pending' and st.session_state.dialer_state == 'idle':
                if st.button("📞 Dial", key=f"dial_{idx}", use_container_width=True):
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
                st.session_state.current_call['conference_sid']
            )

            # Call timer
            elapsed = (datetime.now() - call['start_time']).total_seconds()
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            st.metric("Call Duration", f"{minutes:02d}:{seconds:02d}")

            # Call controls
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("🔇 Mute", use_container_width=True, key="mute_btn"):
                    try:
                        api_client.mute_participant_sync(
                            conference_sid=st.session_state.current_call['conference_sid'],
                            participant_sid=st.session_state.current_call['participant_sid'],
                            muted=True,
                        )
                        st.success("Muted")
                    except Exception as e:
                        st.error(f"Mute failed: {str(e)}")

            with col2:
                if st.button("🔊 Unmute", use_container_width=True, key="unmute_btn"):
                    try:
                        api_client.mute_participant_sync(
                            conference_sid=st.session_state.current_call['conference_sid'],
                            participant_sid=st.session_state.current_call['participant_sid'],
                            muted=False,
                        )
                        st.success("Unmuted")
                    except Exception as e:
                        st.error(f"Unmute failed: {str(e)}")

            with col3:
                # Initialize show_call_info in session state
                if 'show_call_info' not in st.session_state:
                    st.session_state.show_call_info = False

                if st.button("ℹ️ Call Info", use_container_width=True, key="info_btn"):
                    st.session_state.show_call_info = not st.session_state.show_call_info
                    st.rerun()

            with col4:
                if st.button("📴 End Call", use_container_width=True, type="primary", key="end_call_btn"):
                    try:
                        api_client.end_call_sync(
                            conference_sid=st.session_state.current_call['conference_sid'],
                        )
                        st.session_state.dialer_state = 'ended'
                        st.rerun()
                    except Exception as e:
                        st.error(f"End call failed: {str(e)}")

            # Display call info if toggled on
            if st.session_state.get('show_call_info', False):
                st.markdown("---")
                with st.expander("📊 Real-time Call Status", expanded=True):
                    try:
                        # Fetch call status
                        status_data = api_client.get_status_sync(
                            conference_sid=st.session_state.current_call['conference_sid']
                        )

                        # Display status overview
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("Status", status_data['status'].upper())
                        with col_b:
                            st.metric("Participants", status_data['participant_count'])
                        with col_c:
                            duration_mins = status_data['duration'] // 60
                            duration_secs = status_data['duration'] % 60
                            st.metric("Conference Duration", f"{duration_mins}m {duration_secs}s")

                        # Display participants
                        if status_data.get('participants'):
                            st.markdown("**Participants:**")
                            for idx, participant in enumerate(status_data['participants'], 1):
                                mute_icon = "🔇" if participant['muted'] else "🔊"
                                hold_icon = "⏸️" if participant['hold'] else ""
                                call_type = "📱 Phone" if participant['call_sid'] else "💻 WebRTC"

                                st.markdown(
                                    f"{idx}. {call_type} - {mute_icon} {hold_icon} "
                                    f"(SID: `{participant['participant_sid'][:8]}...`)"
                                )

                        # Auto-refresh button
                        if st.button("🔄 Refresh Status", key="refresh_status"):
                            st.rerun()

                        st.caption("ℹ️ Status updates every time you click Refresh")

                    except Exception as e:
                        st.error(f"Failed to fetch call status: {str(e)}")
                        st.caption("Try clicking Refresh Status button")

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
