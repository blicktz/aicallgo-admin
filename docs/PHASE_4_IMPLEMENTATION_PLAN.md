# Phase 4 Implementation Plan - Admin Board

## Overview
Phase 4 adds three new read-only pages (Promotions, Appointments, System) and enhances all pages with CSV export, auto-refresh, manual refresh buttons, error handling, and query optimization.

**Estimated Time:** 2-3 days

---

## Task Breakdown

### Task 29: Build Promotions Page (🎟️)

**Files to Create:**
- `services/admin-board/services/promotion_service.py` - Service layer for promotion code queries
- `services/admin-board/pages/8_🎟️_Promotions.py` - Read-only promotion code tracking

**Implementation Details:**

#### Promotions Page Layout:
1. **Promotion Codes Table** (Main View)
   - Columns: Code, Stripe Promotion ID, User Count, Total Usage Count, Created At
   - Search/filter by code
   - Click to view detailed usage

2. **Promotion Code Detail Panel**
   - Basic info: code, Stripe ID, creation date
   - Users currently using this code (with links to user details)
   - Usage history table with columns: User Email, Action, Date, Stripe Invoice ID

3. **Usage History Section**
   - Filterable by: user, action (validated/applied/cleared/failed), date range
   - Shows audit trail of all promotion code activities

4. **CSV Export**
   - Export promotion codes list
   - Export usage history

**Data Source:**
- Models: `PromotionCode`, `PromotionCodeUsage` from `web-backend/app/models/promotion_code_models.py`
- CRUD: `crud_promotion_code.py` - Need to create sync wrapper methods

**Service Methods Required:**
```python
# promotion_service.py
def get_promotion_codes(session, limit, offset, search_query)
def get_promotion_code_by_id(session, promo_id)
def get_users_by_promotion_code(session, promo_code_id)
def get_usage_history(session, promo_code_id=None, user_id=None, action=None, start_date=None, end_date=None, limit=50, offset=0)
def get_promotion_code_stats(session, promo_code_id)  # user count, usage count
```

---

### Task 30: Build Appointments Page (📅)

**Files to Create:**
- `services/admin-board/services/appointment_service.py` - Service layer for appointment queries
- `services/admin-board/pages/9_📅_Appointments.py` - Appointment viewing and search

**Implementation Details:**

#### Appointments Page Layout:
1. **Search and Filters Section**
   - Search by: user email, end user name/email, title
   - Filters:
     - Date range picker (start time)
     - Status dropdown: all/confirmed/cancelled/completed/no_show
     - Booking source: all/ai_call/manual
   - Sort by: start_time (desc/asc)

2. **Appointments Table**
   - Columns: Start Time, User Email, Title, End User Name, Status, Booking Source, Duration
   - Status badges with appropriate colors
   - Click row to view details

3. **Appointment Detail Panel**
   - **Basic Info:**
     - Title, description
     - Start/end time with timezone
     - Status badge
     - Booking source
   - **Parties:**
     - User (with link to user detail)
     - Business (if linked, with link to business detail)
     - End user: name, email, phone
   - **Tracking:**
     - Confirmation sent at
     - Reminder sent at
     - Cancelled at (if applicable) + cancellation reason
   - **Linked Call Log** (if exists)
     - Link to call log detail
   - **Extra Data** (JSON display)

4. **Statistics Cards** (Top of page)
   - Total appointments (filtered)
   - By status: Confirmed, Cancelled, Completed, No-show
   - By booking source: AI Call, Manual

5. **CSV Export**

**Data Source:**
- Models: `Appointment`, `AppointmentEndUser` from `web-backend/app/models/`
- CRUD: `crud_appointment_sync.py` (already exists!)

**Service Methods Required:**
```python
# appointment_service.py
def get_appointments(session, limit, offset, search_query, status, booking_source, start_date, end_date)
def get_appointment_by_id(session, appointment_id)
def get_appointment_stats(session, start_date=None, end_date=None)  # counts by status/source
def get_end_user_by_id(session, end_user_id)
```

---

### Task 31: Build System Page (🔧)

**Files to Create:**
- `services/admin-board/services/system_service.py` - System health and statistics
- `services/admin-board/pages/10_🔧_System.py` - Health checks and database stats

