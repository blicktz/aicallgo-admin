# Odoo Integration Configuration Guide

## Environment Variables Required

The following environment variables must be configured in `/services/admin-board/.env` for Odoo integration to work:

### Odoo CRM Settings

```bash
# Odoo CRM Integration
ODOO_URL=https://odoo.julya.ai
ODOO_DB=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=sJgC(198253
```

### Variable Descriptions

| Variable | Value | Description |
|----------|-------|-------------|
| `ODOO_URL` | `https://odoo.julya.ai` | **Local/Testing**: Use public URL<br>**Production**: Use internal VPC URL (see below) |
| `ODOO_DB` | `odoo` | Odoo database name |
| `ODOO_USERNAME` | `admin` | Odoo API username with read/write access to contacts |
| `ODOO_PASSWORD` | `sJgC(198253` | Odoo API password for authentication |

---

## Environment-Specific Configuration

### Local Development

For local testing and development, use the **public URL**:

```bash
ODOO_URL=https://odoo.julya.ai
```

**Why**: Your local machine needs to access Odoo over the internet.

**Performance**: Slower due to public internet routing, but acceptable for development.

---

### Production Deployment (Kubernetes)

For production deployment on Digital Ocean Kubernetes, use the **internal VPC URL**:

```bash
ODOO_URL=http://odoo.aicallgo-internal.svc.cluster.local
```

Or if Odoo is a managed service with internal IP:

```bash
ODOO_URL=http://10.x.x.x:8069  # Replace with actual internal IP
```

**Why**: Avoids routing traffic through public internet and back into VPC.

**Benefits**:
- **Faster**: Direct internal network communication
- **More secure**: Traffic stays within VPC
- **Lower latency**: No internet routing overhead
- **No egress costs**: Internal traffic is free

---

## Kubernetes Deployment Configuration

### Option 1: ConfigMap + Secret (Recommended)

**Create Secret for Sensitive Data**:
```bash
kubectl create secret generic odoo-credentials \
  --from-literal=password=sJgC\(198253 \
  -n aicallgo-staging
```

**Create ConfigMap for Non-Sensitive Data**:
```bash
kubectl create configmap odoo-config \
  --from-literal=url=http://odoo.aicallgo-internal.svc.cluster.local \
  --from-literal=db=odoo \
  --from-literal=username=admin \
  -n aicallgo-staging
```

**Update Deployment Manifest**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: admin-board
  namespace: aicallgo-staging
spec:
  template:
    spec:
      containers:
      - name: admin-board
        image: registry.digitalocean.com/aicallgo/admin-board:latest
        env:
        # Odoo Configuration
        - name: ODOO_URL
          valueFrom:
            configMapKeyRef:
              name: odoo-config
              key: url
        - name: ODOO_DB
          valueFrom:
            configMapKeyRef:
              name: odoo-config
              key: db
        - name: ODOO_USERNAME
          valueFrom:
            configMapKeyRef:
              name: odoo-config
              key: username
        - name: ODOO_PASSWORD
          valueFrom:
            secretKeyRef:
              name: odoo-credentials
              key: password
```

### Option 2: Direct Environment Variables

Alternatively, set environment variables directly in deployment:

```yaml
env:
  - name: ODOO_URL
    value: "http://odoo.aicallgo-internal.svc.cluster.local"
  - name: ODOO_DB
    value: "odoo"
  - name: ODOO_USERNAME
    value: "admin"
  - name: ODOO_PASSWORD
    value: "sJgC(198253"  # Not recommended for production
```

**Note**: Direct environment variables are less secure. Use secrets for production.

---

## Verification Steps

### 1. Check Environment Variables

After starting admin-board, verify environment variables are set:

```bash
# Inside the container
kubectl exec -it <admin-board-pod> -n aicallgo-staging -- env | grep ODOO

# Should output:
# ODOO_URL=http://odoo.aicallgo-internal.svc.cluster.local
# ODOO_DB=odoo
# ODOO_USERNAME=admin
# ODOO_PASSWORD=sJgC(198253
```

### 2. Test Odoo Connection

The application will automatically test the connection on startup. Check logs:

```bash
kubectl logs -f <admin-board-pod> -n aicallgo-staging | grep -i odoo

# Should see:
# INFO - Odoo client initialized successfully (URL: http://odoo.aicallgo-internal.svc.cluster.local)
# INFO - Loaded 11 status options from Odoo
```

### 3. Test in Application

1. Navigate to Cold Call Dialer page
2. Click "Load from Odoo" tab
3. Should see: "Fetching filters from Odoo..." spinner
4. If successful: List of saved searches appears
5. If failed: Error message with details

---

## Troubleshooting

### "Odoo integration not available"

**Check 1: Environment Variables Set?**
```bash
kubectl exec -it <admin-board-pod> -n aicallgo-staging -- env | grep ODOO
```
- If empty: Environment variables not configured
- If shows values: Proceed to next check

**Check 2: Network Connectivity**
```bash
# Test from inside admin-board pod
kubectl exec -it <admin-board-pod> -n aicallgo-staging -- \
  curl -I http://odoo.aicallgo-internal.svc.cluster.local
```
- If timeout: Odoo service not accessible
- If 200/301/302: Odoo is reachable

**Check 3: Credentials Valid?**
```bash
# Test authentication with curl
kubectl exec -it <admin-board-pod> -n aicallgo-staging -- \
  curl -X POST http://odoo.aicallgo-internal.svc.cluster.local/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "service": "common",
      "method": "authenticate",
      "args": ["odoo", "admin", "sJgC(198253", {}]
    },
    "id": 1
  }'
