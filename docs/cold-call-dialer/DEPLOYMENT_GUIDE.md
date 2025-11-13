# Cold Call Dialer - Deployment Guide

**Version**: 1.0
**Date**: 2025-11-12

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Local Development Setup](#local-development-setup)
4. [Staging Deployment](#staging-deployment)
5. [Production Deployment](#production-deployment)
6. [Verification & Testing](#verification--testing)
7. [Troubleshooting](#troubleshooting)
8. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### Required Accounts & Credentials

1. **Twilio Account**
   - Account SID
   - Auth Token
   - Phone number with voice capability
   - API Key and Secret (for WebRTC access tokens)
   - TwiML App SID (for Twilio.Device SDK)

2. **Telnyx Account** (Optional, for future)
   - API Key
   - Phone number with voice capability
   - Connection ID

3. **Development Tools**
   - Python 3.12+
   - Docker & Docker Compose
   - kubectl (for Kubernetes deployment)
   - Git

### Infrastructure Requirements

- **Existing Deployments**: Admin-board and outcall-agent services must be running
- **Network**: VPC internal communication enabled
- **Storage**: Redis instance (already exists)
- **DNS**: Proper domain configuration for webhooks

---

## Environment Configuration

### Outcall-Agent Environment Variables

**File**: `services/outcall-agent/.env`

```bash
# Existing Twilio Configuration (verify these exist)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+15551234567

# NEW: Twilio API Key (for WebRTC access tokens)
TWILIO_API_KEY_SID=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_KEY_SECRET=your_api_key_secret_here
TWILIO_TWIML_APP_SID=APxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Existing Telnyx Configuration (verify these exist)
TELNYX_API_KEY=your_telnyx_api_key_here
TELNYX_PHONE_NUMBER=+15559876543
TELNYX_CONNECTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# NEW: Cold Call Configuration
COLD_CALL_DEFAULT_PROVIDER=twilio

# Existing Configuration
TELEPHONY_SYSTEM=twilio  # or telnyx
DOMAIN=your-domain.com
REDIS_URL=redis://redis:6379/0
INTERNAL_API_KEY=your_shared_internal_api_key
```

### Admin-Board Environment Variables

**File**: `services/admin-board/.env`

```bash
# Existing Configuration
APP_NAME=AICallGO Admin Board
APP_ENV=staging  # or production
DEBUG=False

# Database
DATABASE_URL_SYNC=postgresql://user:pass@host:5432/dbname

# Authentication
SESSION_SECRET_KEY=your_secret_key_here
SESSION_TIMEOUT_HOURS=24

# NEW: Outcall Agent Integration
OUTCALL_AGENT_INTERNAL_URL=http://outcall-agent:8000
INTERNAL_API_KEY=your_shared_internal_api_key  # Must match outcall-agent

# NEW: Feature Flag
ENABLE_COLD_CALL_DIALER=true
```

### Kubernetes Secrets

**Update**: `terraform/modules/k8s_config/main.tf`

Add to `internal-api-secrets` secret (or create if doesn't exist):

```hcl
resource "kubernetes_secret" "internal_api_secrets" {
  metadata {
    name      = "internal-api-secrets"
    namespace = var.namespace
  }

  data = {
    api-key = var.internal_api_key
  }
}
```

Update admin-board deployment to use the secret:

```hcl
resource "kubernetes_deployment" "admin_board" {
  # ... existing configuration ...

  spec {
    template {
      spec {
        container {
          # ... existing container config ...

          env {
            name  = "OUTCALL_AGENT_INTERNAL_URL"
            value = "http://outcall-agent:8000"
          }

          env {
            name = "INTERNAL_API_KEY"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.internal_api_secrets.metadata[0].name
                key  = "api-key"
              }
            }
          }

          env {
            name  = "ENABLE_COLD_CALL_DIALER"
            value = "true"
          }
        }
      }
    }
  }
}
```

---

## Local Development Setup

### Step 1: Clone and Setup

```bash
# Navigate to outcall-agent
cd services/outcall-agent

# Install dependencies
poetry install --with dev

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
vim .env
```

### Step 2: Start Dependencies

```bash
# Start Redis and other dependencies
make dev-up

# Verify Redis is running
docker ps | grep redis
```

### Step 3: Run Outcall-Agent

```bash
# Run server
make run

# In another terminal, verify health
curl http://localhost:8000/health
```

### Step 4: Setup Admin-Board

```bash
# Navigate to admin-board
cd ../admin-board

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env
vim .env

# Set local outcall-agent URL
echo "OUTCALL_AGENT_INTERNAL_URL=http://localhost:8000" >> .env
echo "INTERNAL_API_KEY=dev-local-key-123" >> .env
echo "ENABLE_COLD_CALL_DIALER=true" >> .env
```

### Step 5: Run Admin-Board

```bash
# Start Streamlit
streamlit run streamlit_app.py

# Access in browser
# http://localhost:8501
```

### Step 6: Access Cold Call Dialer

```bash
# Navigate to hidden page (directly)
# http://localhost:8501/16_📞_Cold_Call_Dialer
```

### Step 7: Setup Ngrok (for Twilio Webhooks)

```bash
# Start ngrok
ngrok http 8000

# Copy ngrok URL (e.g., https://abc123.ngrok.io)
# Update .env in outcall-agent:
# DOMAIN=abc123.ngrok.io
```

### Step 8: Configure Twilio

1. Go to Twilio Console
2. Configure phone number webhook URL:
   - Voice URL: `https://abc123.ngrok.io/twilio-voice`
   - Status Callback: `https://abc123.ngrok.io/aicallgo/outcall/twilio-conference-status`

### Step 9: Test Local Call

```bash
# In admin-board, navigate to:
# http://localhost:8501/16_📞_Cold_Call_Dialer

# Upload test CSV with your phone number
# Click "Dial"
# Answer phone when it rings
# Browser audio should connect to phone call
```

---

## Staging Deployment

### Step 1: Update Configuration Files

**Update**: `services/outcall-agent/.env` (staging values)

```bash
DOMAIN=staging.aicallgo.com
REDIS_URL=redis://redis-staging:6379/0
INTERNAL_API_KEY=<generate-secure-key>
# ... other staging values
```

**Update**: `services/admin-board/.env` (staging values)

```bash
APP_ENV=staging
OUTCALL_AGENT_INTERNAL_URL=http://outcall-agent:8000
INTERNAL_API_KEY=<same-as-outcall-agent>
# ... other staging values
```

### Step 2: Build Docker Images

```bash
# Build outcall-agent
cd services/outcall-agent
docker build -t registry.digitalocean.com/aicallgo/outcall-agent:latest .

# Build admin-board
cd services/admin-board
docker build -t registry.digitalocean.com/aicallgo/admin-board:latest .
```

### Step 3: Push to Registry

```bash
# Login to registry
doctl registry login

# Push images
docker push registry.digitalocean.com/aicallgo/outcall-agent:latest
docker push registry.digitalocean.com/aicallgo/admin-board:latest
```

### Step 4: Update Kubernetes Secrets

```bash
# Set kubeconfig
export KUBECONFIG=~/staging-kubeconfig.txt

# Create/update internal API secret
kubectl create secret generic internal-api-secrets \
  --from-literal=api-key=<your-secure-key> \
  -n aicallgo-staging \
  --dry-run=client -o yaml | kubectl apply -f -

# Verify secret
kubectl get secret internal-api-secrets -n aicallgo-staging
```

### Step 5: Deploy Services

```bash
# Deploy outcall-agent
kubectl rollout restart deployment/outcall-agent -n aicallgo-staging

# Wait for rollout
kubectl rollout status deployment/outcall-agent -n aicallgo-staging

# Deploy admin-board
kubectl rollout restart deployment/admin-board -n aicallgo-staging

# Wait for rollout
kubectl rollout status deployment/admin-board -n aicallgo-staging
```

### Step 6: Verify Deployment

```bash
# Check pod status
kubectl get pods -n aicallgo-staging

# Check outcall-agent logs
kubectl logs -f deployment/outcall-agent -n aicallgo-staging --tail=100

# Check admin-board logs
kubectl logs -f deployment/admin-board -n aicallgo-staging --tail=100

# Test health endpoints
kubectl port-forward svc/outcall-agent 8000:8000 -n aicallgo-staging
curl http://localhost:8000/health

kubectl port-forward svc/admin-board 8501:8501 -n aicallgo-staging
curl http://localhost:8501/_stcore/health
```

### Step 7: Configure Twilio for Staging

1. Update Twilio phone number configuration:
   - Voice URL: `https://staging-outcall.aicallgo.com/twilio-voice`
   - Status Callback: `https://staging-outcall.aicallgo.com/aicallgo/outcall/twilio-conference-status`

2. Verify webhook signature validation is enabled

### Step 8: Access Dialer in Staging

```bash
# Navigate to:
# https://staging-admin.aicallgo.com/16_📞_Cold_Call_Dialer

# or if using direct path:
# https://staging-admin.aicallgo.com/dial
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] All tests passing in staging
- [ ] Performance testing completed
- [ ] Load testing completed
- [ ] Security audit completed
- [ ] Documentation updated
- [ ] Rollback plan ready
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Stakeholders notified

### Step 1: Production Configuration

**Update**: `services/outcall-agent/.env` (production values)

```bash
APP_ENV=production
DOMAIN=outcall.aicallgo.com
DEBUG=False
LOG_LEVEL=INFO
# ... production values
```

**Update**: `services/admin-board/.env` (production values)

```bash
APP_ENV=production
DEBUG=False
# ... production values
```

### Step 2: Build Production Images

```bash
# Tag with version number
VERSION=v1.0.0

# Build and tag outcall-agent
cd services/outcall-agent
docker build -t registry.digitalocean.com/aicallgo/outcall-agent:${VERSION} .
docker tag registry.digitalocean.com/aicallgo/outcall-agent:${VERSION} \
           registry.digitalocean.com/aicallgo/outcall-agent:latest

# Build and tag admin-board
cd services/admin-board
docker build -t registry.digitalocean.com/aicallgo/admin-board:${VERSION} .
docker tag registry.digitalocean.com/aicallgo/admin-board:${VERSION} \
           registry.digitalocean.com/aicallgo/admin-board:latest
```

### Step 3: Push Production Images

```bash
# Push versioned images
docker push registry.digitalocean.com/aicallgo/outcall-agent:${VERSION}
docker push registry.digitalocean.com/aicallgo/outcall-agent:latest

docker push registry.digitalocean.com/aicallgo/admin-board:${VERSION}
docker push registry.digitalocean.com/aicallgo/admin-board:latest
```

### Step 4: Deploy to Production

```bash
# Switch to production kubeconfig
export KUBECONFIG=~/prod-kubeconfig.txt

# Update secrets (if needed)
kubectl create secret generic internal-api-secrets \
  --from-literal=api-key=<production-secure-key> \
  -n aicallgo-production \
  --dry-run=client -o yaml | kubectl apply -f -

# Deploy with specific version
kubectl set image deployment/outcall-agent \
  outcall-agent=registry.digitalocean.com/aicallgo/outcall-agent:${VERSION} \
  -n aicallgo-production

kubectl set image deployment/admin-board \
  admin-board=registry.digitalocean.com/aicallgo/admin-board:${VERSION} \
  -n aicallgo-production

# Monitor rollout
kubectl rollout status deployment/outcall-agent -n aicallgo-production
kubectl rollout status deployment/admin-board -n aicallgo-production
```

### Step 5: Production Verification

```bash
# Check pod health
kubectl get pods -n aicallgo-production -l app=outcall-agent
kubectl get pods -n aicallgo-production -l app=admin-board

# Check resource usage
kubectl top pods -n aicallgo-production

# Verify endpoints
curl https://outcall.aicallgo.com/health
curl https://admin.aicallgo.com/_stcore/health

# Check logs for errors
kubectl logs deployment/outcall-agent -n aicallgo-production --tail=50
kubectl logs deployment/admin-board -n aicallgo-production --tail=50
```

### Step 6: Post-Deployment Testing

```bash
# Test cold call dialer
# 1. Login to https://admin.aicallgo.com
# 2. Navigate to /16_📞_Cold_Call_Dialer
# 3. Upload test CSV
# 4. Make test call
# 5. Verify audio quality
# 6. Test mute/unmute
# 7. End call and log outcome
```

### Step 7: Monitor Production

```bash
# Watch pod status
watch kubectl get pods -n aicallgo-production

# Stream logs
kubectl logs -f deployment/outcall-agent -n aicallgo-production

# Check for errors
kubectl logs deployment/outcall-agent -n aicallgo-production | grep ERROR

# Monitor resource usage
kubectl top pods -n aicallgo-production --sort-by=cpu
```

---

## Verification & Testing

### Health Check Endpoints

```bash
# Outcall-agent health
curl -X GET http://outcall-agent:8000/health
# Expected: {"status": "healthy"}

# Admin-board health
curl -X GET http://admin-board:8501/_stcore/health
# Expected: {"status": "ok"}
```

### API Endpoint Testing

```bash
# Test cold call initiate endpoint
curl -X POST http://outcall-agent:8000/aicallgo/api/v1/cold-call/initiate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-internal-api-key" \
  -d '{
    "to_phone": "+15551234567",
    "from_phone": "+15559876543",
    "provider": "twilio"
  }'

# Expected: 201 Created with conference details
```

### WebRTC Connection Testing

1. Open browser console on dialer page
2. Upload CSV and click "Dial"
3. Check console for WebRTC connection logs:
   ```javascript
   // Should see:
   "WebRTC: Creating peer connection"
   "WebRTC: Got local stream"
   "WebRTC: Connection established"
   "WebRTC: ICE connection state: connected"
   ```

### Audio Quality Testing

1. Make test call to your own phone
2. Verify:
   - [ ] Can hear other party clearly
   - [ ] Other party can hear you clearly
   - [ ] No echo or feedback
   - [ ] Latency < 300ms
   - [ ] Mute/unmute works correctly

### Load Testing

```bash
# Use locust or similar tool
# Test concurrent calls
locust -f tests/load_test.py --host=http://outcall-agent:8000

# Monitor during load test
kubectl top pods -n aicallgo-staging
```

---

## Troubleshooting

### Issue: Cold Call Page Not Accessible

**Symptoms**: 404 error when navigating to page

**Solutions**:
1. Verify file exists: `pages/16_📞_Cold_Call_Dialer.py`
2. Check authentication is working
3. Verify Streamlit version >= 1.32
4. Restart admin-board service

```bash
kubectl rollout restart deployment/admin-board -n aicallgo-staging
```

### Issue: WebRTC Connection Fails

**Symptoms**: "Failed to establish WebRTC connection"

**Solutions**:
1. Check browser microphone permissions
2. Verify ICE servers configuration
3. Check network/firewall settings
4. Test STUN server connectivity:
   ```bash
   stunclient stun.l.google.com 19302
   ```
5. Review browser console for errors

### Issue: Phone Call Not Ringing

**Symptoms**: Call initiated but phone doesn't ring

**Solutions**:
1. Verify phone number in E.164 format
2. Check Twilio account balance
3. Verify Twilio phone number configuration
4. Check outcall-agent logs:
   ```bash
   kubectl logs deployment/outcall-agent -n aicallgo-staging | grep "Creating outgoing call"
   ```
5. Verify Twilio webhook URLs are correct

### Issue: No Audio in Conference

**Symptoms**: Call connected but no audio

**Solutions**:
1. Check WebRTC connection status
2. Verify both participants in conference:
   ```bash
   curl http://outcall-agent:8000/aicallgo/api/v1/cold-call/status/{conference_sid}
   ```
3. Check mute status
4. Verify browser audio output device
5. Test with different browser

### Issue: Internal API Authentication Fails

**Symptoms**: 401 Unauthorized errors

**Solutions**:
1. Verify API keys match in both services:
   ```bash
   kubectl get secret internal-api-secrets -n aicallgo-staging -o yaml
   ```
2. Check admin-board environment variables
3. Verify header format: `X-API-Key: value`
4. Restart both services after updating secrets

### Issue: Conference Not Found

**Symptoms**: 404 error when joining WebRTC

**Solutions**:
1. Verify conference was created successfully
2. Check conference ID matches
3. Review outcall-agent logs for creation errors
4. Verify Redis connectivity

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `INVALID_PHONE_FORMAT` | Phone not in E.164 | Add country code with + |
| `PROVIDER_NOT_IMPLEMENTED` | Telnyx selected | Use Twilio provider |
| `CONFERENCE_NOT_FOUND` | Invalid conference ID | Check conference creation logs |
| `WEBRTC_ERROR` | Connection failed | Check browser permissions and network |
| `PROVIDER_ERROR` | Twilio API error | Check Twilio account and credentials |

---

## Rollback Procedures

### Quick Rollback

```bash
# Rollback to previous deployment
kubectl rollout undo deployment/outcall-agent -n aicallgo-staging
kubectl rollout undo deployment/admin-board -n aicallgo-staging

# Verify rollback
kubectl rollout status deployment/outcall-agent -n aicallgo-staging
kubectl rollout status deployment/admin-board -n aicallgo-staging
```

### Rollback to Specific Version

```bash
# List deployment history
kubectl rollout history deployment/outcall-agent -n aicallgo-staging

# Rollback to specific revision
kubectl rollout undo deployment/outcall-agent --to-revision=3 -n aicallgo-staging

# Monitor rollback
kubectl rollout status deployment/outcall-agent -n aicallgo-staging
```

### Rollback Checklist

- [ ] Notify team of rollback
- [ ] Execute rollback commands
- [ ] Verify services are healthy
- [ ] Test critical functionality
- [ ] Check error logs
- [ ] Update stakeholders
- [ ] Document rollback reason
- [ ] Schedule post-mortem

---

## Monitoring & Alerts

### Key Metrics to Monitor

1. **Call Success Rate**
   - Metric: `cold_calls_initiated / cold_calls_completed`
   - Alert if < 90%

2. **WebRTC Connection Success**
   - Metric: `webrtc_connections_attempted / webrtc_connections_established`
   - Alert if < 95%

3. **Average Call Duration**
   - Metric: `avg(call_duration)`
   - Alert if < 30 seconds (may indicate connection issues)

4. **API Error Rate**
   - Metric: `api_errors / api_requests`
   - Alert if > 5%

5. **Response Time**
   - Metric: `p95(api_response_time)`
   - Alert if > 2 seconds

### Grafana Dashboard Queries

```promql
# Call success rate
rate(cold_calls_completed[5m]) / rate(cold_calls_initiated[5m])

# WebRTC connection success
rate(webrtc_connections_established[5m]) / rate(webrtc_connections_attempted[5m])

# API error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Average call duration
avg(call_duration_seconds)

# Response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

---

## Appendix

### Dependencies & Versions

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.12+ | Required for both services |
| Streamlit | 1.32+ | Required for @st.dialog |
| FastAPI | 0.100+ | Current version |
| Twilio SDK | 8.0+ | Python SDK |
| streamlit-webrtc | 0.47.1+ | WebRTC component |
| aiortc | 1.6.0+ | WebRTC support |
| phonenumbers | 8.13.0+ | Phone validation |

### Useful Commands

```bash
# View all pods in namespace
kubectl get pods -n aicallgo-staging

# Describe pod for debugging
kubectl describe pod <pod-name> -n aicallgo-staging

# Execute command in pod
kubectl exec -it <pod-name> -n aicallgo-staging -- /bin/bash

# Port forward for local testing
kubectl port-forward svc/outcall-agent 8000:8000 -n aicallgo-staging

# View recent events
kubectl get events -n aicallgo-staging --sort-by='.lastTimestamp'

# Check resource usage
kubectl top nodes
kubectl top pods -n aicallgo-staging
```

### Contact & Support

- **Development Team**: dev-team@aicallgo.com
- **DevOps**: devops@aicallgo.com
- **Emergency Hotline**: +1-555-EMERGENCY

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-12 | Initial deployment guide |

---

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Twilio Voice API](https://www.twilio.com/docs/voice)
- [Streamlit Deployment Guide](https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app)
- [Digital Ocean Kubernetes](https://docs.digitalocean.com/products/kubernetes/)