**Implementation Details:**

#### System Page Layout:
1. **Health Checks Section**
   - **Database**:
     - Status: ✅ Connected / ❌ Error
     - Connection pool stats (if available)
     - Response time
   - **Redis** (optional):
     - Status: ✅ Connected / ❌ Error / ⚠️ Not Configured
     - Test with simple PING
   - **External Services** (read-only indicators):
     - Stripe API: Check if we have valid products synced
     - Note: Don't actually call external APIs, just check local sync status

2. **Database Statistics**
   - **Table Row Counts:**
     - Users (total, active)
     - Businesses
     - AI Agents
     - Call Logs (total, last 30 days)
     - Appointments (upcoming, past)
     - Subscriptions (active, trial, cancelled)
     - Credit Transactions
     - Promotion Codes
   - **Growth Trends:**
     - New users: today, last 7 days, last 30 days
     - New businesses: today, last 7 days, last 30 days
     - New calls: today, last 7 days
   - **Data Quality Metrics:**
     - Users with businesses: count + percentage
     - Users with active agents: count + percentage
     - Users with subscriptions: count + percentage

3. **System Information**
   - Python version
   - Streamlit version
   - Database type and version
   - Environment (from settings.APP_ENV)
   - Deployment info (if available)
   - Current timestamp (server time)

4. **Query Performance Section**
   - List slow queries (if tracking enabled)
   - Query execution stats (optional)

5. **Manual Actions** (Admin tools)
   - "Clear All Cache" button
   - "Test Database Connection" button
   - "Generate System Report" (CSV with all stats)

**Service Methods Required:**
```python
# system_service.py
def check_database_health(session) -> dict
def check_redis_health() -> dict
def get_table_row_counts(session) -> dict
def get_growth_stats(session) -> dict
def get_data_quality_metrics(session) -> dict
def get_system_info() -> dict
def generate_system_report(session) -> dict  # All stats combined
```

---

### Task 32: CSV Export for All Tables

**Files to Update:**
- `pages/3_🏢_Businesses.py` - Add CSV export
- `pages/4_🤖_Agents.py` - Add CSV export
- `pages/5_📞_Call_Logs.py` - Add CSV export
- `pages/6_💳_Billing.py` - Add CSV export
- `pages/6_⚡_Entitlements.py` - Add CSV export (if not already present)
- `pages/7_💰_Credits.py` - Add CSV export (if not already present)

**Pattern to Follow (from Users page):**
```python
# At the bottom of the page, after main content
st.divider()
if st.button("📥 Export to CSV", use_container_width=True):
    try:
        # Load data with higher limit for export
        data = load_data(search_query, filters, page=0, per_page=1000)

        # Convert to DataFrame with user-friendly column names
        df = pd.DataFrame([
            {
                "Column1": item.field1,
                "Column2": item.field2,
                # ... map all relevant fields
            }
            for item in data
        ])

        # Generate CSV
        csv = df.to_csv(index=False)

        # Download button
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"{page_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key='download-csv'
        )
    except Exception as e:
        logger.error(f"CSV export failed: {e}", exc_info=True)
        st.error(f"Failed to export: {str(e)}")
```

**CSV Column Guidelines:**
- Use human-readable column names (not database field names)
- Include relevant fields only (no internal IDs unless useful)
- Format dates as ISO 8601 strings
- Format currency with currency symbol
- Include status/type as readable strings
- Limit to 1000 rows max with warning if truncated

---

### Task 33: Auto-refresh for Dashboard

**File to Update:**
- `pages/1_📊_Dashboard.py`

**Current Implementation Issue:**
```python
# Current code just reruns immediately - not useful
auto_refresh = st.checkbox("Auto-refresh (60s)", value=False)
if auto_refresh:
    st.rerun()  # This runs infinitely!
```

**Improved Implementation:**
```python
import time

# At the top of the page, after title
col1, col2 = st.columns([3, 1])
with col2:
    auto_refresh = st.checkbox("Auto-refresh (60s)", value=False)

# Load and display dashboard data
data = load_dashboard_data()
# ... render all dashboard components ...

# Auto-refresh logic at the bottom
if auto_refresh:
    # Create a placeholder for countdown
    countdown_placeholder = st.empty()

    for remaining in range(60, 0, -1):
        countdown_placeholder.info(f"🔄 Refreshing in {remaining} seconds...")
        time.sleep(1)

    # Clear cache and rerun
    st.cache_data.clear()
    st.rerun()

# Last updated timestamp
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
```