```
- If returns user ID: Credentials valid
- If returns error: Credentials invalid

### "No filters found"

**Possible Causes**:
1. No saved searches in Odoo
2. Filters not shared with API user
3. Filters for wrong model

**Solution**:
1. Login to Odoo as admin
2. Go to Contacts
3. Create a filter (e.g., filter by city)
4. Save the search (click star icon)
5. Make it a "Favorite" (not just "Save current search")
6. Refresh in admin-board

### Connection Timeout

**Local Development**:
```bash
# Test public URL accessible
curl -I https://odoo.julya.ai
```

**Production**:
```bash
# Test internal URL accessible from pod
kubectl exec -it <admin-board-pod> -n aicallgo-staging -- \
  curl -I http://odoo.aicallgo-internal.svc.cluster.local
```

If internal URL fails:
- Check Odoo service is running
- Verify DNS resolution: `nslookup odoo.aicallgo-internal.svc.cluster.local`
- Check network policies allow traffic between namespaces
- Verify firewall rules

---

## Security Considerations

### Password Management

**Current Setup (Development)**:
- Password stored in `.env` file
- **Risk**: File checked into git (should be gitignored)
- **Acceptable for**: Local development only

**Production Best Practices**:
1. **Use Kubernetes Secrets**: Store password in secret, not configmap
2. **Rotate Regularly**: Change password periodically
3. **Limit Permissions**: Create dedicated Odoo user with minimal permissions
4. **Use Service Account**: Consider Odoo API keys instead of password

### Network Security

**Local Development**:
- Uses HTTPS public URL
- Credentials sent over encrypted connection
- Acceptable security posture

**Production**:
- Use internal VPC network (HTTP acceptable)
- Traffic never leaves internal network
- Consider service mesh for mTLS if available

### API User Permissions

The Odoo user (`admin`) should have these minimum permissions:

**Required**:
- Read access to `res.partner` (contacts)
- Write access to `res.partner` (update status)
- Read access to `ir.filters` (saved searches)
- Create access to `mail.message` (activity notes)

**Not Required**:
- Full admin access (too permissive)
- Access to other modules (invoicing, inventory, etc.)

**Recommendation**: Create dedicated API user `cold_call_api` with only required permissions.

---

## Performance Tuning

### Rate Limiting

Current Odoo rate limit: **120 requests/minute**

**Usage Calculation**:
- Load filters: 1 request
- Count contacts: 1 request
- Load contacts (50): 1 request
- Get field definition: 1 request (cached)
- Complete call (status + note): 2 requests

**Typical Workload**:
- Load 50 contacts: 3 requests
- Log 10 calls: 20 requests
- **Total**: 23 requests (well under limit)

### Connection Pooling

The `odoo_client.py` uses `requests` library which supports connection pooling.

**Current**: New connection per request (acceptable for low volume)

**Future Optimization**: Use `requests.Session()` for connection reuse

### Caching Strategy

**Currently Cached**:
- ✅ Field definitions (session state)
- ✅ Filter list (session state until refresh)

**Future Caching**:
- Contact data (1 hour TTL)
- Status options (24 hour TTL)
- Filter metadata (1 hour TTL)

---

## Configuration Checklist

### Local Development Setup
- [ ] `.env` file has all 4 Odoo variables
- [ ] `ODOO_URL` uses public HTTPS URL
- [ ] `ODOO_PASSWORD` is correct (test login to Odoo web)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Can access Odoo web interface at https://odoo.julya.ai

### Production Deployment
- [ ] Kubernetes secret created with password
- [ ] ConfigMap created with URL, DB, username
- [ ] Deployment manifest references secret/configmap
- [ ] `ODOO_URL` uses internal VPC URL
- [ ] Network connectivity tested (pod can reach Odoo)
- [ ] Logs show successful Odoo connection
- [ ] Test filter loading in production

### Testing
- [ ] Filters load successfully
- [ ] Contact count matches Odoo
- [ ] Contacts load with pagination
- [ ] Status dropdown shows Odoo options
- [ ] Status update saves to Odoo
- [ ] Activity note created in Odoo
- [ ] Note appears in contact log

---

## Quick Reference

### Environment Variables Summary

```bash
# Required for Odoo Integration
ODOO_URL=<environment-specific>
ODOO_DB=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=sJgC(198253

# Local Development
ODOO_URL=https://odoo.julya.ai

# Production
ODOO_URL=http://odoo.aicallgo-internal.svc.cluster.local
```

### Testing Connection

```python
# Quick test script
from components.cold_call.odoo_integration import get_odoo_integration

odoo = get_odoo_integration()

if odoo.is_available():
    print("✅ Odoo connected")
    filters = odoo.get_available_filters()
    print(f"Found {len(filters)} filters")

    statuses = odoo.get_status_display_names()
    print(f"Status options: {statuses}")
else:
    print("❌ Odoo not available")
```

---

## Support

For issues or questions:
1. Check logs: `kubectl logs -f <admin-board-pod>`
2. Review troubleshooting section above
3. Test with curl commands provided
4. Check Odoo web interface for data consistency

**Common Issues**:
- Credentials: 90% of problems
- Network connectivity: 5% of problems
- Field configuration: 5% of problems
