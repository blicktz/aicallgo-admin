# Telnyx Cold Call Dialer - Complete Implementation Plan

**Version**: 1.0
**Date**: 2025-11-14
**Status**: Ready for Implementation

---

## Table of Contents

1. [Research Summary](#research-summary)
2. [Architecture Decision](#architecture-decision)
3. [Implementation Plan](#implementation-plan)
4. [Timeline & Resources](#timeline--resources)
5. [Success Criteria](#success-criteria)
6. [Risk Mitigation](#risk-mitigation)

---

## Research Summary: Telnyx Conference Capabilities ✅

### ✅ Conference Support CONFIRMED

**Telnyx provides TWO approaches for conferencing:**

#### 1. **Call Control API** (Recommended)
- **Conference Creation**: `/v2/conferences` - Create explicit conference rooms
- **Join Conference**: `/v2/conferences/:id/actions/join` - Add call legs to conference
- **List Participants**: `/v2/conferences/:id/participants` - Get all participants with status
- **Participant Controls**:
  - Mute/Unmute: Set `mute: true/false` when joining or update participant
  - Hold/Unhold: Set `hold: true/false`
  - Individual participant control via API
- **Conference Management**: Force end, list all conferences, participant events via webhooks

#### 2. **TeXML (TwiML-compatible)** (Alternative)
- Uses `<Conference>` noun (compatible with Twilio TwiML)
- Can use Twilio Python SDK to generate TeXML
- Similar syntax to Twilio implementation
- Good for migration from Twilio
- Less flexible than Call Control API

### ✅ WebRTC Support CONFIRMED

**Telnyx WebRTC SDK (@telnyx/webrtc):**
- **NPM Package**: `@telnyx/webrtc` (v2.x)
- **Authentication**: SIP Connection credentials (username/password)
- **Connection**: Connects to `rtc.telnyx.com` WebRTC gateway
- **Call Method**: `client.newCall({ destinationNumber: 'conference_id' })`
- **Setup**:
  ```javascript
  const client = new TelnyxRTC({
    login: 'sip_username',
    password: 'sip_password'
  });
  client.connect();
  ```

### Key Differences vs Twilio

| Feature | Twilio | Telnyx |
|---------|--------|--------|
| **Conference Creation** | Implicit (on first join) | Explicit API call required |
| **WebRTC Auth** | JWT token (short-lived) | SIP credentials (persistent) |
| **WebRTC SDK** | @twilio/voice-sdk | @telnyx/webrtc |
| **Participant ID** | call_sid / participant_sid | call_control_id |
| **Conference ID** | friendly_name (string) | conference_id (UUID) |
| **Token Generation** | Per-call (backend generates) | One-time setup in portal |
| **Conference Join** | TwiML App → Conference | Direct call to conference_id |
| **Mute Control** | `participant.update(muted=True)` | `POST /participants/:id/actions/mute` |

### Documentation References

- **Conference API**: https://developers.telnyx.com/api/call-control/create-conference
- **Conference Demo**: https://developers.telnyx.com/docs/voice/programmable-voice/conferencing-demo
- **WebRTC SDK**: https://developers.telnyx.com/docs/voice/webrtc/js-sdk/classes/telnyxrtc
- **Participant Controls**: https://developers.telnyx.com/api/call-control/list-conference-participants
- **GitHub Demo**: https://github.com/team-telnyx/demo-conference-node

---

## Architecture Decision

### Decision 1: Use Call Control API (not TeXML)

**Chosen Approach**: Call Control API

**Rationale:**
1. ✅ Already use Call Control for AI agent calls (existing integration in `app/telephony/telnyx_provider.py`)
2. ✅ More powerful and flexible API
3. ✅ Real-time participant management via webhooks
4. ✅ Better documentation and examples
5. ✅ Consistent with outcall-agent architecture
6. ✅ Modern approach (TeXML is legacy compatibility layer)

**Trade-offs:**
- ❌ Slightly more complex than TeXML
- ✅ But provides better control and scalability
- ✅ More consistent with our existing Telnyx integration

### Decision 2: Separate Page (not unified with Twilio)

**Chosen Approach**: Create separate Streamlit page for Telnyx

**File**: `pages/17_📞_Cold_Call_Dialer_Telnyx.py`

**Rationale:**
1. ✅ Different WebRTC SDKs (can't load both `@twilio/voice-sdk` and `@telnyx/webrtc` simultaneously)
2. ✅ Different authentication flows (SIP credentials vs JWT tokens)
3. ✅ Easier to test and debug independently
4. ✅ Can optimize UX per provider
5. ✅ Simpler initial implementation
6. ✅ Backend is shared (same API endpoints, just different provider parameter)

**Trade-offs:**
- ❌ Two pages to maintain
- ✅ But backend logic is shared via provider abstraction
- ✅ Can unify later if desired (phase 2)
- ✅ Users can choose provider based on their account

---

## Implementation Plan

## Phase 1: Backend Implementation (3-4 days)

### 1.1 Implement TelnyxColdCallHandler

**File**: `services/outcall-agent/app/cold_call/telnyx_handler.py`

**Replace placeholder with full implementation:**

```python
"""Telnyx implementation for cold call handler using Call Control API."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import telnyx
from telnyx.error import TelnyxError

from app.cold_call.base_handler import BaseColdCallHandler
from app.cold_call.models import (
    ConferenceStatus,
    ParticipantInfo,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class TelnyxColdCallHandler(BaseColdCallHandler):
    """Telnyx implementation for cold call dialer using Call Control API."""

    def __init__(
        self,
        api_key: str,
        phone_number: str,
        connection_id: str,
        domain: str,
    ):
        """Initialize Telnyx cold call handler.

        Args:
            api_key: Telnyx API key
            phone_number: Telnyx phone number for outgoing calls
            connection_id: Telnyx connection ID for call control
            domain: Domain for webhooks and callbacks
        """
        self.api_key = api_key
        self.phone_number = phone_number
        self.connection_id = connection_id
        self.domain = domain

        # Set API key for telnyx module
        telnyx.api_key = api_key

    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "telnyx"

    async def create_conference(self, conference_id: str) -> str:
        """Create a Telnyx conference room.

        Unlike Twilio (implicit creation), Telnyx requires explicit conference creation.
        However, we need a call_control_id to create a conference, so we'll use
        the conference_id as a placeholder and create the actual conference when
        the first participant joins.

        Args:
            conference_id: Unique identifier for this conference

        Returns:
            Conference ID (will be created when first participant joins)
        """
        try:
            logger.info(f"Conference ID prepared: {conference_id}")
            # Telnyx conferences are created when first call joins
            # We'll store the conference_id and use it when joining participants
            return conference_id

        except Exception as e:
            logger.error(f"Error preparing conference: {e}")
            raise

    async def add_phone_participant(
        self,
        conference_sid: str,
        to_phone: str,
        from_phone: str,
    ) -> str:
        """Add a phone participant to the conference.

        Step 1: Create outbound call
        Step 2: Join call to conference (creates conference if doesn't exist)

        Args:
            conference_sid: Conference identifier to join
            to_phone: Phone number to call (E.164 format)
            from_phone: Caller ID to display (E.164 format)

        Returns:
            Call control ID for the outbound call
        """
        try:
            # Step 1: Create outbound call
            logger.info(f"Creating outbound call from {from_phone} to {to_phone}")

            call = telnyx.Call.create(
                connection_id=self.connection_id,
                from_=from_phone,
                to=to_phone,
                # Set webhook for call status
                webhook_url=f"https://{self.domain}/aicallgo/api/v1/cold-call/webhook/telnyx/call-status",
                webhook_event_url=f"https://{self.domain}/aicallgo/api/v1/cold-call/webhook/telnyx/call-status",
            )

            call_control_id = call.call_control_id
            logger.info(f"Outbound call created: {call_control_id}")

            # Step 2: Join call to conference (auto-creates conference)
            # Note: This must be done after call is answered, so we'll do it via webhook
            # For now, store the conference_sid in client_state for webhook to use

            logger.info(
                f"Phone participant call initiated",
                extra={
                    "call_control_id": call_control_id,
                    "conference_sid": conference_sid,
                    "to_phone": to_phone,
                },
            )

            return call_control_id

        except TelnyxError as e:
            logger.error(
                f"Telnyx error adding phone participant: {e}",
                extra={"code": e.code if hasattr(e, 'code') else None},
            )
            raise
        except Exception as e:
            logger.error(f"Error adding phone participant: {e}")
            raise

    async def add_webrtc_participant(
        self,
        conference_sid: str,
        client_id: str,
        sdp_offer: Optional[str] = None,
    ) -> dict:
        """Add a WebRTC participant to the conference.

        Unlike Twilio (generates JWT per call), Telnyx uses persistent SIP credentials
        configured in the Telnyx Portal. Browser will connect using these credentials
        and call the conference ID directly.

        Args:
            conference_sid: Conference identifier to join
            client_id: Unique identifier for this WebRTC client
            sdp_offer: Not used for Telnyx (uses SIP connection)

        Returns:
            Dictionary with WebRTC connection details
        """
        try:
            logger.info(
                f"Generating WebRTC credentials for client",
                extra={
                    "conference_sid": conference_sid,
                    "client_id": client_id,
                },
            )

            # Return SIP credentials from settings
            # These are configured once in Telnyx Portal and reused
            return {
                "participant_sid": client_id,
                "sip_username": settings.telnyx_sip_username,
                "sip_password": settings.telnyx_sip_password,
                "conference_id": conference_sid,
                "status": "credentials_ready",
                "ice_servers": [
                    {"urls": ["stun:stun.telnyx.com:3478"]},
                    {"urls": ["turn:turn.telnyx.com:3478"], "username": "telnyx", "credential": "telnyx"},
                ],
            }

        except Exception as e:
            logger.error(f"Error generating WebRTC credentials: {e}")
            raise

    async def control_participant(
        self,
        conference_sid: str,
        participant_sid: str,
        action: str,
        value: Optional[bool] = None,
    ) -> dict:
        """Control a conference participant (mute/unmute).

        Args:
            conference_sid: Conference ID
            participant_sid: Call control ID of participant
            action: Control action ("mute" or "unmute")
            value: Optional explicit value (defaults based on action)

        Returns:
            Dictionary with control result
        """
        try:
            # Determine mute action
            if value is not None:
                muted = value
            else:
                muted = action == "mute"

            logger.info(
                f"{'Muting' if muted else 'Unmuting'} participant",
                extra={
                    "conference_sid": conference_sid,
                    "participant_sid": participant_sid,
                },
            )

            # Use Telnyx Conference Participant API
            if muted:
                # POST /v2/conferences/:conference_id/actions/mute
                url = f"https://api.telnyx.com/v2/conferences/{conference_sid}/actions/mute"
                payload = {"call_control_ids": [participant_sid]}
            else:
                # POST /v2/conferences/:conference_id/actions/unmute
                url = f"https://api.telnyx.com/v2/conferences/{conference_sid}/actions/unmute"
                payload = {"call_control_ids": [participant_sid]}

            # Make API request
            import requests
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()

            logger.info(
                f"Participant {'muted' if muted else 'unmuted'} successfully",
                extra={
                    "conference_sid": conference_sid,
                    "participant_sid": participant_sid,
                },
            )

            return {
                "success": True,
                "muted": muted,
                "message": f"Participant {'muted' if muted else 'unmuted'} successfully",
            }

        except Exception as e:
            logger.error(f"Error controlling participant: {e}")
            raise

    async def end_conference(self, conference_sid: str) -> dict:
        """End a conference and hang up all participants.

        Args:
            conference_sid: Conference ID to terminate

        Returns:
            Dictionary with termination result
        """
        try:
            logger.info(f"Ending conference: {conference_sid}")

            # POST /v2/conferences/:conference_id/actions/end
            import requests
            response = requests.post(
                f"https://api.telnyx.com/v2/conferences/{conference_sid}/actions/end",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 404:
                # Conference already ended or doesn't exist
                logger.warning(f"Conference not found or already ended: {conference_sid}")
                return {
                    "success": True,
                    "status": ConferenceStatus.COMPLETED.value,
                    "message": "Conference not found or already completed",
                }

            response.raise_for_status()

            logger.info(f"Conference ended successfully: {conference_sid}")

            return {
                "success": True,
                "status": ConferenceStatus.COMPLETED.value,
                "message": "Conference ended successfully",
            }

        except Exception as e:
            logger.error(f"Error ending conference: {e}")
            raise

    async def get_conference_status(
        self,
        conference_sid: str,
        conference_id: str,
    ) -> dict:
        """Get current status of a conference.

        Args:
            conference_sid: Conference ID
            conference_id: Application conference ID

        Returns:
            Dictionary with conference status details
        """
        try:
            logger.info(f"Fetching conference status: {conference_sid}")

            # GET /v2/conferences/:conference_id
            import requests
            response = requests.get(
                f"https://api.telnyx.com/v2/conferences/{conference_sid}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 404:
                # Conference doesn't exist yet
                logger.info(f"Conference not created yet: {conference_sid}")
                return {
                    "conference_sid": conference_sid,
                    "conference_id": conference_id,
                    "status": ConferenceStatus.INIT.value,
                    "participant_count": 0,
                    "duration": 0,
                    "created_at": datetime.now(timezone.utc),
                    "started_at": None,
                    "ended_at": None,
                    "participants": [],
                }

            response.raise_for_status()
            conference_data = response.json()["data"]

            # Get participants
            participants_response = requests.get(
                f"https://api.telnyx.com/v2/conferences/{conference_sid}/participants",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            participants_data = []
            if participants_response.status_code == 200:
                participants_list = participants_response.json()["data"]
                for p in participants_list:
                    participants_data.append({
                        "participant_sid": p.get("call_control_id"),
                        "call_sid": p.get("call_leg_id"),
                        "muted": p.get("muted", False),
                        "hold": p.get("on_hold", False),
                        "start_time": datetime.fromisoformat(p["created_at"]) if "created_at" in p else datetime.now(timezone.utc),
                    })

            # Map Telnyx status to our enum
            status_map = {
                "init": ConferenceStatus.INIT.value,
                "in_progress": ConferenceStatus.IN_PROGRESS.value,
                "completed": ConferenceStatus.COMPLETED.value,
            }
            status = status_map.get(conference_data.get("status", "init"), ConferenceStatus.INIT.value)

            # Calculate duration
            duration = 0
            created_at = datetime.fromisoformat(conference_data["created_at"]) if "created_at" in conference_data else datetime.now(timezone.utc)
            if status == ConferenceStatus.IN_PROGRESS.value:
                duration = int((datetime.now(timezone.utc) - created_at).total_seconds())

            return {
                "conference_sid": conference_sid,
                "conference_id": conference_id,
                "status": status,
                "participant_count": len(participants_data),
                "duration": duration,
                "created_at": created_at,
                "started_at": created_at if status != ConferenceStatus.INIT.value else None,
                "ended_at": None,
                "participants": participants_data,
            }

        except Exception as e:
            logger.error(f"Error fetching conference status: {e}")
            raise
```

### 1.2 Add Telnyx Webhooks

**File**: `services/outcall-agent/app/cold_call/endpoints.py`

**Add new endpoints:**

```python
@router.post(
    "/webhook/telnyx/conference-status",
    status_code=status.HTTP_200_OK,
    summary="Telnyx conference webhook",
    description="Webhook endpoint for Telnyx conference status events",
)
async def telnyx_conference_webhook(request: Request):
    """Handle Telnyx conference event webhooks.

    Events:
    - conference.participant.joined
    - conference.participant.left
    - conference.started
    - conference.ended
    """
    try:
        payload = await request.json()

        event_type = payload.get("data", {}).get("event_type")
        conference_id = payload.get("data", {}).get("payload", {}).get("conference_id")
        call_control_id = payload.get("data", {}).get("payload", {}).get("call_control_id")

        logger.info(
            f"Telnyx conference webhook received",
            extra={
                "event": event_type,
                "conference_id": conference_id,
                "call_control_id": call_control_id,
                "payload": payload,
            },
        )

        # Determine status based on event
        conference_status = None
        participant_count = None

        if event_type == "conference.started":
            conference_status = "in-progress"
        elif event_type == "conference.ended":
            conference_status = "completed"
            participant_count = 0
        elif event_type == "conference.participant.joined":
            conference_status = "in-progress"
        elif event_type == "conference.participant.left":
            conference_status = "in-progress"

        # Store status in Redis
        await store_call_status_in_redis(
            conference_sid=conference_id,
            friendly_name=conference_id,
            status=conference_status,
            event_type=event_type,
            participant_count=participant_count,
            call_sid=call_control_id,
        )

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error processing Telnyx conference webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@router.post(
    "/webhook/telnyx/call-status",
    status_code=status.HTTP_200_OK,
    summary="Telnyx call status webhook",
    description="Webhook endpoint for Telnyx call status events",
)
async def telnyx_call_webhook(request: Request):
    """Handle Telnyx call status webhooks.

    Events:
    - call.initiated
    - call.answered
    - call.hangup
    - call.machine.detection.ended
    """
    try:
        payload = await request.json()

        event_type = payload.get("data", {}).get("event_type")
        call_control_id = payload.get("data", {}).get("payload", {}).get("call_control_id")
        call_status = payload.get("data", {}).get("payload", {}).get("state")

        logger.info(
            f"Telnyx call webhook received",
            extra={
                "event": event_type,
                "call_control_id": call_control_id,
                "status": call_status,
                "payload": payload,
            },
        )

        # If call is answered, join to conference
        if event_type == "call.answered":
            # Get conference_id from client_state if available
            # For now, log that call was answered
            logger.info(f"Call answered, ready to join conference: {call_control_id}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error processing Telnyx call webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
```

### 1.3 Configuration Updates

**File**: `services/outcall-agent/app/core/config.py`

**Add settings:**

```python
# Telnyx WebRTC credentials for cold calling
telnyx_sip_username: Optional[str] = Field(None, env="TELNYX_SIP_USERNAME")
telnyx_sip_password: Optional[str] = Field(None, env="TELNYX_SIP_PASSWORD")
```

**File**: `services/outcall-agent/.env`

**Add variables:**

```bash
# Telnyx WebRTC (for cold calling)
TELNYX_SIP_USERNAME=your_sip_username
TELNYX_SIP_PASSWORD=your_sip_password
```

### 1.4 Handler Factory Update

**File**: `services/outcall-agent/app/cold_call/handler_factory.py`

**Update Telnyx section:**

```python
# Create Telnyx handler
elif provider_enum == ColdCallProvider.TELNYX:
    if not settings.telnyx_api_key:
        raise ValueError(
            "Telnyx provider selected but API key not configured. "
            "Set TELNYX_API_KEY environment variable."
        )

    if not settings.telnyx_phone_number:
        raise ValueError(
            "Telnyx provider selected but phone number not configured. "
            "Set TELNYX_PHONE_NUMBER environment variable."
        )

    if not settings.telnyx_sip_username or not settings.telnyx_sip_password:
        raise ValueError(
            "Telnyx WebRTC credentials not configured. "
            "Set TELNYX_SIP_USERNAME and TELNYX_SIP_PASSWORD for browser calling."
        )

    logger.info("Creating Telnyx cold call handler")
    return TelnyxColdCallHandler(
        api_key=settings.telnyx_api_key,
        phone_number=settings.telnyx_phone_number,
        connection_id=settings.telnyx_connection_id,
        domain=settings.domain,
    )
```

### 1.5 Testing

**Create tests:**

**File**: `services/outcall-agent/tests/unit/cold_call/test_telnyx_handler.py`

```python
"""Tests for Telnyx cold call handler."""

import pytest
from unittest.mock import Mock, patch

from app.cold_call.telnyx_handler import TelnyxColdCallHandler


@pytest.fixture
def telnyx_handler():
    """Create Telnyx handler for testing."""
    return TelnyxColdCallHandler(
        api_key="test_api_key",
        phone_number="+15551234567",
        connection_id="test_connection_id",
        domain="test.example.com",
    )


@pytest.mark.asyncio
async def test_create_conference(telnyx_handler):
    """Test conference creation."""
    conference_id = "COLD_CALL_test123"
    result = await telnyx_handler.create_conference(conference_id)
    assert result == conference_id


@pytest.mark.asyncio
@patch("telnyx.Call.create")
async def test_add_phone_participant(mock_call_create, telnyx_handler):
    """Test adding phone participant."""
    mock_call = Mock()
    mock_call.call_control_id = "test_call_control_id"
    mock_call_create.return_value = mock_call

    result = await telnyx_handler.add_phone_participant(
        conference_sid="test_conference",
        to_phone="+15559999999",
        from_phone="+15551234567",
    )

    assert result == "test_call_control_id"
    mock_call_create.assert_called_once()


@pytest.mark.asyncio
async def test_add_webrtc_participant(telnyx_handler):
    """Test WebRTC participant credentials."""
    result = await telnyx_handler.add_webrtc_participant(
        conference_sid="test_conference",
        client_id="test_client",
    )

    assert "sip_username" in result
    assert "sip_password" in result
    assert "conference_id" in result
    assert result["status"] == "credentials_ready"
```

---

## Phase 2: Frontend Implementation (2-3 hours)

### Design Decision: Provider as Environment Configuration

**Final Approach**: Configure provider in `.env` file as deployment-time setting, rather than creating a separate page or runtime selector.

**Rationale:**
1. **Eliminates SDK conflicts**: Only one WebRTC SDK (Twilio or Telnyx) loads per service instance
2. **Matches infrastructure pattern**: Provider choice tied to API credentials (similar to main service telephony configuration)
3. **Zero code duplication**: All contact management logic (CSV upload, Odoo integration, pagination) remains shared in single page
4. **Production-ready**: Treats provider as infrastructure config, switched via service restart
5. **Simplest implementation**: Minimal code changes (~135 lines) vs creating separate page (~1120 lines duplicated)

**Trade-off**: Switching providers requires service restart, but this is acceptable since:
- Provider choice aligns with which service account/credentials you have
- Switching is an operations/config change, not a per-user preference
- Clear deployment configuration prevents runtime conflicts

### 2.1 Environment Configuration

**File**: `services/admin-board/.env`

```bash
# Cold Call Dialer Configuration
OUTCALL_AGENT_INTERNAL_URL=http://outcall_agent_backend:8000
ENABLE_COLD_CALL_DIALER=true

# Cold Call Provider Selection (twilio or telnyx)
# Changing this requires service restart
COLD_CALL_PROVIDER=telnyx
```

**File**: `services/admin-board/.env.example`

```bash
# Cold Call Provider: 'twilio' or 'telnyx'
# This determines which WebRTC SDK is loaded
# Requires service restart to change
COLD_CALL_PROVIDER=twilio
```

### 2.2 Settings Configuration

**File**: `services/admin-board/config/settings.py`

```python
# Add to Settings class:
cold_call_provider: str = Field(
    default="twilio",
    env="COLD_CALL_PROVIDER",
    description="Cold call telephony provider (twilio or telnyx)"
)

@field_validator("cold_call_provider")
@classmethod
def validate_provider(cls, v: str) -> str:
    """Validate cold call provider."""
    allowed = ["twilio", "telnyx"]
    v = v.lower()
    if v not in allowed:
        raise ValueError(f"COLD_CALL_PROVIDER must be one of {allowed}")
    return v
```

### 2.3 Update Existing Cold Call Dialer Page

**File**: `services/admin-board/pages/16_📞_Cold_Call_Dialer.py`

**Changes needed:**

#### Change 1: Read provider from settings (top of file)
```python
from config.settings import settings

# Get provider from environment (deployment config)
PROVIDER = settings.cold_call_provider  # 'twilio' or 'telnyx'
```

#### Change 2: Show provider in UI (after header)
```python
st.title("📞 Cold Call Dialer")
st.caption(f"Using {PROVIDER.title()} • Configured in deployment")
st.markdown("### Upload contacts and make calls directly from your browser")
st.markdown("---")
```

#### Change 3: Rename existing Twilio WebRTC function
```python
def render_twilio_webrtc_component(access_token: str, conference_name: str, client_id: str):
    """Render Twilio WebRTC component for browser audio."""
    # Existing code unchanged (lines 119-198)
```

#### Change 4: Add Telnyx WebRTC component
```python
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
        <script src="https://cdn.jsdelivr.net/npm/@telnyx/webrtc@2.x/dist/telnyx.min.js"></script>
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
```

#### Change 5: Update show_dialer() modal
```python
@st.dialog("📞 Call in Progress", width="large")
def show_dialer():
    """Display the dialer modal during an active call."""
    # ... existing code ...

    # When initiating call, use deployment-configured provider:
    if st.session_state.dialer_state == 'dialing':
        with st.spinner("Creating conference and dialing..."):
            try:
                response = api_client.initiate_call_sync(
                    to_phone=call['formatted_phone'],
                    provider=PROVIDER,  # Use deployment-configured provider
                )
                # ... rest unchanged ...

    # When joining WebRTC, store provider-specific credentials:
    if st.session_state.dialer_state == 'connecting':
        with st.spinner("Connecting your browser to the call..."):
            try:
                webrtc_response = api_client.join_webrtc_sync(
                    conference_id=st.session_state.current_call['conference_sid'],
                    client_id=client_id,
                )

                # Store provider-specific credentials
                if PROVIDER == 'twilio':
                    st.session_state.current_call['access_token'] = webrtc_response['access_token']
                elif PROVIDER == 'telnyx':
                    st.session_state.current_call['sip_username'] = webrtc_response['sip_username']
                    st.session_state.current_call['sip_password'] = webrtc_response['sip_password']

                st.session_state.current_call['participant_sid'] = webrtc_response['participant_sid']
                # ... rest unchanged ...

    # Render provider-specific WebRTC component:
    if st.session_state.dialer_state == 'connected':
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

        # ... rest of call controls unchanged ...
```

### 2.4 Shared Components

**No changes needed for:**
- ✅ `components/cold_call/csv_parser.py` - Works for both providers
- ✅ `components/cold_call/phone_validator.py` - Works for both providers
- ✅ `components/cold_call/odoo_integration.py` - Works for both providers
- ✅ `components/cold_call/api_client.py` - Already supports `provider` parameter
- ✅ `services/redis_service.py` - Works for both providers

### 2.5 Deployment Configuration

**To deploy with Telnyx:**
```bash
# Set in .env
COLD_CALL_PROVIDER=telnyx

# Restart service
docker-compose restart admin-board
# OR in Kubernetes:
kubectl rollout restart deployment/admin-board -n aicallgo-staging
```

**To switch providers:**
```bash
# Update .env
COLD_CALL_PROVIDER=twilio  # or telnyx

# Restart required
kubectl rollout restart deployment/admin-board -n aicallgo-staging
```

---

## Phase 3: Configuration & Setup (0.5 day)

### 3.1 Telnyx Portal Setup

**Manual one-time setup in Telnyx Portal:**

#### Step 1: Create SIP Connection

1. Login to Telnyx Portal (https://portal.telnyx.com)
2. Navigate to **Voice** → **SIP Connections**
3. Click **Create SIP Connection**
4. Select **Credentials** authentication type
5. Give it a name: "Cold Call Dialer WebRTC"
6. Click **Save**

#### Step 2: Configure SIP Credentials

1. In the SIP Connection settings, go to **Authentication**
2. Note the auto-generated **Username** (e.g., `sip_user_abc123`)
3. Click **Generate New Password** and copy it
4. **Important**: Store these credentials securely
5. Save settings

#### Step 3: Enable WebRTC

1. In SIP Connection settings, go to **WebRTC**
2. Toggle **Enable WebRTC** to ON
3. Add your domain to **Allowed Origins**:
   - For staging: `https://staging.aicallgo.com`
   - For production: `https://app.aicallgo.com`
4. Save settings

#### Step 4: Assign Phone Number

1. Navigate to **Phone Numbers** → **Manage Phone Numbers**
2. Select your phone number
3. Under **Connection**, select the SIP Connection created above
4. Save

#### Step 5: Configure Webhooks

1. In SIP Connection settings, go to **Webhooks**
2. Set **Webhook URL** to: `https://your-domain/aicallgo/api/v1/cold-call/webhook/telnyx/call-status`
3. Enable these events:
   - `call.initiated`
   - `call.answered`
   - `call.hangup`
   - `conference.started`
   - `conference.ended`
   - `conference.participant.joined`
   - `conference.participant.left`
4. Save

#### Step 6: Enable Recording (Optional)

1. In SIP Connection settings, go to **Recording**
2. Toggle **Enable Recording** to ON
3. Set **Recording Channels** to **Dual** (separate channels for each side)
4. Set **Recording Webhook** to: `https://your-domain/aicallgo/api/v1/cold-call/webhook/telnyx/recording-status`
5. Save

### 3.2 Environment Variables

**File**: `services/outcall-agent/.env`

```bash
# Existing Telnyx config (for AI agent)
TELNYX_API_KEY=KEY...
TELNYX_PHONE_NUMBER=+15551234567
TELNYX_CONNECTION_ID=1234567890

# NEW - Telnyx WebRTC credentials (from Portal)
TELNYX_SIP_USERNAME=sip_user_abc123
TELNYX_SIP_PASSWORD=your_secure_password_here
```

**File**: `services/admin-board/.env`

No changes needed - uses outcall-agent API.

### 3.3 Kubernetes Secrets

**File**: `terraform/modules/k8s_config/secrets.tf`

**Add if not present:**

```hcl
telnyx_sip_username = var.telnyx_sip_username
telnyx_sip_password = var.telnyx_sip_password
```

**File**: `terraform/staging.tfvars`

```hcl
telnyx_sip_username = "sip_user_abc123"
telnyx_sip_password = "your_secure_password"  # Or use TF_VAR_
```

### 3.4 Requirements

**File**: `services/outcall-agent/requirements.txt`

Already has:
```
telnyx>=2.0.0
```

**File**: `services/admin-board/requirements.txt`

No changes needed - Telnyx WebRTC SDK loaded via CDN.

---

## Phase 4: Testing & Validation (2 days)

### 4.1 Unit Tests

Run existing test suite:
```bash
cd services/outcall-agent
pytest tests/unit/cold_call/
```

### 4.2 Integration Tests

**Test Scenarios:**

1. **Conference Creation**
   ```bash
   # Test via API
   curl -X POST https://staging-outcall.aicallgo.com/aicallgo/api/v1/cold-call/initiate \
     -H "X-API-Key: your_api_key" \
     -H "Content-Type: application/json" \
     -d '{
       "to_phone": "+15559999999",
       "from_phone": "+15551234567",
       "provider": "telnyx"
     }'
   ```

2. **WebRTC Join**
   ```bash
   curl -X POST https://staging-outcall.aicallgo.com/aicallgo/api/v1/cold-call/webrtc-join \
     -H "X-API-Key: your_api_key" \
     -H "Content-Type: application/json" \
     -d '{
       "conference_id": "COLD_CALL_abc123",
       "client_id": "browser_client_1"
     }'
   ```

3. **Participant Control**
   ```bash
   curl -X POST https://staging-outcall.aicallgo.com/aicallgo/api/v1/cold-call/control/mute \
     -H "X-API-Key: your_api_key" \
     -H "Content-Type: application/json" \
     -d '{
       "conference_sid": "conference_id",
       "participant_sid": "call_control_id",
       "action": "mute"
     }'
   ```

### 4.3 End-to-End Testing

**Full workflow test:**

1. **Setup**
   - Access Telnyx page: https://staging.aicallgo.com/17_📞_Cold_Call_Dialer_Telnyx
   - Upload test CSV or load Odoo contacts

2. **Initiate Call**
   - Click "Dial" on a contact
   - Verify:
     - Modal opens showing "Dialing..."
     - PSTN call initiated (check Telnyx Portal → Call Logs)
     - Status updates in real-time

3. **WebRTC Connection**
   - Verify:
     - Browser requests microphone permission
     - Telnyx WebRTC connects (check console logs)
     - Audio indicator shows "🎧 Telnyx audio active"

4. **Call Connected**
   - Answer the PSTN call on your phone
   - Verify:
     - Status changes to "Connected"
     - Timer starts counting
     - Can hear audio both ways
     - Audio quality is clear

5. **Call Controls**
   - Click "Mute" button
   - Verify:
     - Microphone muted (phone side can't hear you)
     - Button shows "Unmute"
   - Click "Unmute"
   - Verify audio restored

6. **End Call**
   - Click "End Call"
   - Verify:
     - Both sides disconnect
     - Post-call logging modal appears
     - Can select outcome and add notes
     - Call log saved

7. **Recording**
   - Check recording retrieval
   - Verify recording posted to backend
   - Download and verify audio quality

### 4.4 Browser Compatibility

Test on:
- ✅ Chrome (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Edge (latest)

### 4.5 Comparison Testing

**Run parallel tests:**

| Test | Twilio (Page 16) | Telnyx (Page 17) | Notes |
|------|------------------|------------------|-------|
| Call initiation time | ___ sec | ___ sec | Should be similar |
| Audio quality | ___ | ___ | Subjective rating 1-5 |
| Latency | ___ ms | ___ ms | Measure RTT |
| Mute/unmute lag | ___ ms | ___ ms | Control responsiveness |
| Recording quality | ___ | ___ | Listen to both |
| Cost per minute | $___ | $___ | Check billing |

---

## Timeline & Resources

### Timeline

| Phase | Description | Duration | Start | End |
|-------|-------------|----------|-------|-----|
| **Phase 1** | Backend implementation | 3-4 days | Day 1 | Day 4 |
| **Phase 2** | Frontend implementation (env-based) | 2-3 hours | Day 5 | Day 5 |
| **Phase 3** | Configuration & setup | 0.5 day | Day 6 | Day 6 |
| **Phase 4** | Testing & validation | 2 days | Day 7 | Day 8 |
| **Total** | End-to-end | **5.5-7 days** | - | - |

### Resource Requirements

**Development:**
- 1 Backend developer (Python, FastAPI, Telnyx API)
- 1 Frontend developer (Streamlit, JavaScript, WebRTC)
- Can be same developer with full-stack skills

**Infrastructure:**
- Existing outcall-agent deployment (no new resources)
- Existing admin-board deployment (no new resources)
- Telnyx account with conference capability
- Test phone numbers for validation

**External Services:**
- Telnyx API access (existing)
- Telnyx SIP Connection (new - configure in portal)
- Staging environment for testing

---

## Success Criteria

### Backend (Phase 1)
- ✅ `TelnyxColdCallHandler` fully implemented
- ✅ All methods working (conference creation, participant management, status)
- ✅ Telnyx webhooks receiving and processing events
- ✅ WebRTC credentials generation working
- ✅ Mute/unmute controls functional
- ✅ Conference termination working
- ✅ Unit tests passing (>80% coverage)
- ✅ Integration tests with Telnyx sandbox passing

### Frontend (Phase 2)
- ✅ Provider configured via `COLD_CALL_PROVIDER` env variable
- ✅ Single page supports both Twilio and Telnyx (conditional rendering)
- ✅ Provider selection locked at service startup
- ✅ CSV upload and Odoo integration working for both providers
- ✅ Correct WebRTC SDK loads based on configuration
- ✅ Browser microphone permission handled
- ✅ Conference calling works end-to-end for both providers
- ✅ Bidirectional audio confirmed
- ✅ Mute/unmute controls functional
- ✅ Call status updates in real-time
- ✅ Post-call logging saves correctly
- ✅ Recording retrieval working
- ✅ Zero code duplication (all data logic shared)

### Overall
- ✅ Feature parity with Twilio version
- ✅ Same UX flow (provider-agnostic)
- ✅ No code duplication (single page for both providers)
- ✅ Provider switchable via deployment config
- ✅ Documentation complete
- ✅ Staging deployment successful
- ✅ Production-ready code quality
- ✅ All tests passing
- ✅ Stakeholder approval

---

## Risk Mitigation

### Risk 1: WebRTC SDK Compatibility Issues

**Risk**: Telnyx WebRTC SDK may not work on all browsers

**Impact**: High - Users can't make calls

**Probability**: Medium

**Mitigation:**
- Test on Chrome, Firefox, Safari, Edge early
- Provide browser compatibility warning on page
- Have fallback instructions for unsupported browsers
- Monitor console errors and provide helpful messages

**Contingency:**
- Document supported browsers clearly
- Provide alternative calling methods (phone bridge)

### Risk 2: SIP Credential Security

**Risk**: SIP credentials exposed in frontend code

**Impact**: High - Unauthorized usage, security breach

**Probability**: Low (if implemented correctly)

**Mitigation:**
- Never hardcode credentials in frontend
- Pass credentials server-side only
- Use environment variables in backend
- Store in Kubernetes secrets encrypted
- Rotate credentials regularly
- Consider using Telnyx JWT for production

**Contingency:**
- Have credential rotation procedure ready
- Monitor usage for anomalies
- Set up billing alerts

### Risk 3: Conference API Limitations

**Risk**: Telnyx conference limits lower than expected

**Impact**: Medium - Can't handle large conferences

**Probability**: Low

**Mitigation:**
- Check Telnyx account limits early
- Document max participants (usually 40+)
- Add participant limit validation in code
- Provide clear error messages to users

**Contingency:**
- Upgrade Telnyx account tier if needed
- Implement queueing for large lists

### Risk 4: Audio Quality Issues

**Risk**: Poor audio quality or latency

**Impact**: High - Bad user experience

**Probability**: Low

**Mitigation:**
- Test with multiple network conditions
- Use Telnyx recommended codecs (PCMU, Opus)
- Configure STUN/TURN servers properly
- Test from different geographic locations

**Contingency:**
- Provide audio troubleshooting guide
- Have network requirements documented
- Support ticket escalation to Telnyx

### Risk 5: Webhook Reliability

**Risk**: Webhooks not received or delayed

**Impact**: Medium - Status updates missing

**Probability**: Low

**Mitigation:**
- Implement webhook retry logic
- Log all webhook events
- Use Redis for status caching
- Set up webhook monitoring/alerts

**Contingency:**
- Polling fallback for status updates
- Manual refresh button for users

### Risk 6: Migration Complexity

**Risk**: Users confused by two separate pages

**Impact**: Low - User confusion

**Probability**: Medium

**Mitigation:**
- Clear naming: "Cold Call Dialer (Twilio)" vs "(Telnyx)"
- Documentation explaining differences
- Provider selection guide
- Link between pages

**Contingency:**
- Unify pages in Phase 2 if needed
- Add provider switcher on single page

---

## Post-Implementation

### Phase 5: Optional Enhancements

**After successful deployment, consider:**

1. **Unified Interface** (2-3 days)
   - Single page with provider toggle
   - Dynamic WebRTC SDK loading
   - Provider auto-selection based on account

2. **Advanced Features** (3-5 days)
   - Call recording auto-transcription
   - Call analytics dashboard
   - Voicemail detection and skip
   - Call queue management

3. **Performance Optimization** (1-2 days)
   - WebRTC connection pooling
   - Faster call initiation
   - Reduced latency tuning

4. **Cost Optimization** (1 day)
   - Provider cost comparison
   - Auto-select cheapest provider per call
   - Usage analytics and reporting

---

## Documentation

### User Documentation

**Create guides:**

1. **Getting Started with Telnyx Dialer**
   - Account setup
   - Accessing the page
   - Making your first call

2. **Telnyx vs Twilio Comparison**
   - Features comparison
   - Cost comparison
   - When to use which

3. **Troubleshooting Guide**
   - Common issues and fixes
   - Browser compatibility
   - Audio problems
   - Webhook issues

### Developer Documentation

**Update docs:**

1. **Architecture diagram** (include Telnyx flow)
2. **API specification** (add Telnyx examples)
3. **Deployment guide** (Telnyx setup steps)
4. **Testing guide** (Telnyx test scenarios)

---

## Appendix: Code Examples

### Example: Making a Call from Frontend

```python
# In pages/17_📞_Cold_Call_Dialer_Telnyx.py

# Initiate call with Telnyx
response = api_client.initiate_call(
    to_phone=contact["phone"],
    from_phone=from_phone_number,
    provider="telnyx"  # Important!
)

conference_id = response["conference_id"]
conference_sid = response["conference_sid"]

# Get WebRTC credentials
webrtc_response = api_client.webrtc_join(
    conference_id=conference_id,
    client_id=f"admin_{st.session_state.user_id}",
)

# For Telnyx, response contains SIP credentials
sip_username = webrtc_response["sip_username"]
sip_password = webrtc_response["sip_password"]

# Render WebRTC component
render_telnyx_webrtc_component(
    sip_username=sip_username,
    sip_password=sip_password,
    conference_id=conference_id,
    client_id=f"admin_{st.session_state.user_id}",
)
```

### Example: Conference Join (Backend)

```python
# In telnyx_handler.py

async def add_phone_participant(self, conference_sid: str, to_phone: str, from_phone: str) -> str:
    # Step 1: Create outbound call
    call = telnyx.Call.create(
        connection_id=self.connection_id,
        from_=from_phone,
        to=to_phone,
        webhook_url=f"https://{self.domain}/aicallgo/api/v1/cold-call/webhook/telnyx/call-status",
    )

    call_control_id = call.call_control_id

    # Step 2: Join to conference (via webhook after call answers)
    # Store conference_sid in Redis for webhook to use
    await redis_client.set(f"telnyx_call:{call_control_id}", conference_sid, ex=3600)

    return call_control_id
```

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-14 | Initial implementation plan created |

---

## References

- **Telnyx Conference API**: https://developers.telnyx.com/api/call-control/create-conference
- **Telnyx WebRTC SDK**: https://developers.telnyx.com/docs/voice/webrtc/js-sdk/classes/telnyxrtc
- **Conference Demo**: https://developers.telnyx.com/docs/voice/programmable-voice/conferencing-demo
- **Call Control API**: https://developers.telnyx.com/docs/api/v2/call-control
- **GitHub Examples**: https://github.com/team-telnyx/demo-conference-node
- **Original Twilio Plan**: ./IMPLEMENTATION_PLAN.md
- **Architecture Doc**: ./ARCHITECTURE.md
- **API Spec**: ./API_SPECIFICATION.md