**Note:** Streamlit's execution model means the countdown will block, but that's acceptable for a 60s refresh. Alternative approach using `st.empty()` and manual countdown could work better.

---

### Task 34: Manual Refresh Buttons

**Files to Update (add if missing):**
- `pages/3_🏢_Businesses.py`
- `pages/4_🤖_Agents.py`
- `pages/5_📞_Call_Logs.py`
- `pages/6_💳_Billing.py`
- `pages/6_⚡_Entitlements.py`
- `pages/7_💰_Credits.py`

**Implementation Pattern:**
```python
# Near the top of the page, in the filter row
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
with col1:
    search_query = st.text_input("🔍 Search...", ...)
with col2:
    filter1 = st.selectbox("Filter 1", ...)
with col3:
    filter2 = st.selectbox("Filter 2", ...)
with col4:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
```

**Alternative: Use a button at the bottom (if top is too cluttered):**
```python
# At the bottom of the page
st.divider()
col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col2:
    if st.button("📥 Export to CSV", use_container_width=True):
        # Export logic
```

---

### Task 35: Error Handling Enhancement

**All Pages to Update:**
- Every page with database operations
- Every page with user input forms

**Error Handling Principles:**

1. **Database Operation Errors:**
```python
try:
    with get_session() as session:
        data = service.get_data(session, ...)

        if not data:
            st.info("No data found matching your criteria")
        else:
            # Display data

except ValueError as e:
    # User input validation errors
    st.error(f"❌ Invalid input: {str(e)}")

except ConnectionError as e:
    # Database connection errors
    st.error("❌ Database connection failed. Please try again or contact support.")
    logger.error(f"Database connection error: {e}", exc_info=True)

except Exception as e:
    # Catch-all for unexpected errors
    st.error("❌ An unexpected error occurred. Please try again or contact support.")
    logger.error(f"Unexpected error in {page_name}: {e}", exc_info=True)
```

2. **Form Validation:**
```python
# Before submitting a form
if not user_id:
    st.error("❌ Please select a user first")
    st.stop()

if not reason or len(reason.strip()) < 10:
    st.error("❌ Reason must be at least 10 characters")
    st.stop()

if amount == 0:
    st.error("❌ Amount cannot be zero")
    st.stop()
```

3. **Null/Empty Data Handling:**
```python
# Instead of:
st.write(user.full_name)

# Do:
st.write(user.full_name or "N/A")

# Or use formatters:
from utils.formatters import format_datetime
st.write(format_datetime(user.created_at))  # Returns "N/A" if None
```

4. **Loading States:**
```python
with st.spinner("Loading data..."):
    data = load_expensive_data()
```

5. **User-Friendly Error Messages:**
```python
# Bad:
st.error("NoneType object has no attribute 'email'")

# Good:
st.error("❌ User data is incomplete. Please contact support.")
```

---

### Task 36: Query Optimization

**Service Files to Review:**
- All files in `services/admin-board/services/`

**Optimization Checklist:**

1. **Always Use Pagination:**
```python
def get_items(session, limit=50, offset=0, ...):
    # Always include limit/offset
    query = session.query(Model).limit(limit).offset(offset)
    return query.all()
```

2. **Avoid N+1 Queries with Eager Loading:**
```python
# Bad (N+1 query):
users = session.query(User).all()
for user in users:
    business = user.business  # Triggers a query each time!

# Good (eager loading):
from sqlalchemy.orm import joinedload
users = session.query(User).options(joinedload(User.business)).all()
```

3. **Use Proper Indexing:**
Document which columns should be indexed in `QUERY_OPTIMIZATION.md`:
- User: email (unique), stripe_customer_id, is_active
- Business: user_id
- CallLog: user_id, business_id, created_at, status
- Appointment: user_id, start_time, status
- CreditTransaction: user_id, created_at
- PromotionCodeUsage: user_id, promotion_code_id, created_at

