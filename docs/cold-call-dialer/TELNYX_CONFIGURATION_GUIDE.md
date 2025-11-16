# Telnyx Cold Call Backend Configuration Guide

**Version**: 1.0
**Date**: 2025-11-14
**Purpose**: Step-by-step guide to configure Telnyx for cold calling

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Telnyx Portal Configuration](#telnyx-portal-configuration)
3. [Local Development Setup](#local-development-setup)
4. [Staging/Production Setup](#stagingproduction-setup)
5. [Verification & Testing](#verification--testing)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

- ✅ Active Telnyx account (https://portal.telnyx.com)
- ✅ Telnyx API key with Call Control permissions
- ✅ At least one Telnyx phone number
- ✅ Access to outcall-agent deployment environment
- ✅ Web-backend configured with cold call business ID

---

## Telnyx Portal Configuration

### Step 1: Create SIP Connection (for WebRTC)

This connection enables browser-based calling via WebRTC.

1. **Login to Telnyx Portal**
   - Navigate to https://portal.telnyx.com
   - Login with your credentials

2. **Create New SIP Connection**
   - Go to **Voice** → **SIP Connections**
   - Click **Create SIP Connection**
   - Select **Credentials** authentication type
   - Give it a descriptive name: `Cold Call Dialer WebRTC`
   - Click **Save**

3. **Configure Authentication**
   - In the SIP Connection settings, go to **Authentication** tab
   - Note the auto-generated **Username** (format: `sip_user_xxxxx`)
   - Click **Generate New Password**
   - **IMPORTANT**: Copy and save the password securely (you won't see it again)
   - Example:
     ```
     Username: sip_user_abc123xyz
     Password: xJ9kL2mN5pQ8rT3v
     ```

4. **Enable WebRTC**
   - In SIP Connection settings, go to **WebRTC** tab
   - Toggle **Enable WebRTC** to ON
   - Under **Allowed Origins**, add your domains:
     ```
     https://staging.aicallgo.com
     https://app.aicallgo.com
     http://localhost:8501  (for local testing)
     ```
   - Click **Save**

5. **Get Connection ID**
   - In the SIP Connection overview, copy the **Connection ID**
   - Format: Usually a numeric ID like `1234567890`
   - Save this for later

### Step 2: Configure Phone Number

1. **Navigate to Phone Numbers**
   - Go to **Phone Numbers** → **My Numbers**
   - Find your phone number or purchase a new one

2. **Assign to SIP Connection**
   - Click on your phone number
   - Under **Connection**, select the SIP Connection created in Step 1
   - Click **Save**

### Step 3: Configure Call Control Application

This enables the Call Control API for programmatic call handling.

1. **Create Call Control Application**
   - Go to **Voice** → **Call Control Applications**
   - Click **Create New Application**
   - Name: `Cold Call Dialer Backend`

2. **Configure Webhooks**

   **For Staging:**
   ```
   Webhook URL: https://staging-outcall.aicallgo.com/aicallgo/api/v1/cold-call/webhook/telnyx/call-status
   ```

   **For Production:**
   ```
   Webhook URL: https://outcall.aicallgo.com/aicallgo/api/v1/cold-call/webhook/telnyx/call-status
   ```

3. **Enable Webhook Events**

   Select the following events:
   - ✅ `call.initiated`
   - ✅ `call.answered`
   - ✅ `call.hangup`
   - ✅ `call.machine.detection.ended` (optional)
   - ✅ `conference.created`
   - ✅ `conference.started`
   - ✅ `conference.ended`
   - ✅ `conference.participant.joined`
   - ✅ `conference.participant.left`
   - ✅ `call.recording.saved`
   - ✅ `call.recording.error` (optional)

4. **Set Webhook Format**
   - Format: **JSON** (not form-encoded)
   - HTTP Method: **POST**
   - Click **Save**

### Step 4: Configure Recording Settings

1. **Enable Call Recording**
   - In your SIP Connection settings
   - Go to **Recording** tab
   - Toggle **Enable Recording** to ON

2. **Recording Configuration**
   - **Recording Channels**: Select **Dual** (separate channels for each side)
   - **Recording Format**: **MP3** or **WAV** (MP3 recommended for size)
   - **Storage**: Telnyx will store for 30 days by default

3. **Recording Webhook**

   **For Staging:**
   ```
   https://staging-outcall.aicallgo.com/aicallgo/api/v1/cold-call/webhook/telnyx/recording-status
   ```

   **For Production:**
   ```
   https://outcall.aicallgo.com/aicallgo/api/v1/cold-call/webhook/telnyx/recording-status
   ```

4. **Save Configuration**

### Step 5: Get API Credentials

1. **Navigate to API Keys**
   - Go to **Settings** → **API Keys**

2. **Create New API Key** (if needed)
   - Click **Create API Key**
   - Name: `Cold Call Dialer`
   - Permissions: Select **Full Access** or at minimum:
     - ✅ Call Control API
     - ✅ Recordings API
     - ✅ Numbers API
   - Click **Create**

3. **Copy API Key**
   - **IMPORTANT**: Copy the API key immediately (format: `KEYxxx...`)
   - You won't be able to see it again
   - Store securely

### Summary of Credentials to Collect

By now you should have collected:

| Credential | Example | Where to Find |
|------------|---------|---------------|
| **API Key** | `KEYxxxxxxxxxxxxx` | Settings → API Keys |
| **Phone Number** | `+15551234567` | Phone Numbers → My Numbers |
| **Connection ID** | `1234567890` | Voice → SIP Connections |
| **SIP Username** | `sip_user_abc123xyz` | SIP Connection → Authentication |
| **SIP Password** | `xJ9kL2mN5pQ8rT3v` | SIP Connection → Authentication |

---

## Local Development Setup

### File: `services/outcall-agent/.env`

Add the following environment variables to your `.env` file:

```bash
# ============================================================================
# Telnyx Configuration (for Cold Calling)
# ============================================================================

# Telnyx API Key (from Settings → API Keys)
TELNYX_API_KEY=KEYxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Telnyx Phone Number (in E.164 format)
TELNYX_PHONE_NUMBER=+15551234567

# Telnyx Connection ID (from Voice → SIP Connections)
TELNYX_CONNECTION_ID=1234567890

# Webhook signature validation (recommended: True for production)
TELNYX_VALIDATE_SIGNATURE=True

# Telnyx WebRTC SIP Credentials (from SIP Connection → Authentication)
TELNYX_SIP_USERNAME=sip_user_abc123xyz
TELNYX_SIP_PASSWORD=xJ9kL2mN5pQ8rT3v

# ============================================================================
# Cold Call Configuration
# ============================================================================

# Business ID for call recordings (UUID from web-backend)
# This is where recordings will be stored in your CRM
COLD_CALL_BUSINESS_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Domain for webhook callbacks
# Local: use ngrok or similar tunnel
# Example: DOMAIN=abc123.ngrok.io
DOMAIN=your-domain.com
```

### Verify Configuration

Run this command to verify your configuration is loaded:

```bash
cd services/outcall-agent
python -c "from app.core.config import settings; print(f'Telnyx API Key: {settings.telnyx_api_key[:10]}...'); print(f'Phone: {settings.telnyx_phone_number}'); print(f'SIP User: {settings.telnyx_sip_username}')"
```

Expected output:
```
Telnyx API Key: KEYxxxxxxx...
Phone: +15551234567
SIP User: sip_user_abc123xyz
```

---

## Staging/Production Setup

### Kubernetes Secrets Configuration

#### Step 1: Update Terraform Variables

**File**: `terraform/staging.tfvars` (or `production.tfvars`)

Add Telnyx credentials:

```hcl
# Telnyx Configuration
telnyx_api_key         = "KEYxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
telnyx_phone_number    = "+15551234567"
telnyx_connection_id   = "1234567890"
telnyx_sip_username    = "sip_user_abc123xyz"
telnyx_sip_password    = "xJ9kL2mN5pQ8rT3v"
telnyx_validate_signature = true

# Cold Call Configuration
cold_call_business_id  = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

**Security Best Practice**: Use environment variables instead of hardcoding:

```bash
# Set via environment variables
export TF_VAR_telnyx_api_key="KEYxxxxx..."
export TF_VAR_telnyx_sip_password="xJ9kL2m..."
```

#### Step 2: Update Terraform Secrets Module

**File**: `terraform/modules/k8s_config/secrets.tf`

Ensure these variables are mapped to Kubernetes secrets:

```hcl
# Telnyx credentials
telnyx_api_key         = var.telnyx_api_key
telnyx_phone_number    = var.telnyx_phone_number
telnyx_connection_id   = var.telnyx_connection_id
telnyx_sip_username    = var.telnyx_sip_username
telnyx_sip_password    = var.telnyx_sip_password
telnyx_validate_signature = var.telnyx_validate_signature

# Cold call business ID
cold_call_business_id  = var.cold_call_business_id
```

#### Step 3: Apply Terraform Changes

```bash
cd terraform

# Source credentials
source .envrc

# Plan changes
make staging-plan

# Apply changes (will update Kubernetes secrets)
make staging-apply
```

#### Step 4: Verify Kubernetes Secrets

```bash
# Set kubeconfig
export KUBECONFIG=~/staging-kubeconfig.txt

# Check if secrets are created
kubectl get secret outcall-agent-secrets -n aicallgo-staging -o yaml

# Decode and verify (optional)
kubectl get secret outcall-agent-secrets -n aicallgo-staging -o jsonpath='{.data.TELNYX_API_KEY}' | base64 -d
```

#### Step 5: Restart Pods

After updating secrets, restart the outcall-agent pods:

```bash
kubectl rollout restart deployment outcall-agent -n aicallgo-staging
kubectl rollout status deployment outcall-agent -n aicallgo-staging
```

---

## Verification & Testing

### Test 1: Verify Handler Creation

```bash
# SSH into outcall-agent pod
kubectl exec -it $(kubectl get pod -l app=outcall-agent -n aicallgo-staging -o jsonpath='{.items[0].metadata.name}') -n aicallgo-staging -- python

# In Python shell:
from app.cold_call.handler_factory import get_cold_call_handler

# Test Telnyx handler creation
handler = get_cold_call_handler("telnyx")
print(f"Handler created: {handler.provider_name}")
print(f"Phone: {handler.phone_number}")
# Should print: Handler created: telnyx
```

### Test 2: Test Conference Creation

Create a test script:

```python
# test_telnyx_conference.py
import asyncio
from app.cold_call.handler_factory import get_cold_call_handler

async def test_conference():
    handler = get_cold_call_handler("telnyx")

    # Create conference
    conference_id = "COLD_CALL_test123"
    result = await handler.create_conference(conference_id)
    print(f"Conference created: {result}")

    # Test WebRTC credentials
    webrtc = await handler.add_webrtc_participant(
        conference_sid=result,
        client_id="test_client"
    )
    print(f"WebRTC credentials: {webrtc}")

asyncio.run(test_conference())
```

Expected output:
```
Conference created: COLD_CALL_test123
WebRTC credentials: {'participant_sid': 'test_client', 'sip_username': 'sip_user_abc123xyz', ...}
```

### Test 3: Test Webhook Endpoints

Use curl to test webhook endpoints:

```bash
# Test conference webhook
curl -X POST https://staging-outcall.aicallgo.com/aicallgo/api/v1/cold-call/webhook/telnyx/conference-status \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "event_type": "conference.started",
      "payload": {
        "conference_id": "test_123"
      }
    }
  }'

# Expected: {"status":"ok"}
```

### Test 4: End-to-End Call Test

1. **Make a test call via API:**

```bash
curl -X POST https://staging-outcall.aicallgo.com/aicallgo/api/v1/cold-call/initiate \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "to_phone": "+15559999999",
    "from_phone": "+15551234567",
    "provider": "telnyx"
  }'
```

2. **Check Telnyx Dashboard:**
   - Go to **Voice** → **Call Logs**
   - Verify call appears with correct status

3. **Check Application Logs:**

```bash
kubectl logs -f $(kubectl get pod -l app=outcall-agent -n aicallgo-staging -o jsonpath='{.items[0].metadata.name}') -n aicallgo-staging | grep -i telnyx
```

Expected log entries:
```
Telnyx outbound call created: call_control_id=xxx
Conference ID prepared for Telnyx: COLD_CALL_xxx
Telnyx conference webhook received: conference.started
```

4. **Check Redis:**

```bash
# Connect to Redis
kubectl exec -it redis-staging-master-0 -n aicallgo-staging -- redis-cli

# In Redis:
KEYS cold_call_status:*
GET cold_call_status:COLD_CALL_xxx

# Should show JSON with participant_count, status, etc.
```

---

## Troubleshooting

### Issue 1: "Telnyx API key not configured"

**Symptom**: Error when creating handler

**Solution**:
```bash
# Check if environment variable is set
echo $TELNYX_API_KEY

# Check in Kubernetes
kubectl get secret outcall-agent-secrets -n aicallgo-staging -o jsonpath='{.data.TELNYX_API_KEY}' | base64 -d

# If missing, update .env or Terraform variables and re-apply
```

### Issue 2: "Telnyx SIP credentials not configured"

**Symptom**: Error when trying WebRTC join

**Solution**:
```bash
# Verify SIP credentials exist
kubectl get secret outcall-agent-secrets -n aicallgo-staging -o jsonpath='{.data.TELNYX_SIP_USERNAME}' | base64 -d

# If missing, ensure you copied them from Telnyx Portal → SIP Connection → Authentication
# Update secrets via Terraform or manually
```

### Issue 3: Webhooks not received

**Symptom**: No webhook events in logs

**Solution**:
1. **Check webhook URL is accessible:**
   ```bash
   curl -v https://staging-outcall.aicallgo.com/aicallgo/api/v1/cold-call/webhook/telnyx/conference-status
   ```

2. **Verify webhook configuration in Telnyx Portal:**
   - Go to Call Control Application
   - Check webhook URL is correct
   - Ensure events are enabled

3. **Check webhook logs in Telnyx Portal:**
   - Go to **Developers** → **Webhooks**
   - View webhook delivery attempts
   - Check for errors (401, 404, 500, etc.)

4. **Test webhook manually:**
   ```bash
   curl -X POST https://staging-outcall.aicallgo.com/aicallgo/api/v1/cold-call/webhook/telnyx/conference-status \
     -H "Content-Type: application/json" \
     -d '{"data":{"event_type":"conference.started","payload":{"conference_id":"test"}}}'
   ```

### Issue 4: Recording not saved to web-backend

**Symptom**: Recording webhook received but not in database

**Solution**:
1. **Check business ID is configured:**
   ```bash
   echo $COLD_CALL_BUSINESS_ID
   ```

2. **Check web-backend API is accessible:**
   ```bash
   # From outcall-agent pod
   curl -v https://web-backend/api/v1/recordings
   ```

3. **Check logs for recording post errors:**
   ```bash
   kubectl logs -f outcall-agent-xxx -n aicallgo-staging | grep -i "recording"
   ```

### Issue 5: WebRTC not connecting

**Symptom**: Browser can't connect via Telnyx WebRTC SDK

**Solution**:
1. **Check browser console for errors**
2. **Verify SIP credentials are correct:**
   ```javascript
   // In browser console
   console.log('SIP Username:', sip_username);
   console.log('SIP Password:', sip_password);
   ```

3. **Check allowed origins in Telnyx Portal:**
   - Go to SIP Connection → WebRTC
   - Ensure your frontend domain is listed

4. **Test WebRTC connection manually:**
   ```html
   <script src="https://cdn.jsdelivr.net/npm/@telnyx/webrtc@2.x/dist/telnyx.min.js"></script>
   <script>
     const client = new TelnyxRTC({
       login: 'your_sip_username',
       password: 'your_sip_password'
     });
     client.connect();
     client.on('telnyx.ready', () => console.log('Connected!'));
   </script>
   ```

### Issue 6: Call not joining conference

**Symptom**: Call initiated but not in conference

**Solution**:
1. **Check call.answered webhook is received:**
   ```bash
   kubectl logs outcall-agent-xxx -n aicallgo-staging | grep "call.answered"
   ```

2. **Verify conference join API call:**
   ```bash
   kubectl logs outcall-agent-xxx -n aicallgo-staging | grep "join_conference"
   ```

3. **Check Telnyx API response:**
   - Look for errors in logs
   - Common issues: Invalid conference_id, call already ended

---

## Configuration Checklist

Use this checklist to ensure everything is configured:

### Telnyx Portal
- [ ] SIP Connection created
- [ ] SIP Username and Password generated and saved
- [ ] WebRTC enabled on SIP Connection
- [ ] Allowed origins configured
- [ ] Phone number assigned to SIP Connection
- [ ] Call Control Application created
- [ ] Webhook URL configured (call-status)
- [ ] Webhook events enabled (all required events)
- [ ] Recording enabled on SIP Connection
- [ ] Recording webhook configured (recording-status)
- [ ] API Key created with correct permissions

### Local Development
- [ ] `.env` file updated with all Telnyx credentials
- [ ] `TELNYX_API_KEY` set
- [ ] `TELNYX_PHONE_NUMBER` set
- [ ] `TELNYX_CONNECTION_ID` set
- [ ] `TELNYX_SIP_USERNAME` set
- [ ] `TELNYX_SIP_PASSWORD` set
- [ ] `COLD_CALL_BUSINESS_ID` set
- [ ] `DOMAIN` set for webhook callbacks
- [ ] Configuration verified with test script

### Staging/Production
- [ ] Terraform variables updated
- [ ] Secrets applied to Kubernetes
- [ ] Pods restarted to pick up new secrets
- [ ] Handler creation test passed
- [ ] Webhook endpoints tested
- [ ] End-to-end call test completed
- [ ] Recording test completed
- [ ] WebRTC connection test completed

---

## Next Steps

After completing configuration:

1. **Test Backend Thoroughly** - Run all verification tests
2. **Deploy Frontend** - Implement Telnyx frontend page (Phase 2)
3. **Integration Testing** - Test full cold calling workflow
4. **Monitor Production** - Set up alerts for webhook failures
5. **Document Issues** - Keep track of any Telnyx-specific quirks

---

## Reference Links

- **Telnyx Portal**: https://portal.telnyx.com
- **Telnyx API Docs**: https://developers.telnyx.com
- **Call Control API**: https://developers.telnyx.com/api/call-control
- **WebRTC SDK**: https://developers.telnyx.com/docs/voice/webrtc
- **Conference API**: https://developers.telnyx.com/api/call-control/create-conference
- **Recording API**: https://developers.telnyx.com/api/call-recordings

---

## Support

For Telnyx-specific issues:
- **Telnyx Support**: support@telnyx.com
- **Telnyx Community**: https://community.telnyx.com

For implementation issues:
- Check logs in Kubernetes: `kubectl logs -f outcall-agent-xxx`
- Review Telnyx webhook delivery logs in Portal
- Test webhooks with curl/Postman

---

**Last Updated**: 2025-11-14
**Version**: 1.0
