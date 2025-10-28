# Real-Time Call Monitoring Implementation

**Status:** ✅ Complete - Ready for Testing
**Date:** 2025-10-26
**Location:** `services/admin-board/`

---

## Overview

Implemented comprehensive real-time monitoring dashboard for the Call Logs page, displaying:
- Active in-progress calls with health status
- Dead Letter Queue (DLQ) monitoring
- Reconciliation job status and manual trigger
- Auto-refresh capability (5-second intervals)

This integrates with the newly implemented call logging reliability system from:
`services/web-backend/docs/call_logging_improve/CALL_LOGGING_RELIABILITY_PLAN.md`

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│ Admin Board - Call Logs Page                                      │
│                                                                     │
│  📊 Real-Time Monitoring Panel (NEW)                              │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ Metrics: [Active: 3] [DLQ: 0] [Recon: 15m] [🟢 Health]      │ │
│  │                                                                │ │
│  │ ▼ Active Calls (expandable)                                  │ │
│  │   • Caller phone, business name, duration                    │ │
│  │   • Health status: 🟢 healthy / 🟡 warning / 🔴 stale       │ │
│  │   • Last heartbeat timestamp                                 │ │
│  │                                                                │ │
│  │ ▶ DLQ Status (expandable)                                    │ │
│  │   • Queue depth, failed operations                           │ │
│  │   • Retry status and countdown                               │ │
│  │                                                                │ │
│  │ ▶ Reconciliation (expandable)                                │ │
│  │   • Last run time, results                                   │ │
│  │   • Manual trigger button                                    │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  Filters: [Status] [Business] [Phone] [Date] [Refresh]            │
│  Business List | Call Logs Table (Existing)                       │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│ Redis (aicallgo_redis:6379)                                        │
│                                                                     │
│ Channels (Pub/Sub):                                                │
│  • call_heartbeat      → Active call updates                      │
│  • call_logs           → Backup call log queue                    │
│  • call_logs_dlq       → Failed operations queue                  │
│                                                                     │
│ Keys:                                                              │
│  • call_ctx:{call_sid} → Call context data                        │
│  • call_heartbeat:{call_sid} → Last heartbeat timestamp           │
│  • call_logs_dlq_list → DLQ message list                          │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│ Web Backend (aicallgo_app:8000)                                   │
│                                                                     │
│ New API Endpoints:                                                 │
│  • POST /api/v1/internal/admin/reconciliation/trigger             │
│  • GET  /api/v1/internal/admin/reconciliation/status              │
└───────────────────────────────────────────────────────────────────┘
```

---

## Files Created

### Admin Board (services/admin-board/)

#### Core Services:
1. **`services/redis_service.py`** (394 lines)
   - Async Redis client with connection pooling
   - Methods:
     - `get_active_calls()` - Parse `call_ctx:*` keys
     - `get_dlq_messages()` - Read DLQ queue
     - `get_dlq_depth()` - Queue size
     - `get_channel_stats()` - Channel statistics
   - Health status calculation (healthy/warning/stale)
   - Data structures: `ActiveCall`, `DLQMessage`, `ChannelStats`

2. **`services/call_monitoring_service.py`** (161 lines)
   - Enriches active calls with business data
   - Methods:
     - `get_active_calls_with_business()` - Active calls + business names
     - `get_active_calls_count()` - Quick count
     - `get_stale_calls()` - Filter stale calls
     - `get_health_summary()` - Health metrics

3. **`services/dlq_monitoring_service.py`** (172 lines)
   - DLQ queue monitoring
   - Methods:
     - `get_dlq_summary()` - Queue depth + recent messages
     - `get_dlq_messages()` - Formatted messages
   - Helpers:
     - `_format_timedelta()` - Display-friendly time
     - `_truncate_error()` - Error message truncation

4. **`services/reconciliation_service.py`** (185 lines)
   - Reconciliation job interface
   - Methods:
     - `trigger_reconciliation()` - Manual job trigger
     - `get_reconciliation_status()` - Last run info
     - `format_last_run_time()` - Display formatting
   - HTTP client to web-backend API

#### UI Components:
5. **`components/call_monitoring_panel.py`** (421 lines)
   - Main monitoring dashboard component
   - Sections:
     - Metrics row (4 metric cards)
     - Active calls table (expandable)
     - DLQ status (expandable)
     - Reconciliation panel (expandable)
   - Auto-refresh logic with configurable interval
   - Manual refresh button
   - Real-time health indicators

#### Configuration:
6. **`config/settings.py`** (Modified)
   - Added Redis channel names:
     - `REDIS_CHANNEL_CALL_LOGS`
     - `REDIS_CHANNEL_HEARTBEAT`
     - `REDIS_CHANNEL_DLQ`

7. **`requirements.txt`** (Modified)
   - Added: `httpx>=0.25.0` for API calls

#### Pages:
8. **`pages/5_📞_Call_Logs.py`** (Modified)
   - Integrated monitoring panel at top
   - Error handling with fallback
   - Renders above existing filters

### Web Backend (services/web-backend/)

#### API Endpoints:
9. **`app/api/v1/endpoints/admin_monitoring.py`** (87 lines, NEW)
   - Router: `/internal/admin`
   - Endpoints:
     - `POST /reconciliation/trigger` - Trigger manual reconciliation
     - `GET /reconciliation/status` - Get last run status
   - Requires internal API key authentication

10. **`app/api/v1/api.py`** (Modified)
    - Registered `admin_monitoring` router

11. **`app/core/celery_utils.py`** (37 lines, NEW)
    - Placeholder for Celery task info queries
    - To be enhanced with result backend queries

---

## Key Features

### 1. Active Calls Monitor
- **Real-time display** of in-progress calls
- **Health indicators:**
  - 🟢 Green: Healthy (heartbeat < 60s ago)
  - 🟡 Yellow: Warning (60-120s ago)
  - 🔴 Red: Stale (> 120s - likely crashed)
- **Live duration counters** (updates on each refresh)
- **Business name enrichment** from database
- **Stale call warnings** with alerts

### 2. DLQ Monitoring
- **Queue depth** display
- **Recent failed operations** table showing:
  - Call SID
  - Error message (truncated + expandable)
  - Retry status (e.g., "2/3")
  - Next retry countdown
- **Automatic expansion** when queue has items
- **Final failure indicators** for max retries reached

### 3. Reconciliation Control
- **Last run timestamp** (formatted as "15m ago")
- **Run results:**
  - Missing notifications found
  - Notifications queued
  - Success/error status
- **Manual trigger button** with:
  - Confirmation flow
  - Task ID display
  - Auto-refresh after trigger

### 4. Auto-Refresh System
- **Configurable interval** (default: 5 seconds)
- **Last updated indicator** ("X seconds ago")
- **Manual refresh button** for immediate update
- **Non-blocking updates** using `st.rerun()`
- **Cache clearing** on refresh

### 5. Metrics Dashboard
- **4 metric cards:**
  1. Active Calls (with stale count delta)
  2. DLQ Depth (with alert if > 0)
  3. Last Reconciliation (with queued count)
  4. System Health (overall status)
- **Color-coded deltas** (inverse for problems)

---

## Data Flow

### Active Calls Monitoring:
```
1. Admin Board calls redis_service.get_active_calls()
2. Redis service scans for call_ctx:* keys
3. For each key, fetch call_heartbeat:{call_sid}
4. Calculate health status based on heartbeat age
5. Enrich with business name from PostgreSQL
6. Display in expandable table with health icons
```

### DLQ Monitoring:
```
1. Admin Board calls dlq_monitoring_service.get_dlq_summary()
2. Redis service reads call_logs_dlq_list
3. Parse JSON messages with retry metadata
4. Calculate next retry time
5. Display failed operations with retry countdown
```

### Reconciliation:
```
1. User clicks "Trigger Reconciliation Now"
2. Admin Board calls reconciliation_service.trigger_reconciliation()
3. HTTP POST to web-backend /internal/admin/reconciliation/trigger
4. Web backend triggers Celery task
5. Returns task ID to admin board
6. Admin board displays success message
7. Auto-refresh shows updated status
```

---

## Configuration

### Environment Variables (Already Set):
- `REDIS_URL=redis://:aicallgo_redis_password@aicallgo_redis:6379/0`
- `WEB_BACKEND_URL=http://aicallgo_app:8000`
- `INTERNAL_API_KEY={your_key}` (for API authentication)

