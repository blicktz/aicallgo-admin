# Cold Call Dialer - API Specification

**Version**: 1.0
**Date**: 2025-11-12
**Base URL**: `http://outcall-agent:8000/aicallgo/api/v1/cold-call` (Internal VPC)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Endpoints](#endpoints)
3. [Request/Response Examples](#requestresponse-examples)
4. [Error Handling](#error-handling)
5. [Status Codes](#status-codes)
6. [Webhook Events](#webhook-events)

---

## Authentication

All endpoints require internal API key authentication via header:

```http
X-API-Key: <INTERNAL_API_KEY>
```

**Security Note**: This API is only accessible within the VPC. The internal API key is shared between admin-board and outcall-agent services.

---

## Endpoints

### 1. Initiate Cold Call

**Endpoint**: `POST /initiate`

**Description**: Creates a conference room and initiates an outbound call to the specified phone number.

**Request Body**:
```json
{
  "to_phone": "string (E.164 format, required)",
  "from_phone": "string (E.164 format, optional)",
  "provider": "string (default: 'twilio')"
}
```

**Response**: `201 Created`
```json
{
  "conference_sid": "string",
  "conference_id": "string",
  "call_sid": "string",
  "access_token": "string (optional)",
  "status": "string",
  "provider": "string",
  "created_at": "string (ISO 8601)"
}
```

**Errors**:
- `400 Bad Request` - Invalid phone number format
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Telephony provider error
- `501 Not Implemented` - Provider not supported

**Phone Number Validation**:
- Must be E.164 format: `+[country_code][number]`
- Example: `+15551234567`
- Leading plus sign required
- No spaces, dashes, or parentheses

---

### 2. Join WebRTC to Conference

**Endpoint**: `POST /webrtc-join`

**Description**: Joins a browser WebRTC client to an existing conference room.

**Request Body**:
```json
{
  "conference_id": "string (required)",
  "client_id": "string (required)",
  "sdp_offer": "string (optional)"
}
```

**Response**: `200 OK`
```json
{
  "participant_sid": "string",
  "access_token": "string",
  "conference_name": "string",
  "status": "string",
  "ice_servers": [
    {
      "urls": ["string"]
    }
  ]
}
```

**Errors**:
- `404 Not Found` - Conference not found
- `400 Bad Request` - Invalid conference ID or client ID
- `500 Internal Server Error` - WebRTC connection error

**Usage Flow**:
1. Browser requests microphone permission
2. Creates RTC peer connection
3. Sends request with client ID
4. Receives access token
5. Uses Twilio.Device SDK to connect

---

### 3. Control Participant Mute

**Endpoint**: `POST /control/mute`

**Description**: Mute or unmute a conference participant.

**Request Body**:
```json
{
  "conference_sid": "string (required)",
  "participant_sid": "string (required)",
  "action": "mute | unmute (required)",
  "value": "boolean (optional, defaults based on action)"
}
```

**Response**: `200 OK`
```json
{
  "success": true,
  "conference_sid": "string",
  "participant_sid": "string",
  "muted": "boolean",
  "message": "string"
}
```

**Errors**:
- `404 Not Found` - Conference or participant not found
- `400 Bad Request` - Invalid action
- `500 Internal Server Error` - Control operation failed

**Actions**:
- `mute` - Mute the participant's microphone
- `unmute` - Unmute the participant's microphone

---

### 4. End Conference

**Endpoint**: `POST /end`

**Description**: Terminates a conference and hangs up all participants.

**Request Body**:
```json
{
  "conference_sid": "string (required)"
}
```

**Response**: `200 OK`
```json
{
  "success": true,
  "conference_sid": "string",
  "status": "completed",
  "message": "string",
  "ended_at": "string (ISO 8601)"
}
```

**Errors**:
- `404 Not Found` - Conference not found
- `500 Internal Server Error` - Termination failed

**Side Effects**:
- All participants hung up
- Conference marked as completed
- Resources cleaned up

---

### 5. Get Conference Status

**Endpoint**: `GET /status/{conference_sid}`

**Description**: Retrieves current status of a conference room.

**Path Parameters**:
- `conference_sid` (string, required) - Conference SID

**Response**: `200 OK`
```json
{
  "conference_sid": "string",
  "conference_id": "string",
  "status": "string",
  "participant_count": "integer",
  "duration": "integer (seconds)",
  "created_at": "string (ISO 8601)",
  "started_at": "string (ISO 8601, optional)",
  "ended_at": "string (ISO 8601, optional)",
  "participants": [
    {
      "participant_sid": "string",
      "call_sid": "string",
      "muted": "boolean",
      "hold": "boolean",
      "start_time": "string (ISO 8601)"
    }
  ]
}
```

**Conference Status Values**:
- `init` - Conference created, no participants yet
- `in-progress` - At least one participant connected
- `completed` - Conference ended

**Errors**:
- `404 Not Found` - Conference not found
- `500 Internal Server Error` - Status fetch failed

---

## Request/Response Examples

### Example 1: Full Cold Call Flow

#### Step 1: Initiate Call

**Request**:
```http
POST /aicallgo/api/v1/cold-call/initiate HTTP/1.1
Host: outcall-agent:8000
Content-Type: application/json
X-API-Key: <internal-api-key>

{
  "to_phone": "+15551234567",
  "from_phone": "+15559876543",
  "provider": "twilio"
}
```

**Response**:
```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "conference_sid": "CFabc123def456",
  "conference_id": "COLD_CALL_2025-11-12_abc123",
  "call_sid": "CA789ghi012jkl",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "status": "initiated",
  "provider": "twilio",
  "created_at": "2025-11-12T10:30:00Z"
}
```

#### Step 2: Join WebRTC

**Request**:
```http
POST /aicallgo/api/v1/cold-call/webrtc-join HTTP/1.1
Host: outcall-agent:8000
Content-Type: application/json
X-API-Key: <internal-api-key>

{
  "conference_id": "COLD_CALL_2025-11-12_abc123",
  "client_id": "browser_user_session_xyz"
}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "participant_sid": "PAmno345pqr678",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "conference_name": "COLD_CALL_2025-11-12_abc123",
  "status": "connected",
  "ice_servers": [
    {
      "urls": ["stun:stun.l.google.com:19302"]
    }
  ]
}
```

#### Step 3: Mute Participant

**Request**:
```http
POST /aicallgo/api/v1/cold-call/control/mute HTTP/1.1
Host: outcall-agent:8000
Content-Type: application/json
X-API-Key: <internal-api-key>

{
  "conference_sid": "CFabc123def456",
  "participant_sid": "PAmno345pqr678",
  "action": "mute"
}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "conference_sid": "CFabc123def456",
  "participant_sid": "PAmno345pqr678",
  "muted": true,
  "message": "Participant muted successfully"
}
```

#### Step 4: Get Status

**Request**:
```http
GET /aicallgo/api/v1/cold-call/status/CFabc123def456 HTTP/1.1
Host: outcall-agent:8000
X-API-Key: <internal-api-key>
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "conference_sid": "CFabc123def456",
  "conference_id": "COLD_CALL_2025-11-12_abc123",
  "status": "in-progress",
  "participant_count": 2,
  "duration": 127,
  "created_at": "2025-11-12T10:30:00Z",
  "started_at": "2025-11-12T10:30:05Z",
  "participants": [
    {
      "participant_sid": "PAmno345pqr678",
      "call_sid": null,
      "muted": true,
      "hold": false,
      "start_time": "2025-11-12T10:30:05Z"
    },
    {
      "participant_sid": "PAstu901vwx234",
      "call_sid": "CA789ghi012jkl",
      "muted": false,
      "hold": false,
      "start_time": "2025-11-12T10:30:08Z"
    }
  ]
}
```

#### Step 5: End Call

**Request**:
```http
POST /aicallgo/api/v1/cold-call/end HTTP/1.1
Host: outcall-agent:8000
Content-Type: application/json
X-API-Key: <internal-api-key>

{
  "conference_sid": "CFabc123def456"
}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "conference_sid": "CFabc123def456",
  "status": "completed",
  "message": "Conference ended successfully",
  "ended_at": "2025-11-12T10:32:15Z"
}
```

---

## Error Handling

### Error Response Format

All error responses follow this format:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "object (optional)"
  }
}
```

### Error Codes

| Code | Message | Description |
|------|---------|-------------|
| `INVALID_PHONE_FORMAT` | Invalid phone number format | Phone must be E.164 format |
| `CONFERENCE_NOT_FOUND` | Conference not found | Conference SID doesn't exist |
| `PARTICIPANT_NOT_FOUND` | Participant not found | Participant SID doesn't exist in conference |
| `PROVIDER_NOT_SUPPORTED` | Provider not supported | Requested provider not available |
| `PROVIDER_NOT_IMPLEMENTED` | Provider not implemented | Provider exists but not yet implemented |
| `PROVIDER_ERROR` | Telephony provider error | Error from Twilio/Telnyx API |
| `WEBRTC_ERROR` | WebRTC connection error | Failed to establish WebRTC connection |
| `CONTROL_ERROR` | Control operation failed | Failed to mute/unmute participant |
| `VALIDATION_ERROR` | Validation error | Request validation failed |
| `INTERNAL_ERROR` | Internal server error | Unexpected error occurred |

### Example Error Responses

**Invalid Phone Number**:
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": {
    "code": "INVALID_PHONE_FORMAT",
    "message": "Invalid phone number format",
    "details": {
      "phone": "+1555-123-4567",
      "expected_format": "+[country_code][number]",
      "example": "+15551234567"
    }
  }
}
```

**Conference Not Found**:
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error": {
    "code": "CONFERENCE_NOT_FOUND",
    "message": "Conference not found",
    "details": {
      "conference_sid": "CFabc123def456"
    }
  }
}
```

**Provider Not Implemented**:
```http
HTTP/1.1 501 Not Implemented
Content-Type: application/json

{
  "error": {
    "code": "PROVIDER_NOT_IMPLEMENTED",
    "message": "Telnyx cold calling is not yet implemented. Please use Twilio provider.",
    "details": {
      "provider": "telnyx",
      "supported_providers": ["twilio"]
    }
  }
}
```

**Provider API Error**:
```http
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{
  "error": {
    "code": "PROVIDER_ERROR",
    "message": "Failed to create conference",
    "details": {
      "provider": "twilio",
      "provider_error": "Invalid phone number",
      "provider_code": 21217
    }
  }
}
```

---

## Status Codes

### Success Codes

| Code | Meaning | Usage |
|------|---------|-------|
| `200 OK` | Request successful | Status queries, control operations |
| `201 Created` | Resource created | Conference created |

### Client Error Codes

| Code | Meaning | Usage |
|------|---------|-------|
| `400 Bad Request` | Invalid request data | Validation errors, invalid formats |
| `401 Unauthorized` | Missing/invalid API key | Authentication failure |
| `404 Not Found` | Resource not found | Conference or participant doesn't exist |
| `422 Unprocessable Entity` | Semantic error | Valid format but logically invalid |

### Server Error Codes

| Code | Meaning | Usage |
|------|---------|-------|
| `500 Internal Server Error` | Unexpected error | Provider errors, system failures |
| `501 Not Implemented` | Feature not available | Telnyx provider, future features |
| `503 Service Unavailable` | Temporary unavailability | Provider downtime |

---

## Webhook Events

### Conference Status Callback

Twilio sends status updates to:
```
POST /aicallgo/outcall/twilio-conference-status
```

**Event Types**:
- `conference-start` - First participant joined
- `conference-end` - All participants left
- `participant-join` - New participant joined
- `participant-leave` - Participant left

**Payload Example**:
```json
{
  "FriendlyName": "COLD_CALL_2025-11-12_abc123",
  "ConferenceSid": "CFabc123def456",
  "StatusCallbackEvent": "conference-start",
  "Timestamp": "2025-11-12T10:30:05Z"
}
```

**Handler**: Already implemented in existing `twilio_endpoints.py`

---

## Rate Limits

### API Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/initiate` | 10 requests | per minute |
| `/webrtc-join` | 20 requests | per minute |
| `/control/mute` | 30 requests | per minute |
| `/end` | 20 requests | per minute |
| `/status/:sid` | 60 requests | per minute |

### Twilio API Limits

- **Concurrent Calls**: Based on Twilio account tier
- **API Requests**: 100 requests/second (standard tier)
- **Conference Participants**: Up to 250 per conference (may vary by tier)

**Mitigation**:
- Implement exponential backoff for retries
- Queue requests if hitting limits
- Monitor rate limit headers

---

## Client Implementation Examples

### Python (aiohttp)

```python
import aiohttp
from typing import Optional

class ColdCallAPIClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def initiate_call(
        self,
        to_phone: str,
        from_phone: Optional[str] = None,
        provider: str = 'twilio'
    ) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/initiate",
                json={
                    "to_phone": to_phone,
                    "from_phone": from_phone,
                    "provider": provider
                },
                headers={"X-API-Key": self.api_key}
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def join_webrtc(
        self,
        conference_id: str,
        client_id: str
    ) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/webrtc-join",
                json={
                    "conference_id": conference_id,
                    "client_id": client_id
                },
                headers={"X-API-Key": self.api_key}
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def control_mute(
        self,
        conference_sid: str,
        participant_sid: str,
        muted: bool
    ) -> dict:
        action = "mute" if muted else "unmute"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/control/mute",
                json={
                    "conference_sid": conference_sid,
                    "participant_sid": participant_sid,
                    "action": action
                },
                headers={"X-API-Key": self.api_key}
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def end_call(self, conference_sid: str) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/end",
                json={"conference_sid": conference_sid},
                headers={"X-API-Key": self.api_key}
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def get_status(self, conference_sid: str) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/status/{conference_sid}",
                headers={"X-API-Key": self.api_key}
            ) as response:
                response.raise_for_status()
                return await response.json()
```

### JavaScript (Fetch API)

```javascript
class ColdCallAPIClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }

  async initiateCall(toPhone, fromPhone = null, provider = 'twilio') {
    const response = await fetch(`${this.baseUrl}/initiate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey
      },
      body: JSON.stringify({
        to_phone: toPhone,
        from_phone: fromPhone,
        provider: provider
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error.message);
    }

    return await response.json();
  }

  async joinWebRTC(conferenceId, clientId) {
    const response = await fetch(`${this.baseUrl}/webrtc-join`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey
      },
      body: JSON.stringify({
        conference_id: conferenceId,
        client_id: clientId
      })
    });

    if (!response.ok) {
      throw new Error('Failed to join WebRTC');
    }

    return await response.json();
  }

  async controlMute(conferenceSid, participantSid, muted) {
    const action = muted ? 'mute' : 'unmute';
    const response = await fetch(`${this.baseUrl}/control/mute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey
      },
      body: JSON.stringify({
        conference_sid: conferenceSid,
        participant_sid: participantSid,
        action: action
      })
    });

    if (!response.ok) {
      throw new Error('Failed to control mute');
    }

    return await response.json();
  }

  async endCall(conferenceSid) {
    const response = await fetch(`${this.baseUrl}/end`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey
      },
      body: JSON.stringify({
        conference_sid: conferenceSid
      })
    });

    if (!response.ok) {
      throw new Error('Failed to end call');
    }

    return await response.json();
  }

  async getStatus(conferenceSid) {
    const response = await fetch(
      `${this.baseUrl}/status/${conferenceSid}`,
      {
        headers: {
          'X-API-Key': this.apiKey
        }
      }
    );

    if (!response.ok) {
      throw new Error('Failed to get status');
    }

    return await response.json();
  }
}
```

---

## Testing Endpoints

### Using cURL

```bash
# 1. Initiate call
curl -X POST http://outcall-agent:8000/aicallgo/api/v1/cold-call/initiate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-internal-api-key" \
  -d '{
    "to_phone": "+15551234567",
    "from_phone": "+15559876543",
    "provider": "twilio"
  }'

# 2. Get status
curl -X GET http://outcall-agent:8000/aicallgo/api/v1/cold-call/status/CFabc123 \
  -H "X-API-Key: your-internal-api-key"

# 3. End call
curl -X POST http://outcall-agent:8000/aicallgo/api/v1/cold-call/end \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-internal-api-key" \
  -d '{"conference_sid": "CFabc123"}'
```

### Using HTTPie

```bash
# 1. Initiate call
http POST http://outcall-agent:8000/aicallgo/api/v1/cold-call/initiate \
  X-API-Key:your-internal-api-key \
  to_phone="+15551234567" \
  from_phone="+15559876543" \
  provider="twilio"

# 2. Get status
http GET http://outcall-agent:8000/aicallgo/api/v1/cold-call/status/CFabc123 \
  X-API-Key:your-internal-api-key

# 3. End call
http POST http://outcall-agent:8000/aicallgo/api/v1/cold-call/end \
  X-API-Key:your-internal-api-key \
  conference_sid="CFabc123"
```

---

## Appendix: Provider-Specific Details

### Twilio

**Conference Creation**:
- Conferences are created implicitly when first participant joins
- `FriendlyName` used as conference identifier
- Maximum 250 participants per conference (depending on tier)

**Access Token Generation**:
- Uses Twilio API Key and Secret
- Token grants access to Voice resources
- Expires after configured TTL (default: 1 hour)

**WebRTC Client**:
- Uses Twilio.Device JavaScript SDK
- Handles ICE negotiation automatically
- Built-in NAT traversal

### Telnyx (Future)

**Conference Creation**:
- Uses Telnyx Conference API
- Explicit conference creation required
- Different participant limits (check Telnyx docs)

**WebRTC Client**:
- Uses Telnyx WebRTC SDK
- Different token generation method
- May require custom ICE server configuration

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-12 | Initial API specification |

---

## References

- [Twilio Conference API](https://www.twilio.com/docs/voice/api/conference-resource)
- [Twilio Client SDK](https://www.twilio.com/docs/voice/client/javascript)
- [Telnyx Conference API](https://developers.telnyx.com/docs/api/v2/call-control/Conference-Commands)
- [E.164 Phone Number Format](https://en.wikipedia.org/wiki/E.164)