4. **Count Queries Optimization:**
```python
# Instead of loading all and counting:
# users = session.query(User).all()
# count = len(users)

# Do:
from sqlalchemy import func
count = session.query(func.count(User.id)).scalar()
```

5. **Selective Column Loading:**
```python
# If you only need a few columns:
users = session.query(User.id, User.email, User.full_name).all()
# Instead of loading entire User objects
```

6. **Query Result Caching:**
```python
# Use Streamlit's caching effectively
@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_dashboard_data():
    with get_session() as session:
        return get_stats(session)
```

7. **Limit Search Results:**
```python
# For search/autocomplete, limit results
def search_users(session, query, limit=20):
    # Only return first 20 matches
    pass
```

**Create Documentation:**
`services/admin-board/docs/QUERY_OPTIMIZATION.md`:
```markdown
# Query Optimization Guide

## Recommended Indexes
[List all recommended indexes with rationale]

## Query Patterns
[Document common query patterns and their performance]

## Performance Benchmarks
[Record typical response times for each service method]

## Common Pitfalls
[Document N+1 issues and how to avoid them]
```

---

## Testing Checklist

### New Pages Testing:
- [ ] **Promotions Page (8_🎟️_Promotions.py)**
  - [ ] Promotion codes list loads
  - [ ] Search by code works
  - [ ] Detail panel shows usage history
  - [ ] Links to user details work
  - [ ] CSV export generates correct data

- [ ] **Appointments Page (9_📅_Appointments.py)**
  - [ ] Appointments list loads with all columns
  - [ ] Date range filter works
  - [ ] Status filter works
  - [ ] Booking source filter works
  - [ ] Detail panel shows all info
  - [ ] Links to user/business/call log work
  - [ ] CSV export includes all relevant fields

- [ ] **System Page (10_🔧_System.py)**
  - [ ] Database health check works
  - [ ] All table counts are accurate
  - [ ] Growth stats calculate correctly
  - [ ] System info displays properly
  - [ ] Clear cache button works
  - [ ] System report export works

### CSV Export Testing:
- [ ] Users page export works
- [ ] Businesses page export works
- [ ] Agents page export works
- [ ] Call Logs page export works
- [ ] Billing page export works
- [ ] Entitlements page export works
- [ ] Credits page export works
- [ ] Promotions page export works
- [ ] Appointments page export works
- [ ] CSV files open correctly in Excel/Sheets
- [ ] All columns have readable names
- [ ] Dates are formatted as ISO 8601
- [ ] Currency values include symbols

### Refresh Functionality Testing:
- [ ] Dashboard auto-refresh works (60s countdown)
- [ ] Dashboard auto-refresh can be toggled off
- [ ] All pages have manual refresh button
- [ ] Manual refresh clears cache
- [ ] Manual refresh reloads current data

### Error Handling Testing:
- [ ] Database connection errors show friendly message
- [ ] Invalid search queries are handled gracefully
- [ ] Empty results show appropriate info message
- [ ] Form validation catches invalid inputs
- [ ] Null/None values display as "N/A"
- [ ] Errors are logged with proper context

### Query Optimization Testing:
- [ ] All paginated queries use limit/offset
- [ ] No N+1 queries in table views
- [ ] Count queries use COUNT(*) not len()
- [ ] Search queries return quickly (<1s)
- [ ] Dashboard loads in <2s
- [ ] Detail panels load in <500ms

---

## File Structure