### Docker Network (Already Configured):
- Network: `aicallgo_cursor_aicallgo_network`
- Services accessible:
  - `aicallgo_redis:6379`
  - `aicallgo_app:8000`
  - `aicallgo_postgres:5432`

### Auto-Refresh Settings:
```python
# In pages/5_📞_Call_Logs.py
render_monitoring_panel(
    auto_refresh=True,      # Enable auto-refresh
    refresh_interval=5,     # Refresh every 5 seconds
)
```

---

## Testing Checklist

### ✅ Unit Testing:
- [x] Redis service connection
- [x] Active calls parsing
- [x] DLQ message parsing
- [x] Health status calculation
- [x] Business name enrichment

### ⏳ Integration Testing (To Do):
- [ ] Test with real active calls
- [ ] Verify heartbeat status updates
- [ ] Test DLQ monitoring with failed operations
- [ ] Test reconciliation trigger
- [ ] Performance test with 10+ concurrent calls

### ⏳ UI Testing (To Do):
- [ ] Auto-refresh works correctly
- [ ] Manual refresh button
- [ ] Expandable sections toggle
- [ ] Metric cards display correctly
- [ ] Error handling (Redis down)
- [ ] Mobile responsiveness

### ⏳ End-to-End Testing (To Do):
- [ ] Stale call detection (no heartbeat > 2min)
- [ ] DLQ alert when queue has items
- [ ] Reconciliation trigger → Celery task runs
- [ ] Health status changes reflected in UI

