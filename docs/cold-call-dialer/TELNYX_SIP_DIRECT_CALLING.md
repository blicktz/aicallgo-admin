# Telnyx SIP Direct Calling - Architecture & Implementation

## Overview

This document describes the simplified architecture for cold call dialing using Telnyx WebRTC SDK with direct browser-to-phone calling, eliminating the need for conference-based bridging required by Twilio.

## Key Architectural Change

### Previous (Conference-Based - Twilio Way)
```
Admin Browser → WebRTC → Conference Room ← Call Control API → Phone Number
                            ↓
                    Track 2+ participants
                    Complex state management
```

### New (Direct Calling - Telnyx Native Way)
```
Admin Browser → Telnyx WebRTC SDK → Phone Number
                     ↓
            Track single call state
            Simpler implementation
```

## Benefits

- ✅ No conference complexity or participant tracking
- ✅ Simpler state management (single call vs. multiple participants)
- ✅ Native Telnyx capabilities (not working around limitations)
- ✅ Direct RTP path with better audio quality
- ✅ Lower costs (no conference usage)
- ✅ Easier debugging (single call leg)

## Configuration

### Environment Variables

**Dedicated SIP Connection (Cold Call Dialer):**
```bash
# SIP Connection for WebRTC browser dialing
TELNYX_SIP_CONNECTION_ID=<dedicated_sip_connection_id>
TELNYX_SIP_API_KEY=<api_key_for_sip_connection>
TELNYX_SIP_PHONE_NUMBER=<phone_number_on_sip_connection>
TELNYX_SIP_USERNAME=<sip_username_for_webrtc_auth>
TELNYX_SIP_PASSWORD=<sip_password_for_webrtc_auth>
```

**Existing AI Agent Connection (Keep Separate):**
```bash
# AI Agent Call Control API (existing)
TELNYX_API_KEY=<existing_api_key>
TELNYX_CONNECTION_ID=<existing_connection_id>
TELNYX_PHONE_NUMBER=<existing_phone_number>
```

### Files Requiring Updates

1. `services/outcall-agent/.env`
2. `services/outcall-agent/app/core/config.py` - Add new settings fields
3. `services/admin-board/.env`
4. Replace all references: `TELNYX_COLD_CALL_*` → `TELNYX_SIP_*`

## Complete Call Flow

### 1. Call Initiation
```
User clicks "Dial" → Admin Board requests SIP credentials → Browser initializes Telnyx WebRTC client
```

### 2. WebRTC Connection
```
Browser: client.newCall({ destinationNumber, callerNumber })
    ↓
Telnyx generates call_control_id
    ↓
Browser receives call.id via stateChange event
```

### 3. Recording Start
```
Browser sends call_control_id to backend
    ↓
Backend: POST to Telnyx Call Control API /v2/calls/{call_control_id}/actions/record_start
    ↓
Recording begins
```

### 4. Call In Progress
```
Two-way audio via WebRTC
Store call start time in Redis when call.answered event received
```

### 5. Call Completion
```
Call ends (hangup) → Telnyx webhook: call.hangup
    ↓
Backend retrieves call data from Redis
    ↓
Backend calculates duration
    ↓
Backend POST to Web Backend: Create call log
```

### 6. Recording Delivery
```
Telnyx webhook: call.recording.saved
    ↓
Backend receives recording_id and download_url
    ↓
Backend POST to Web Backend: Create recording entry
    ↓
Web Backend downloads recording → Upload to Backblaze B2
```

## Key Endpoints

### Admin Board → Outcall Agent

#### GET `/aicallgo/api/v1/cold-call/webrtc-credentials`
- **Purpose:** Get SIP credentials for WebRTC client initialization
- **Auth:** Internal API key
- **Returns:**
  - `sip_username`
  - `sip_password`
  - `status`
- **Note:** Credentials are reusable, can be cached in session

#### POST `/aicallgo/api/v1/cold-call/start-recording`
- **Purpose:** Initiate recording for a WebRTC call
- **Auth:** Internal API key
- **Body:**
  - `call_control_id` - From WebRTC SDK call.id
  - `to_phone` - Destination phone number
  - `from_phone` - Caller ID