### New Files to Create:
```
services/admin-board/
├── docs/
│   ├── IMPLEMENTATION_PLAN.md           (existing)
│   ├── PHASE_4_IMPLEMENTATION_PLAN.md   (this document)
│   └── QUERY_OPTIMIZATION.md            (NEW - Task 36)
├── pages/
│   ├── 1_📊_Dashboard.py                (update - Task 33)
│   ├── 2_👥_Users.py                     (existing, has CSV)
│   ├── 3_🏢_Businesses.py                (update - Task 32, 34)
│   ├── 4_🤖_Agents.py                    (update - Task 32, 34)
│   ├── 5_📞_Call_Logs.py                 (update - Task 32, 34)
│   ├── 6_💳_Billing.py                   (update - Task 32, 34)
│   ├── 6_⚡_Entitlements.py              (update - Task 32, 34, 35)
│   ├── 7_💰_Credits.py                   (update - Task 32, 34, 35)
│   ├── 8_🎟️_Promotions.py                (NEW - Task 29)
│   ├── 9_📅_Appointments.py              (NEW - Task 30)
│   └── 10_🔧_System.py                   (NEW - Task 31)
└── services/
    ├── user_service.py                  (existing)
    ├── business_service.py              (existing)
    ├── agent_service.py                 (existing)
    ├── call_log_service.py              (existing)
    ├── billing_service.py               (existing)
    ├── entitlement_service.py           (existing)
    ├── credit_service.py                (existing)
    ├── audit_service.py                 (existing)
    ├── promotion_service.py             (NEW - Task 29)
    ├── appointment_service.py           (NEW - Task 30)
    └── system_service.py                (NEW - Task 31)
```

---

## Estimated Timeline: 2-3 Days

### Day 1:
**Morning (4 hours):**
- Task 29: Build Promotions page (2.5 hours)
  - Create promotion_service.py (1 hour)
  - Create 8_🎟️_Promotions.py (1.5 hours)
- Task 30: Build Appointments page (1.5 hours)
  - Create appointment_service.py (0.5 hours)
  - Create 9_📅_Appointments.py (1 hour)

**Afternoon (4 hours):**
- Task 31: Build System page (2 hours)
  - Create system_service.py (1 hour)
  - Create 10_🔧_System.py (1 hour)
- Task 32: CSV exports (2 hours)
  - Add to all 6 existing pages

### Day 2:
**Morning (4 hours):**
- Task 33: Auto-refresh Dashboard (0.5 hours)
- Task 34: Manual refresh buttons (0.5 hours)
- Task 35: Error handling enhancement (3 hours)
  - Review and update all 10 pages

**Afternoon (4 hours):**
- Task 36: Query optimization (2 hours)
  - Review all services
  - Create QUERY_OPTIMIZATION.md
- Testing: New pages (2 hours)

### Day 3:
**Full Day (6-8 hours):**
- Testing: All features (4 hours)
  - CSV exports
  - Refresh functionality
  - Error handling
  - Query performance
- Bug fixes and refinements (2-4 hours)
- Documentation updates (1 hour)

---

## Dependencies

### Web-Backend:
- ✅ Models: PromotionCode, PromotionCodeUsage (already exist)
- ✅ Models: Appointment, AppointmentEndUser (already exist)
- ✅ CRUD: crud_promotion_code.py (already exists)
- ✅ CRUD: crud_appointment_sync.py (already exists)

### Admin-Board:
- ✅ Service pattern established (Phase 1-3)
- ✅ Components: cards, tables, charts (already exist)
- ✅ Utils: formatters (already exist)
- ✅ Database connection utilities (already exist)
- ✅ Authentication system (already exists)

### External:
- PostgreSQL database (staging)
- No external API calls required for Phase 4

---

## Success Criteria

Phase 4 is complete when:
1. ✅ All 3 new pages (Promotions, Appointments, System) are functional
2. ✅ All 10 pages have CSV export functionality
3. ✅ Dashboard has working auto-refresh (60s)
4. ✅ All pages have manual refresh buttons
5. ✅ Comprehensive error handling on all pages
6. ✅ Query optimization implemented and documented
7. ✅ All tests pass
8. ✅ No performance regressions
9. ✅ Documentation is complete

---

## Notes

- This phase focuses entirely on **read-only** features
- No write operations (except audit logging from Phase 3)
- CSV exports limited to 1000 rows to prevent performance issues
- Auto-refresh only on Dashboard to avoid disrupting user workflows
- Error messages should be user-friendly, with technical details logged
- Query optimization is critical - staging database may have limited resources

---

## Next Steps (Phase 5)

After Phase 4 completion, Phase 5 will focus on deployment:
- Dockerfile creation
- Kubernetes manifests
- Digital Ocean registry push
- DNS configuration
- SSL setup
- End-to-end testing in staging

See original `IMPLEMENTATION_PLAN.md` for Phase 5 details.