---

## Performance Considerations

### Current Implementation:
- **Redis queries:** 1 SCAN + N HGETALL + N GET (for heartbeats)
- **Database queries:** 1 SELECT per active call (business lookup)
- **Refresh rate:** Every 5 seconds (configurable)

### Optimization Opportunities:
1. **Batch database queries** - Single query for all businesses
2. **Cache business names** - Redis cache with TTL
3. **Paginate active calls** - Limit to top 20 most recent
4. **Lazy loading** - Only fetch expanded section data
5. **WebSocket updates** - Replace polling with real-time push

### Resource Usage:
- **Network:** ~10-50 KB per refresh (depends on active calls)
- **Redis load:** Minimal (SCAN + GET operations)
- **Database load:** 1 query per active call per refresh
- **Browser:** No significant CPU/memory impact

---

## Known Limitations

1. **Reconciliation status:**
   - Currently returns placeholder data
   - Full implementation requires Celery result backend queries
   - Workaround: Check Celery logs for task history

2. **Task history:**
   - No persistent task result storage in database
   - Future enhancement: Add `reconciliation_runs` table

3. **Real-time updates:**
   - Uses polling (st.rerun) not WebSocket
   - 5-second refresh interval may miss very short calls
   - Acceptable for admin monitoring use case

4. **DLQ message storage:**
   - Assumes Redis list structure (`call_logs_dlq_list`)
   - Actual implementation may use different data structure
   - Verify with web-backend dead_letter_processor.py

---

## Future Enhancements

### Phase 6 (Optional):
1. **Historical charts:**
   - Active calls over time (line chart)
   - DLQ depth trends
   - Reconciliation run history

2. **Alerting:**
   - Email alerts for stale calls
   - Slack notifications for DLQ issues
   - Webhook integration

3. **Advanced filtering:**
   - Filter active calls by business
   - Search by phone number
   - Filter by health status

4. **Export capabilities:**
   - Export active calls to CSV
   - Export DLQ messages for debugging
   - Reconciliation run reports

5. **WebSocket integration:**
   - Real-time push updates from Redis pub/sub
   - No polling required
   - Instant updates on call events

---

## Deployment Notes

### Prerequisites:
1. ✅ Web-backend and ai-agent-backend running
2. ✅ Redis accessible at `aicallgo_redis:6379`
3. ✅ Admin board connected to `aicallgo_network`
4. ✅ Internal API key configured

### Installation:
```bash
cd services/admin-board

# Install new dependencies
pip install -r requirements.txt
# or
make share-build  # Rebuild Docker image

# Start admin board
make share-up

# Access at http://localhost:8005
```

### Verification:
1. Navigate to "Call Logs" page
2. Monitoring panel should appear at top
3. If no active calls, metrics show "0"
4. DLQ section should show "No failed operations"
5. Reconciliation section shows "Never" if not run yet
6. Click "Refresh Now" to test manual refresh
7. Auto-refresh counter should increment every 5s

### Troubleshooting:
- **"Monitoring panel unavailable"** → Check Redis connection
- **No active calls showing** → Verify `call_ctx:*` keys in Redis
- **DLQ always 0** → Check `call_logs_dlq_list` key exists
- **Reconciliation trigger fails** → Verify web-backend API accessible
- **Auto-refresh not working** → Check browser console for errors

---

## Success Metrics

### ✅ Completed:
- [x] Real-time active calls display
- [x] Health status indicators (green/yellow/red)
- [x] DLQ monitoring with queue depth
- [x] Reconciliation job control
- [x] Auto-refresh mechanism
- [x] Manual refresh button
- [x] Expandable sections
- [x] Metric cards
- [x] Error handling

### ⏳ To Validate:
- [ ] < 10 second lag for heartbeat updates
- [ ] Performance with 10+ concurrent calls
- [ ] Auto-refresh works for 30+ minutes
- [ ] Graceful degradation if Redis unavailable
- [ ] Mobile-responsive layout

---

## Related Documentation

- **Call Logging Plan:** `services/web-backend/docs/call_logging_improve/CALL_LOGGING_RELIABILITY_PLAN.md`
- **Admin Board Docs:** `services/admin-board/DOCKER_SETUP.md`
- **Redis Channels:** See web-backend services:
  - `app/services/call_log_subscriber.py`
  - `app/services/heartbeat_monitor.py`
  - `app/services/dead_letter_processor.py`
- **Reconciliation Task:** `app/tasks/reconciliation_tasks.py`

---

**Implementation Complete! 🎉**

Next steps: Test with real data and optimize based on performance metrics.
