# Cold Call Dialer - Complete Implementation Plan

**Version**: 1.0
**Date**: 2025-11-12
**Status**: Ready for Implementation

---

## Table of Contents

1. [Overview](#overview)
2. [Requirements Summary](#requirements-summary)
3. [Architecture Strategy](#architecture-strategy)
4. [Implementation Phases](#implementation-phases)
5. [File Structure](#file-structure)
6. [Timeline & Resources](#timeline--resources)
7. [Risk Assessment](#risk-assessment)

---

## Overview

Create a cold call dialer application within the admin-board service that allows sales representatives to make outbound calls directly from their browser. The critical requirement is connecting browser-based audio (WebRTC) with traditional phone calls (PSTN) so users can talk to contacts through their computer microphone and speakers.

### Key Goals

1. **Browser-to-Phone Connection**: Enable seamless audio communication between browser and phone
2. **Simple Workflow**: Upload CSV → Dial contacts → Log call outcomes
3. **Hidden Access**: Accessible only via direct URL, not shown in main navigation
4. **Provider Flexibility**: Support both Twilio and Telnyx (implement Twilio first)
5. **No New Infrastructure**: Use existing admin-board deployment

---

## Requirements Summary

### Functional Requirements

1. **Contact Management**
   - CSV file upload with validation (name, company, phone, title)
   - Display contacts in table format
   - Track call status per contact

2. **Web-Based Calling**
   - Browser microphone access via WebRTC
   - E.164 phone number validation
   - Connection to outcall-agent for call initiation

3. **Call UI**
   - Modal overlay during active call
   - Call states: Dialing → Connected → Timer
   - Mute/unmute controls
   - End call button

4. **Post-Call Logging**
   - Outcome dropdown (Connected, Voicemail, No Answer, etc.)
   - Notes textarea
   - Save/cancel actions

### Technical Requirements

1. **Architecture**
   - Hidden Streamlit page (not in navigation)
   - Internal VPC communication with outcall-agent
   - Provider abstraction (Twilio/Telnyx)
   - Conference-based call bridging

2. **Security**
   - Authentication required (existing admin-board auth)
   - Internal API key for service-to-service communication
   - Phone number validation and sanitization

3. **Deployment**
   - No new Kubernetes resources
   - Minimal configuration changes
   - Backward compatible

---

## Architecture Strategy

### Call Bridging Flow

The critical technical challenge is connecting browser audio with phone calls. We solve this using **Twilio Conference Rooms**:

```
┌─────────────┐                    ┌──────────────┐                    ┌─────────────┐
│   Browser   │                    │   Outcall    │                    │   Twilio    │
│  (WebRTC)   │◄──────────────────►│    Agent     │◄──────────────────►│ Conference  │
└─────────────┘                    └──────────────┘                    └─────────────┘
      │                                    │                                    │
      │                                    │                                    │
      │                                    ▼                                    ▼
      │                            Create Conference              Add Phone Participant
      │                                    │                                    │
      │                                    │                                    ▼
      └────────────────────────────────────┼────────────────────►  ┌──────────────────┐
                                           │                       │  Contact's Phone  │
                  Audio flows through conference room              └──────────────────┘
```

### Detailed Call Flow

1. **Initiation** (Admin-board → Outcall-agent)
   ```
   POST /aicallgo/api/v1/cold-call/initiate
   {
     "to_phone": "+15551234567",
     "from_phone": "+15559876543",
     "provider": "twilio"
   }
   ```

2. **Conference Creation** (Outcall-agent → Twilio)
   - Creates Twilio conference room
   - Generates unique conference ID
   - Returns conference details to admin-board

3. **PSTN Call** (Outcall-agent → Twilio)
   - Initiates outbound call to contact's phone
   - Connects call to conference room as "Participant A"

4. **WebRTC Connection** (Browser → Outcall-agent → Twilio)
   ```
   POST /aicallgo/api/v1/cold-call/webrtc-join
   {
     "conference_id": "COLD_CALL_abc123",
     "sdp_offer": "v=0\no=- ... (SDP offer)"
   }
   ```
   - Browser establishes WebRTC connection
   - Outcall-agent bridges WebRTC to conference as "Participant B"

5. **Connected Call**
   - Both participants in conference room
   - Audio flows bidirectionally
   - Call controls available (mute, end)

6. **Call End**
   - User clicks "End Call" or hangs up
   - Conference terminated
   - Post-call logging UI displayed

### Provider Abstraction

```python
# Base interface
class BaseColdCallHandler(ABC):
    @abstractmethod
    async def create_conference(self, conference_id: str) -> str

    @abstractmethod
    async def add_phone_participant(self, conference_sid: str, to_phone: str, from_phone: str)

    @abstractmethod
    async def add_webrtc_participant(self, conference_sid: str, ...)

    @abstractmethod
    async def control_participant(self, conference_sid: str, participant_sid: str, action: str)

# Twilio implementation (Phase 1)
class TwilioColdCallHandler(BaseColdCallHandler):
    # Full implementation using Twilio SDK

# Telnyx placeholder (Phase 2)
class TelnyxColdCallHandler(BaseColdCallHandler):
    # Raises NotImplementedError for now
```

---

## Implementation Phases

### Phase 1: Outcall-Agent Backend (2-3 days)

**Location**: `services/outcall-agent/app/cold_call/`

#### Tasks

1. **Create module structure**
   - `__init__.py` - Module initialization
   - `models.py` - Pydantic request/response models
   - `base_handler.py` - Abstract base handler interface
   - `twilio_handler.py` - Twilio implementation
   - `telnyx_handler.py` - Placeholder with NotImplementedError
   - `handler_factory.py` - Provider factory pattern
   - `endpoints.py` - FastAPI route definitions

2. **Implement Twilio handler**
   - Conference creation using `client.conferences.create()`
   - Add phone participant via `participants.create(to=phone_number)`
   - WebRTC participant handling (may need Twilio Voice SDK)
   - Participant control (mute/unmute)
   - Conference termination

3. **Create API endpoints**
   - `POST /aicallgo/api/v1/cold-call/initiate` - Start cold call
   - `POST /aicallgo/api/v1/cold-call/webrtc-join` - Join browser to conference
   - `POST /aicallgo/api/v1/cold-call/control/mute` - Mute control
   - `POST /aicallgo/api/v1/cold-call/end` - End conference
   - `GET /aicallgo/api/v1/cold-call/status/{conference_sid}` - Status check

4. **Testing**
   - Unit tests for models and factory
   - Integration tests with Twilio sandbox
   - Mock handler for testing

**Deliverables**:
- Fully functional Twilio cold call API
- Telnyx placeholder ready for future implementation
- API documentation
- Unit and integration tests

---

### Phase 2: Admin-Board Frontend (3-4 days)

**Location**: `services/admin-board/`

#### Tasks

1. **Create hidden page**
   - File: `pages/16_📞_Cold_Call_Dialer.py`
   - **Critical**: Do NOT add to `streamlit_app.py` navigation dict
   - This makes it accessible via URL but hidden from sidebar

2. **Implement CSV upload**
   - Component: `components/cold_call/csv_parser.py`
   - Validate required columns: name, company, phone
   - Optional column: title
   - Parse and store in session state
   - Display error messages for invalid CSV

3. **Build contact list UI**
   - Display contacts in `st.dataframe()` or custom table
   - Add "Dial" button per row
   - Show call status column
   - "Load New List" button to reset

4. **Implement dialer modal**
   - Use `@st.dialog()` decorator (Streamlit 1.32+)
   - Display call status (Dialing, Connected, timer)
   - WebRTC audio component integration
   - Mute/unmute button
   - End call button

5. **WebRTC integration**
   - **Option A**: Use `streamlit-webrtc` library
     - Simpler integration
     - Built-in microphone access
     - Auto-handles permissions
   - **Option B**: Custom Streamlit component
     - More control over WebRTC
     - Custom UI
     - Direct signaling control

6. **Post-call logging**
   - Outcome dropdown (st.selectbox)
   - Notes textarea (st.text_area)
   - Save button → Update contact in session state
   - Cancel button → Discard notes

7. **API client**
   - Component: `components/cold_call/api_client.py`
   - HTTP client for outcall-agent communication
   - Use internal VPC URL
   - Include internal API key header
   - Error handling and retries

8. **Phone validation**
   - Component: `components/cold_call/phone_validator.py`
   - Use `phonenumbers` library
   - Validate E.164 format
   - Auto-format if possible
   - Display validation errors

**Deliverables**:
- Fully functional cold call dialer UI
- Hidden page accessible via `/dial` URL
- WebRTC audio working
- CSV upload and validation
- Post-call logging

---

### Phase 3: Configuration & Environment (0.5 days)

#### Tasks

1. **Outcall-agent configuration**
   - Add to `.env` (if not present):
     ```bash
     COLD_CALL_DEFAULT_PROVIDER=twilio
     ```

2. **Admin-board configuration**
   - Add to `.env`:
     ```bash
     OUTCALL_AGENT_INTERNAL_URL=http://outcall-agent:8000
     INTERNAL_API_KEY=<shared-secret>
     ENABLE_COLD_CALL_DIALER=true
     ```

3. **Update requirements**
   - Admin-board `requirements.txt`:
     ```
     streamlit-webrtc>=0.47.1
     aiortc>=1.6.0
     aiohttp>=3.9.0
     phonenumbers>=8.13.0
     ```

4. **Kubernetes secrets** (if needed)
   - Update `terraform/modules/k8s_config/main.tf`
   - Add internal API key to secrets
   - Update admin-board deployment env vars

**Deliverables**:
- All environment variables configured
- Dependencies installed
- Kubernetes secrets updated

---

### Phase 4: Testing & Validation (2-3 days)

#### Tasks

1. **Unit tests**
   - CSV parser validation
   - Phone number validation
   - Handler factory provider selection
   - API client error handling

2. **Integration tests**
   - Outcall-agent API endpoints
   - Twilio conference creation
   - Conference participant management
   - WebRTC connection establishment

3. **End-to-end testing**
   - Full call flow from browser to phone
   - Audio quality verification
   - Call controls (mute, end)
   - Post-call logging persistence

4. **Local development setup**
   - Ngrok setup for Twilio webhooks
   - Test with real phone numbers
   - Debug WebRTC issues
   - Browser compatibility testing

5. **Staging deployment**
   - Deploy to staging environment
   - Test in production-like setup
   - Load testing (multiple concurrent calls)
   - Error handling validation

**Deliverables**:
- Comprehensive test suite
- Passing integration tests
- Verified call quality
- Deployment documentation

---

## File Structure

### Outcall-Agent

```
services/outcall-agent/
├── app/
│   ├── cold_call/                    # NEW MODULE
│   │   ├── __init__.py
│   │   ├── models.py                 # Pydantic models
│   │   │   ├── ColdCallInitiateRequest
│   │   │   ├── ColdCallConferenceResponse
│   │   │   ├── WebRTCJoinRequest
│   │   │   ├── ControlRequest
│   │   │   └── StatusResponse
│   │   ├── base_handler.py           # Abstract base class
│   │   │   └── BaseColdCallHandler
│   │   ├── twilio_handler.py         # Twilio implementation ✅
│   │   │   └── TwilioColdCallHandler
│   │   ├── telnyx_handler.py         # Telnyx placeholder ⏸️
│   │   │   └── TelnyxColdCallHandler (NotImplementedError)
│   │   ├── handler_factory.py        # Provider factory
│   │   │   └── get_cold_call_handler(provider: str)
│   │   └── endpoints.py              # FastAPI routes
│   │       ├── POST /aicallgo/api/v1/cold-call/initiate
│   │       ├── POST /aicallgo/api/v1/cold-call/webrtc-join
│   │       ├── POST /aicallgo/api/v1/cold-call/control/mute
│   │       ├── POST /aicallgo/api/v1/cold-call/end
│   │       └── GET  /aicallgo/api/v1/cold-call/status/{conference_sid}
│   └── telephony/
│       ├── twilio_provider.py        # USE EXISTING
│       └── telnyx_provider.py        # USE EXISTING
```

### Admin-Board

```
services/admin-board/
├── pages/
│   └── 16_📞_Cold_Call_Dialer.py     # NEW - Hidden page
│       ├── Authentication check
│       ├── CSV upload section
│       ├── Contact list display
│       ├── Dialer modal (@st.dialog)
│       └── Post-call logging form
├── components/
│   └── cold_call/                    # NEW MODULE
│       ├── __init__.py
│       ├── csv_parser.py             # CSV validation & parsing
│       │   ├── validate_csv(file)
│       │   └── parse_contacts(file)
│       ├── phone_validator.py        # E.164 validation
│       │   ├── validate_phone(phone)
│       │   └── format_e164(phone)
│       └── api_client.py             # Outcall-agent HTTP client
│           ├── initiate_call(to_phone, from_phone)
│           ├── join_webrtc(conference_id, sdp_offer)
│           ├── mute_participant(conference_sid, muted)
│           ├── end_call(conference_sid)
│           └── get_status(conference_sid)
├── requirements.txt                  # UPDATE
│   ├── streamlit-webrtc>=0.47.1     # NEW
│   ├── aiortc>=1.6.0                # NEW
│   ├── aiohttp>=3.9.0               # NEW
│   └── phonenumbers>=8.13.0         # NEW
└── streamlit_app.py                  # NO CHANGES
    └── (Do NOT add 16_📞_Cold_Call_Dialer to navigation)
```

---

## Timeline & Resources

### Development Timeline

| Phase | Tasks | Duration | Dependencies |
|-------|-------|----------|--------------|
| **Phase 1** | Outcall-agent backend | 2-3 days | Twilio account, API credentials |
| **Phase 2** | Admin-board frontend | 3-4 days | Phase 1 complete |
| **Phase 3** | Configuration | 0.5 days | Phase 1-2 complete |
| **Phase 4** | Testing | 2-3 days | All phases complete |
| **Buffer** | Unexpected issues | 1-2 days | - |
| **Total** | End-to-end | **9-13 days** | - |

### Resource Requirements

**Development**:
- 1 Backend developer (FastAPI, Twilio SDK)
- 1 Frontend developer (Streamlit, WebRTC)
- Can be done by same developer with full-stack skills

**Infrastructure**:
- Existing admin-board deployment (no new resources)
- Existing outcall-agent deployment (no new resources)
- Twilio account with conference capability
- Test phone numbers for validation

**External Services**:
- Twilio API access (existing)
- Telnyx API access (existing, for future)

---

## Risk Assessment

### High Priority Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **WebRTC compatibility issues** | High | Medium | Test on multiple browsers early; have fallback UI |
| **Audio quality problems** | High | Medium | Use Twilio's recommended codecs; test extensively |
| **Conference capacity limits** | Medium | Low | Review Twilio account limits; request increase if needed |
| **VPC networking issues** | High | Low | Test internal URL connectivity early |

### Medium Priority Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **CSV format variations** | Medium | Medium | Robust parsing with clear error messages |
| **Phone number validation edge cases** | Low | High | Use established library (phonenumbers) |
| **Session state management** | Medium | Low | Test thoroughly; add state debugging |
| **Streamlit dialog limitations** | Medium | Low | Have fallback to full-page modal if needed |

### Low Priority Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Deployment configuration issues** | Low | Low | Minimal config changes; test in staging first |
| **Hidden page discovery** | Low | Low | Intentional behavior; can add access control later |

---

## Success Criteria

### Phase 1 Success Criteria
- [ ] All API endpoints return correct responses
- [ ] Twilio conference created successfully
- [ ] Phone participant added to conference
- [ ] Conference terminated correctly
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests with Twilio sandbox passing

### Phase 2 Success Criteria
- [ ] CSV upload works with valid files
- [ ] Validation errors displayed for invalid CSV
- [ ] Contact list displays correctly
- [ ] Dialer modal opens on "Dial" click
- [ ] WebRTC audio connection established
- [ ] Mute/unmute controls work
- [ ] Call timer displays accurately
- [ ] Post-call logging saves data
- [ ] Hidden page accessible via direct URL only

### Phase 3 Success Criteria
- [ ] All environment variables configured
- [ ] Dependencies installed successfully
- [ ] Internal API communication works
- [ ] Kubernetes secrets updated (if needed)

### Phase 4 Success Criteria
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] End-to-end test successful (browser to phone)
- [ ] Audio quality acceptable (clear, no echo, low latency)
- [ ] Multiple concurrent calls supported
- [ ] Error handling works correctly
- [ ] Staging deployment successful

### Overall Success Criteria
- [ ] User can upload CSV and see contact list
- [ ] User can click "Dial" and hear ringing
- [ ] Contact answers phone and user can talk via browser
- [ ] Audio quality is production-ready
- [ ] Mute/unmute controls work reliably
- [ ] Call ends cleanly
- [ ] Post-call logging persists data
- [ ] No new infrastructure required
- [ ] Code reviewed and approved
- [ ] Documentation complete

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Set up development environment** (Twilio credentials, test phones)
3. **Create feature branch** (`feature/cold-call-dialer`)
4. **Start Phase 1** (Outcall-agent backend)
5. **Daily standups** to track progress
6. **Code reviews** after each phase
7. **Staging deployment** after Phase 3
8. **Production deployment** after Phase 4 validation

---

## References

- [Requirements Document](./cold-call-dialer.md) - Original requirements
- [Architecture Design](./ARCHITECTURE.md) - Detailed technical design
- [API Specification](./API_SPECIFICATION.md) - API endpoint details
- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Deployment instructions
- [Testing Strategy](./TESTING_STRATEGY.md) - Testing approach
- [Twilio Conference API](https://www.twilio.com/docs/voice/api/conference-resource) - External reference
- [Streamlit WebRTC](https://github.com/whitphx/streamlit-webrtc) - External reference