- **Action:** Calls Telnyx Call Control API to start recording
- **Returns:** Recording status confirmation

### Telnyx Webhooks → Outcall Agent

#### POST `/aicallgo/api/v1/cold-call/webhook/telnyx/direct/call-status`
- **Events:** `call.initiated`, `call.answered`, `call.hangup`
- **Purpose:** Track call lifecycle
- **Key Actions:**
  - On `call.answered`: Store call start time in Redis
  - On `call.hangup`: Create call log and post to Web Backend

#### POST `/aicallgo/api/v1/cold-call/webhook/telnyx/direct/recording`
- **Events:** `call.recording.saved`, `call.recording.error`
- **Purpose:** Handle recording delivery
- **Key Actions:**
  - Extract recording_id, download_url, duration
  - POST recording metadata to Web Backend
  - Web Backend handles B2 upload

### Outcall Agent → Web Backend

#### POST `/api/v1/call-logs`
- **Purpose:** Create call log entry
- **Body:** `CallLogCreateRequest`
  - `business_id`
  - `caller_phone_number`
  - `to_phone_number`
  - `call_direction: OUTBOUND`
  - `call_start_time`
  - `call_end_time`
  - `call_duration_seconds`
  - `call_status`
  - `twilio_call_sid` (use call_control_id)

#### POST `/api/v1/recordings`
- **Purpose:** Store recording metadata and trigger B2 upload
- **Body:** `RecordingCreateRequest`
  - `call_sid` (use call_control_id)
  - `recording_sid` (Telnyx recording_id)
  - `recording_url`
  - `recording_status`
  - `recording_duration_seconds`
  - `recording_channels`
  - `telephony_provider: "telnyx"`

## Frontend Implementation

### Admin Board WebRTC Component

**Key Functions:**
1. `get_sip_credentials()` - Fetch from backend, cache in session
2. `initialize_telnyx_client()` - Create TelnyxRTC client with SIP credentials
3. `make_call(phone_number)` - Use client.newCall() for direct calling
4. `handle_call_state_changes()` - Track call states and send call_control_id to backend
5. `end_call()` - Hangup call via client

**Call States to Track:**
- `new` - Call initiated
- `trying` - Attempting connection
- `ringing` - Phone is ringing
- `active` - Call connected (two-way audio)
- `hangup` - Call ended

**No longer needed:**
- Conference creation
- Participant count tracking
- Conference status polling

## Backend Implementation

### Key Functions

**Outcall Agent:**
1. `get_webrtc_credentials()` - Return SIP username/password
2. `start_call_recording()` - Call Telnyx API to start recording
3. `handle_call_status_webhook()` - Process call lifecycle events
4. `handle_recording_webhook()` - Process recording saved events
5. `create_call_log_for_cold_call()` - Generate and post call log to Web Backend
6. `store_call_status_in_redis()` - Cache call metadata (simplified for single call)

**Removed/Simplified:**
- Conference creation logic
- Conference status fetching
- Participant management
- Conference webhooks

## Data Storage

### Redis Schema (Simplified)

**Key:** `cold_call_status:{call_control_id}`

**Value:**
```json
{
  "call_control_id": "v3:abc123...",
  "state": "active",
  "to_phone": "+18005551234",
  "from_phone": "+14083572311",
  "call_start_time": "2025-11-15T10:30:00Z",
  "updated_at": "2025-11-15T10:30:45Z"
}
```

**No longer stored:**
- conference_sid
- participant_count
- participants array

## Telnyx Portal Configuration

### SIP Connection Setup

1. Create dedicated SIP Connection for cold call dialer
2. Note the Connection ID
3. Configure SIP credentials (username/password)
4. Associate phone number with connection
5. Generate API key with recording permissions

### Webhook Configuration

Configure on your SIP Connection:

**Call Status Webhook:**
- URL: `https://{DOMAIN}/aicallgo/api/v1/cold-call/webhook/telnyx/direct/call-status`
- Events:
  - `call.initiated`
  - `call.answered`
  - `call.hangup`

**Recording Webhook:**
- URL: `https://{DOMAIN}/aicallgo/api/v1/cold-call/webhook/telnyx/direct/recording`
- Events:
  - `call.recording.saved`
  - `call.recording.error`

## Call Recording Details

### Recording Configuration

**Format:** MP3
**Channels:** Dual (separate tracks for caller/callee)
**Trigger:** Started via Call Control API when call_control_id is available
**Storage:** Telnyx temporary storage → Web Backend downloads → Backblaze B2

### Recording Flow

1. Browser obtains `call_control_id` from WebRTC SDK
2. Browser sends `call_control_id` to backend
3. Backend calls Telnyx API: `POST /v2/calls/{call_control_id}/actions/record_start`
4. Recording starts automatically
5. On call end, Telnyx webhook delivers recording details
6. Backend posts recording metadata to Web Backend
7. Web Backend downloads from Telnyx URL and uploads to B2

## Testing Checklist

### Configuration
- [ ] Create dedicated SIP Connection in Telnyx Portal
- [ ] Generate and store SIP credentials
- [ ] Configure webhooks in Telnyx Portal
- [ ] Update environment variables in both services
- [ ] Update config.py with new settings

### Functionality
- [ ] SIP credentials endpoint returns valid credentials
- [ ] Browser can initialize Telnyx WebRTC client
- [ ] Direct call to phone number works
- [ ] Two-way audio confirmed
- [ ] Call control ID captured successfully
- [ ] Recording starts automatically
- [ ] Call duration tracked correctly
- [ ] Call log posted to Web Backend on hangup
- [ ] Recording webhook received
- [ ] Recording metadata posted to Web Backend
- [ ] Recording uploaded to Backblaze B2

### Edge Cases
- [ ] Call rejected by callee
- [ ] Call not answered (no answer timeout)
- [ ] Call with very short duration (<10 seconds)
- [ ] Recording failure handling
- [ ] Network disconnection during call

## Migration Path

### Option A: Clean Implementation (Recommended)
1. Implement new endpoints alongside existing
2. Create new frontend component for direct calling
3. Test thoroughly in staging
4. Switch admin board to use new flow
5. Remove old conference-based code after verification

### Option B: Feature Flag Toggle
1. Add feature flag `USE_DIRECT_CALLING`
2. Implement both flows in parallel
3. Toggle between conference/direct based on flag
4. Migrate gradually
5. Remove conference code when confident

## Estimated Effort

- **Backend Implementation:** 3-4 hours
  - New endpoints for credentials and recording
  - Webhook handlers
  - Call log creation logic

- **Frontend Implementation:** 2-3 hours
  - New WebRTC component for direct calling
  - Call state tracking
  - UI updates

- **Testing & Debugging:** 2-3 hours
  - End-to-end call flow
  - Recording verification
  - Call log accuracy

- **Documentation & Cleanup:** 1-2 hours
  - Remove old code
  - Update configuration docs

**Total:** 8-12 hours

## Success Metrics

- ✅ Successful direct browser-to-phone calls
- ✅ 100% call recording capture rate
- ✅ Accurate call duration tracking
- ✅ Call logs posted to Web Backend within 5 seconds of hangup
- ✅ Recordings uploaded to B2 within 30 seconds of webhook
- ✅ No audio quality degradation vs. conference approach
- ✅ Reduced latency (no conference hop)

## References

- [Telnyx WebRTC SDK Documentation](https://developers.telnyx.com/docs/voice/webrtc)
- [Telnyx Call Control API - Recording](https://developers.telnyx.com/api/call-control/start-call-record)
- [Telnyx WebRTC Migration from Twilio](https://developers.telnyx.com/docs/voice/webrtc/migration-from-twilio)
- [Storing Call Recordings](https://developers.telnyx.com/docs/voice/programmable-voice/storing-call-recordings)
