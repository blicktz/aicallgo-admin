# Cold Call Dialer - Architecture Design

**Version**: 1.0
**Date**: 2025-11-12
**Status**: Design Specification

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Call Flow Sequences](#call-flow-sequences)
4. [Provider Abstraction](#provider-abstraction)
5. [WebRTC Integration](#webrtc-integration)
6. [Data Models](#data-models)
7. [Security Considerations](#security-considerations)
8. [Scalability & Performance](#scalability--performance)

---

## System Overview

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Admin Board (Streamlit)                        │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  Hidden Page: /dial                                             │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │    │
│  │  │  CSV Upload  │  │ Contact List │  │ Dialer Modal │         │    │
│  │  │  Component   │  │   Display    │  │  (WebRTC)    │         │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘         │    │
│  │                           │                    │                 │    │
│  │                           └────────────────────┘                 │    │
│  │                                    │                             │    │
│  │                           ┌────────▼────────┐                   │    │
│  │                           │   API Client    │                   │    │
│  │                           │  (HTTP/WebRTC)  │                   │    │
│  └───────────────────────────┴─────────────────┴───────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ Internal VPC
                                   │ INTERNAL_API_KEY
                                   │
┌──────────────────────────────────▼──────────────────────────────────────┐
│                        Outcall Agent (FastAPI)                           │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  Cold Call Module                                               │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │    │
│  │  │   Endpoints  │  │    Factory   │  │   Handlers   │         │    │
│  │  │  (FastAPI)   │─►│   Pattern    │─►│ Twilio/Telnyx│         │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘         │    │
│  │         │                                      │                 │    │
│  └─────────┼──────────────────────────────────────┼─────────────────┘    │
│            │                                      │                      │
│            │          Uses Existing               │                      │
│            │          ┌──────────────────┐        │                      │
│            └─────────►│ Twilio Provider  │◄───────┘                      │
│                       │ Telnyx Provider  │                               │
│                       └──────────────────┘                               │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ Twilio REST API
                               │ Telnyx API
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                          Twilio/Telnyx Cloud                             │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  Conference Room                                                │    │
│  │  ┌──────────────────┐              ┌──────────────────┐        │    │
│  │  │  Participant A   │◄────────────►│  Participant B   │        │    │
│  │  │  (Browser/WebRTC)│  Audio Mix   │  (PSTN Phone)    │        │    │
│  │  └──────────────────┘              └──────────────────┘        │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Separation of Concerns**
   - Admin-board: UI and user interaction
   - Outcall-agent: Business logic and telephony integration
   - Twilio/Telnyx: Telephony infrastructure

2. **Provider Abstraction**
   - Common interface for all telephony providers
   - Easy to add new providers
   - Configuration-based provider selection

3. **Minimal Infrastructure Changes**
   - Reuse existing deployments
   - No new Kubernetes resources
   - Backward compatible

4. **Security by Default**
   - Internal VPC communication only
   - API key authentication
   - No public endpoints for cold calling

---

## Component Architecture

### Admin-Board Components

#### 1. Hidden Page (`pages/16_📞_Cold_Call_Dialer.py`)

**Purpose**: Main UI entry point for cold calling

**Responsibilities**:
- Authentication check
- CSV upload interface
- Contact list management
- Dialer modal orchestration
- Post-call logging

**Technology Stack**:
- Streamlit 1.32+
- Python 3.12+
- Session state management

**Key Features**:
- Not included in navigation (hidden page)
- Accessible via direct URL only
- Full authentication integration
- Responsive UI design

#### 2. CSV Parser (`components/cold_call/csv_parser.py`)

**Purpose**: Parse and validate contact CSV files

**Interface**:
```python
class CSVParser:
    REQUIRED_COLUMNS = ['name', 'company', 'phone']
    OPTIONAL_COLUMNS = ['title']

    def validate_csv(self, file: UploadedFile) -> ValidationResult
    def parse_contacts(self, file: UploadedFile) -> List[Contact]
    def format_contact_row(self, row: dict) -> Contact
```

**Validation Rules**:
- Required columns must be present
- Phone numbers must be parseable
- Name and company cannot be empty
- Title is optional

**Error Handling**:
- Clear error messages for validation failures
- Row-level error reporting
- Partial success handling (skip invalid rows)

#### 3. Phone Validator (`components/cold_call/phone_validator.py`)

**Purpose**: Validate and format phone numbers

**Interface**:
```python
class PhoneValidator:
    def validate_e164(self, phone: str) -> bool
    def format_e164(self, phone: str, country_code: str = 'US') -> str
    def parse_phone(self, phone: str) -> PhoneNumber
    def is_valid_for_calling(self, phone: str) -> bool
```

**Library**: `phonenumbers` (Google's libphonenumber)

**Features**:
- E.164 format validation
- Auto-formatting with country code
- International number support
- Invalid number detection

#### 4. API Client (`components/cold_call/api_client.py`)

**Purpose**: Communicate with outcall-agent

**Interface**:
```python
class ColdCallAPIClient:
    def __init__(self, base_url: str, api_key: str)

    async def initiate_call(
        self,
        to_phone: str,
        from_phone: str,
        provider: str = 'twilio'
    ) -> ConferenceResponse

    async def join_webrtc(
        self,
        conference_id: str,
        sdp_offer: str
    ) -> WebRTCJoinResponse

    async def control_mute(
        self,
        conference_sid: str,
        participant_sid: str,
        muted: bool
    ) -> ControlResponse

    async def end_call(
        self,
        conference_sid: str
    ) -> EndCallResponse

    async def get_status(
        self,
        conference_sid: str
    ) -> StatusResponse
```

**HTTP Client**: `aiohttp` (async HTTP)

**Error Handling**:
- Automatic retry with exponential backoff
- Timeout configuration
- Clear error messages
- Connection pooling

### Outcall-Agent Components

#### 1. Cold Call Endpoints (`app/cold_call/endpoints.py`)

**Purpose**: FastAPI routes for cold call operations

**Routes**:

```python
router = APIRouter(
    prefix="/aicallgo/api/v1/cold-call",
    tags=["cold-call"],
    dependencies=[Depends(require_internal_api_key())]
)

@router.post("/initiate")
async def initiate_cold_call(
    request: ColdCallInitiateRequest
) -> ColdCallConferenceResponse:
    """
    Initiate a cold call by creating a conference and dialing phone.

    Steps:
    1. Validate phone number
    2. Get handler from factory
    3. Create conference room
    4. Dial phone number
    5. Return conference details
    """

@router.post("/webrtc-join")
async def webrtc_join_conference(
    request: WebRTCJoinRequest
) -> WebRTCJoinResponse:
    """
    Join browser WebRTC to existing conference.

    Steps:
    1. Validate conference exists
    2. Process SDP offer
    3. Create SDP answer
    4. Add WebRTC participant to conference
    5. Return SDP answer
    """

@router.post("/control/mute")
async def control_mute(
    request: ControlRequest
) -> ControlResponse:
    """
    Control participant mute state.

    Steps:
    1. Validate conference and participant
    2. Update mute state via provider API
    3. Return updated status
    """

@router.post("/end")
async def end_conference(
    conference_sid: str
) -> EndCallResponse:
    """
    End conference and hang up all participants.

    Steps:
    1. Validate conference exists
    2. Terminate conference via provider API
    3. Clean up resources
    4. Return success status
    """

@router.get("/status/{conference_sid}")
async def get_conference_status(
    conference_sid: str
) -> StatusResponse:
    """
    Get current conference status.

    Returns:
    - Conference state (active, completed, etc.)
    - Participant list
    - Duration
    - Audio quality metrics
    """
```

#### 2. Handler Factory (`app/cold_call/handler_factory.py`)

**Purpose**: Create appropriate handler based on provider

**Pattern**: Factory Pattern

**Interface**:
```python
def get_cold_call_handler(provider: str) -> BaseColdCallHandler:
    """
    Get handler instance for specified provider.

    Args:
        provider: 'twilio' or 'telnyx'

    Returns:
        Handler instance

    Raises:
        ValueError: If provider not supported
        NotImplementedError: If provider not yet implemented
    """
    provider = provider.lower()

    if provider == 'twilio':
        return TwilioColdCallHandler(
            twilio_provider=get_telephony_provider()
        )
    elif provider == 'telnyx':
        return TelnyxColdCallHandler(
            telnyx_provider=get_telephony_provider()
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
```

#### 3. Base Handler (`app/cold_call/base_handler.py`)

**Purpose**: Abstract interface for all handlers

**Interface**:
```python
class BaseColdCallHandler(ABC):
    """Abstract base class for cold call handlers."""

    @abstractmethod
    async def create_conference(
        self,
        conference_id: str,
        status_callback_url: str
    ) -> str:
        """
        Create conference room.

        Args:
            conference_id: Unique conference identifier
            status_callback_url: Webhook for conference events

        Returns:
            Conference SID
        """
        pass

    @abstractmethod
    async def add_phone_participant(
        self,
        conference_sid: str,
        to_phone: str,
        from_phone: str
    ) -> str:
        """
        Add PSTN phone to conference.

        Args:
            conference_sid: Conference to join
            to_phone: Phone number to call (E.164)
            from_phone: Caller ID (E.164)

        Returns:
            Participant SID (call SID)
        """
        pass

    @abstractmethod
    async def add_webrtc_participant(
        self,
        conference_sid: str,
        client_id: str,
        sdp_offer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add WebRTC client to conference.

        Args:
            conference_sid: Conference to join
            client_id: Unique client identifier
            sdp_offer: Optional SDP offer for WebRTC

        Returns:
            Dict with participant_sid and sdp_answer (if applicable)
        """
        pass

    @abstractmethod
    async def control_participant(
        self,
        conference_sid: str,
        participant_sid: str,
        action: str,
        value: Any
    ) -> bool:
        """
        Control participant state.

        Args:
            conference_sid: Conference room
            participant_sid: Participant to control
            action: 'mute', 'unmute', 'hold', etc.
            value: Action-specific value

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def end_conference(
        self,
        conference_sid: str
    ) -> bool:
        """
        End conference and hang up all participants.

        Args:
            conference_sid: Conference to end

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def get_conference_status(
        self,
        conference_sid: str
    ) -> Dict[str, Any]:
        """
        Get conference status.

        Args:
            conference_sid: Conference to query

        Returns:
            Dict with status, participants, duration, etc.
        """
        pass
```

#### 4. Twilio Handler (`app/cold_call/twilio_handler.py`)

**Purpose**: Implement cold calling using Twilio

**Dependencies**:
- `app.telephony.twilio_provider.TwilioProvider`
- `twilio` SDK

**Implementation Details**:

```python
class TwilioColdCallHandler(BaseColdCallHandler):
    """Twilio-specific cold call handler."""

    def __init__(self, twilio_provider: TwilioProvider):
        self.provider = twilio_provider
        self.client = twilio_provider.client

    async def create_conference(
        self,
        conference_id: str,
        status_callback_url: str
    ) -> str:
        """
        Create Twilio conference room.

        Note: Twilio conferences are created implicitly when first
        participant dials in. We use TwiML to create the conference.
        """
        # Conference created via TwiML when calling participant
        # Return friendly name as conference ID
        return conference_id

    async def add_phone_participant(
        self,
        conference_sid: str,
        to_phone: str,
        from_phone: str
    ) -> str:
        """
        Add PSTN phone to Twilio conference.

        Uses Twilio REST API to create call with conference TwiML.
        """
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Conference
            beep="false"
            startConferenceOnEnter="true"
            endConferenceOnExit="false"
            statusCallback="{status_callback_url}"
            statusCallbackEvent="start join leave end"
        >{conference_sid}</Conference>
    </Dial>
</Response>'''

        call = self.client.calls.create(
            to=to_phone,
            from_=from_phone,
            twiml=twiml
        )

        return call.sid

    async def add_webrtc_participant(
        self,
        conference_sid: str,
        client_id: str,
        sdp_offer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add WebRTC client to Twilio conference.

        Uses Twilio Client SDK approach:
        1. Generate access token for client
        2. Client connects to Twilio using token
        3. Client dials conference via TwiML
        """
        # Generate Twilio access token
        from twilio.jwt.access_token import AccessToken
        from twilio.jwt.access_token.grants import VoiceGrant

        token = AccessToken(
            self.provider.account_sid,
            self.provider.api_key_sid,  # Need to add this
            self.provider.api_key_secret,  # Need to add this
            identity=client_id
        )

        voice_grant = VoiceGrant(
            outgoing_application_sid=self.provider.twiml_app_sid,
            incoming_allow=False
        )
        token.add_grant(voice_grant)

        return {
            'access_token': token.to_jwt(),
            'client_id': client_id,
            'conference_name': conference_sid
        }

    async def control_participant(
        self,
        conference_sid: str,
        participant_sid: str,
        action: str,
        value: Any
    ) -> bool:
        """
        Control Twilio conference participant.

        Supported actions:
        - mute: Set participant muted state
        - hold: Put participant on hold
        """
        try:
            if action == 'mute':
                self.client.conferences(conference_sid) \
                    .participants(participant_sid) \
                    .update(muted=value)
                return True
            elif action == 'hold':
                self.client.conferences(conference_sid) \
                    .participants(participant_sid) \
                    .update(hold=value)
                return True
            else:
                logger.warning(f"Unsupported action: {action}")
                return False
        except Exception as e:
            logger.error(f"Failed to control participant: {e}")
            return False

    async def end_conference(
        self,
        conference_sid: str
    ) -> bool:
        """
        End Twilio conference.

        Updates conference status to 'completed', which hangs up
        all participants.
        """
        try:
            self.client.conferences(conference_sid) \
                .update(status='completed')
            return True
        except Exception as e:
            logger.error(f"Failed to end conference: {e}")
            return False

    async def get_conference_status(
        self,
        conference_sid: str
    ) -> Dict[str, Any]:
        """
        Get Twilio conference status.

        Returns conference details and participant list.
        """
        try:
            conference = self.client.conferences(conference_sid).fetch()
            participants = self.client.conferences(conference_sid) \
                .participants.list()

            return {
                'status': conference.status,
                'friendly_name': conference.friendly_name,
                'participant_count': len(participants),
                'participants': [
                    {
                        'sid': p.call_sid,
                        'muted': p.muted,
                        'hold': p.hold,
                        'start_time': p.date_created
                    }
                    for p in participants
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get conference status: {e}")
            return {'status': 'error', 'error': str(e)}
```

#### 5. Telnyx Handler (`app/cold_call/telnyx_handler.py`)

**Purpose**: Placeholder for Telnyx implementation

**Status**: Not yet implemented

```python
class TelnyxColdCallHandler(BaseColdCallHandler):
    """Telnyx-specific cold call handler - TO BE IMPLEMENTED."""

    def __init__(self, telnyx_provider: TelnyxProvider):
        self.provider = telnyx_provider
        logger.warning(
            "TelnyxColdCallHandler is not yet implemented. "
            "Use TwilioColdCallHandler instead."
        )

    async def create_conference(
        self,
        conference_id: str,
        status_callback_url: str
    ) -> str:
        raise NotImplementedError(
            "Telnyx cold calling is not yet implemented. "
            "Please use Twilio provider."
        )

    # ... all other methods raise NotImplementedError
```

**Future Implementation Notes**:
- Telnyx supports conference calling via Conference API
- Similar pattern to Twilio but different API
- WebRTC support via Telnyx WebRTC Client SDK
- Will implement in future sprint

---

## Call Flow Sequences

### Sequence 1: Call Initiation

```
User          Admin-Board       Outcall-Agent    Twilio         Phone
 │                │                  │              │             │
 │  Click "Dial"  │                  │              │             │
 ├───────────────►│                  │              │             │
 │                │  POST /initiate  │              │             │
 │                ├─────────────────►│              │             │
 │                │                  │ Create Conf  │             │
 │                │                  ├─────────────►│             │
 │                │                  │ Conf Created │             │
 │                │                  │◄─────────────┤             │
 │                │                  │   Create Call│             │
 │                │                  ├─────────────►│   Ring...   │
 │                │                  │              ├────────────►│
 │                │  Conference Info │              │             │
 │                │◄─────────────────┤              │             │
 │  Show Modal    │                  │              │             │
 │◄───────────────┤                  │              │             │
 │  "Dialing..."  │                  │              │             │
```

### Sequence 2: WebRTC Connection

```
User          Admin-Board       Outcall-Agent    Twilio      Conference
 │                │                  │              │             │
 │  Get Mic Perm  │                  │              │             │
 ├───────────────►│                  │              │             │
 │  Permission OK │                  │              │             │
 │◄───────────────┤                  │              │             │
 │                │ Create RTC Offer │              │             │
 │                ├─────────────────►│              │             │
 │                │                  │  Generate    │             │
 │                │                  │  Access Token│             │
 │                │                  ├─────────────►│             │
 │                │  RTC Answer +    │              │             │
 │                │  Access Token    │              │             │
 │                │◄─────────────────┤              │             │
 │  Establish     │                  │              │             │
 │  WebRTC        │                  │              │             │
 ├────────────────┼──────────────────┼──────────────┤             │
 │                │                  │              │ Add WebRTC  │
 │                │                  │              │ Participant │
 │                │                  │              ├────────────►│
 │  Audio Connected                  │              │             │
 │◄──────────────────────────────────┼──────────────┼─────────────┤
```

### Sequence 3: Active Call (Both Connected)

```
User          Admin-Board    Conference    Phone
 │                │              │           │
 │  Speak         │              │           │
 ├────────────────┼─────────────►│           │
 │                │              │  Audio    │
 │                │              ├──────────►│
 │                │              │  Audio    │
 │                │              │◄──────────┤
 │  Hear          │              │           │
 │◄───────────────┼──────────────┤           │
 │                │              │           │
 │  Click Mute    │              │           │
 ├───────────────►│              │           │
 │                │ POST /mute   │           │
 │                ├─────────────►│           │
 │                │  Muted       │           │
 │                │◄─────────────┤           │
 │  Mic Muted     │              │           │
 │◄───────────────┤              │           │
```

### Sequence 4: Call End & Logging

```
User          Admin-Board       Outcall-Agent    Conference
 │                │                  │              │
 │  Click "End"   │                  │              │
 ├───────────────►│                  │              │
 │                │  POST /end       │              │
 │                ├─────────────────►│              │
 │                │                  │ End Conf     │
 │                │                  ├─────────────►│
 │                │                  │ Conf Ended   │
 │                │                  │◄─────────────┤
 │                │  Success         │              │
 │                │◄─────────────────┤              │
 │  Show Log Form │                  │              │
 │◄───────────────┤                  │              │
 │                │                  │              │
 │  Select Outcome│                  │              │
 │  Enter Notes   │                  │              │
 ├───────────────►│                  │              │
 │                │                  │              │
 │  Click "Save"  │                  │              │
 ├───────────────►│                  │              │
 │                │ Update Session   │              │
 │                │ State            │              │
 │  Saved ✓       │                  │              │
 │◄───────────────┤                  │              │
```

---

## Provider Abstraction

### Design Pattern

The provider abstraction uses the **Strategy Pattern** to allow runtime selection of telephony providers without changing the core business logic.

### Benefits

1. **Flexibility**: Easy to switch providers via configuration
2. **Testability**: Mock providers for unit testing
3. **Extensibility**: Add new providers without modifying existing code
4. **Maintainability**: Provider-specific code isolated

### Implementation

```python
# Base interface
class BaseColdCallHandler(ABC):
    # Abstract methods...

# Twilio implementation
class TwilioColdCallHandler(BaseColdCallHandler):
    # Twilio-specific implementation...

# Telnyx placeholder
class TelnyxColdCallHandler(BaseColdCallHandler):
    # NotImplementedError for now...

# Factory for provider selection
def get_cold_call_handler(provider: str) -> BaseColdCallHandler:
    if provider == 'twilio':
        return TwilioColdCallHandler(...)
    elif provider == 'telnyx':
        return TelnyxColdCallHandler(...)
    # More providers can be added here
```

### Provider Comparison

| Feature | Twilio | Telnyx | Notes |
|---------|--------|--------|-------|
| **Conference API** | ✅ Yes | ✅ Yes | Both support conference calling |
| **WebRTC Support** | ✅ Twilio Client | ✅ Telnyx WebRTC | Different SDKs |
| **REST API** | ✅ Comprehensive | ✅ Comprehensive | Similar capabilities |
| **Pricing** | $$ Standard | $ Lower cost | Telnyx typically cheaper |
| **Implementation Status** | ✅ Phase 1 | ⏸️ Future | Twilio first, Telnyx later |

---

## WebRTC Integration

### Approach Options

#### Option A: streamlit-webrtc Library

**Pros**:
- Easy integration with Streamlit
- Handles WebRTC complexity
- Built-in UI components
- Auto-manages microphone permissions

**Cons**:
- Less control over WebRTC internals
- Limited customization
- Additional dependency

**Example**:
```python
from streamlit_webrtc import webrtc_streamer, WebRtcMode

webrtc_ctx = webrtc_streamer(
    key="cold-call-audio",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration={
        "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
    },
    media_stream_constraints={
        "video": False,
        "audio": True
    },
    async_processing=True
)

if webrtc_ctx.state.playing:
    # Audio is connected
    pass
```

#### Option B: Custom Streamlit Component (Recommended)

**Pros**:
- Full control over WebRTC negotiation
- Custom UI/UX
- Better Twilio integration
- More flexibility

**Cons**:
- More development effort
- Need to handle WebRTC details
- Custom JavaScript required

**Architecture**:
```javascript
// custom_component.js
class ColdCallDialer extends HTMLElement {
  constructor() {
    super();
    this.peerConnection = null;
    this.localStream = null;
  }

  async getMicrophoneAccess() {
    this.localStream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: false
    });
  }

  async connectToTwilio(accessToken, conferenceName) {
    // Use Twilio.Device SDK
    const device = new Twilio.Device(accessToken);
    await device.register();

    const call = await device.connect({
      params: {
        To: conferenceName
      }
    });

    return call;
  }

  mute() {
    this.localStream.getAudioTracks().forEach(track => {
      track.enabled = false;
    });
  }

  unmute() {
    this.localStream.getAudioTracks().forEach(track => {
      track.enabled = true;
    });
  }

  hangup() {
    if (this.peerConnection) {
      this.peerConnection.close();
    }
    if (this.localStream) {
      this.localStream.getTracks().forEach(track => track.stop());
    }
  }
}
```

### Recommended Approach

**Use Twilio Client SDK directly** for the best integration:

1. Admin-board gets access token from outcall-agent
2. JavaScript component uses Twilio.Device SDK
3. Device connects to conference via token
4. Audio flows through Twilio infrastructure

This approach:
- ✅ Simplifies WebRTC complexity
- ✅ Leverages Twilio's optimized infrastructure
- ✅ Better audio quality and reliability
- ✅ Built-in NAT traversal and firewall handling

---

## Data Models

### Request Models

```python
class ColdCallInitiateRequest(BaseModel):
    """Request to initiate a cold call."""

    to_phone: str = Field(
        ...,
        description="Phone number to call (E.164 format)",
        regex=r'^\+[1-9]\d{1,14}$'
    )
    from_phone: Optional[str] = Field(
        None,
        description="Caller ID (E.164 format)",
        regex=r'^\+[1-9]\d{1,14}$'
    )
    provider: str = Field(
        default='twilio',
        description="Telephony provider to use"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "to_phone": "+15551234567",
                "from_phone": "+15559876543",
                "provider": "twilio"
            }
        }
```

```python
class WebRTCJoinRequest(BaseModel):
    """Request to join browser WebRTC to conference."""

    conference_id: str = Field(
        ...,
        description="Conference room to join"
    )
    client_id: str = Field(
        ...,
        description="Unique client identifier"
    )
    sdp_offer: Optional[str] = Field(
        None,
        description="WebRTC SDP offer (if using pure WebRTC)"
    )
```

```python
class ControlRequest(BaseModel):
    """Request to control conference participant."""

    conference_sid: str
    participant_sid: str
    action: str = Field(..., regex='^(mute|unmute|hold|unhold)$')
    value: Optional[bool] = None
```

### Response Models

```python
class ColdCallConferenceResponse(BaseModel):
    """Response after initiating cold call."""

    conference_sid: str = Field(
        ...,
        description="Twilio conference SID"
    )
    conference_id: str = Field(
        ...,
        description="Friendly conference name"
    )
    call_sid: str = Field(
        ...,
        description="PSTN call SID"
    )
    access_token: Optional[str] = Field(
        None,
        description="Twilio access token for WebRTC"
    )
    status: str = Field(
        ...,
        description="Call status"
    )
    provider: str

    class Config:
        json_schema_extra = {
            "example": {
                "conference_sid": "CF1234567890abcdef",
                "conference_id": "COLD_CALL_abc123",
                "call_sid": "CA1234567890abcdef",
                "access_token": "eyJ...",
                "status": "initiated",
                "provider": "twilio"
            }
        }
```

```python
class WebRTCJoinResponse(BaseModel):
    """Response after joining WebRTC."""

    participant_sid: str
    status: str
    ice_servers: Optional[List[Dict[str, Any]]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "participant_sid": "PA1234567890abcdef",
                "status": "connected",
                "ice_servers": [
                    {"urls": ["stun:stun.l.google.com:19302"]}
                ]
            }
        }
```

### Domain Models

```python
@dataclass
class Contact:
    """Contact from CSV."""

    name: str
    company: str
    phone: str
    title: Optional[str] = None
    call_status: str = "not_called"
    call_outcome: Optional[str] = None
    call_notes: Optional[str] = None
    call_duration: Optional[int] = None
    call_timestamp: Optional[datetime] = None
```

```python
class CallOutcome(str, Enum):
    """Possible call outcomes."""

    CONNECTED = "connected"
    VOICEMAIL = "voicemail"
    NO_ANSWER = "no_answer"
    NOT_INTERESTED = "not_interested"
    FOLLOW_UP = "follow_up"
    WRONG_NUMBER = "wrong_number"
    BUSY = "busy"
```

---

## Security Considerations

### Authentication & Authorization

1. **Admin-Board Access**
   - Requires user login (existing auth system)
   - Session-based authentication
   - No public access to dialer page

2. **Internal API Communication**
   - Internal API key header: `X-API-Key`
   - VPC-only communication
   - No public endpoints for cold calling

3. **Twilio/Telnyx Security**
   - API credentials stored in environment variables
   - Webhook signature validation
   - Secure token generation for WebRTC

### Data Protection

1. **Phone Numbers**
   - Validated before dialing
   - Logged securely
   - No exposure in URLs

2. **Call Notes**
   - Stored in session state only
   - Can be extended to database storage
   - No sensitive data in logs

3. **Audio Streams**
   - Encrypted in transit (TLS/DTLS)
   - Not recorded by default
   - Can enable recording if needed

### Rate Limiting

1. **API Endpoints**
   - Rate limit per user/session
   - Prevent abuse
   - Configurable limits

2. **Concurrent Calls**
   - Limit simultaneous calls per user
   - Resource protection
   - Queue management

---

## Scalability & Performance

### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| **Call Setup Time** | < 3 seconds | From "Dial" to ringing |
| **Audio Latency** | < 150ms | One-way |
| **Concurrent Calls** | 10+ per pod | Limited by resources |
| **WebRTC Connection Time** | < 2 seconds | Browser to conference |

### Scaling Strategies

1. **Horizontal Scaling**
   - Multiple outcall-agent pods
   - Load balancing across pods
   - Stateless design

2. **Resource Optimization**
   - Connection pooling for HTTP clients
   - Async/await for I/O operations
   - Efficient error handling

3. **Monitoring**
   - Call success rates
   - Audio quality metrics
   - Error rates and types
   - Performance metrics

### Bottlenecks & Mitigation

| Bottleneck | Impact | Mitigation |
|------------|--------|------------|
| **Twilio API Rate Limits** | Medium | Implement retry with backoff |
| **WebRTC ICE Negotiation** | Low | Use TURN servers if needed |
| **Session State Size** | Low | Implement pagination for contacts |
| **Network Latency** | Medium | Optimize API calls, use CDN |

---

## Future Enhancements

1. **Telnyx Implementation**
   - Complete TelnyxColdCallHandler
   - Test and validate
   - Performance comparison

2. **Call Recording**
   - Optional recording feature
   - Cloud storage integration
   - Playback UI

3. **Advanced Analytics**
   - Call outcome tracking
   - Conversion metrics
   - Agent performance

4. **CRM Integration**
   - Auto-sync call logs
   - Contact management
   - Follow-up reminders

5. **Auto-dialer**
   - Sequential dialing
   - Skip no-answers automatically
   - Queue management

---

## References

- [Twilio Conference API](https://www.twilio.com/docs/voice/api/conference-resource)
- [Twilio Client SDK](https://www.twilio.com/docs/voice/client/javascript)
- [Streamlit WebRTC](https://github.com/whitphx/streamlit-webrtc)
- [WebRTC Specification](https://www.w3.org/TR/webrtc/)
- [E.164 Phone Number Format](https://en.wikipedia.org/wiki/E.164)
