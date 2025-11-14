# Odoo Integration Plan for Cold Call Dialer

## Document Information
- **Created**: 2025-11-13
- **Status**: Planning Phase
- **Owner**: Admin Board Team
- **Related Feature**: Cold Call Dialer (16_📞_Cold_Call_Dialer.py)

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Research Findings](#research-findings)
3. [Implementation Plan](#implementation-plan)
4. [Technical Details](#technical-details)
5. [Future Improvements](#future-improvements)
6. [Appendix: Code Examples](#appendix-code-examples)

---

## Executive Summary

### Objective
Integrate the Admin Board's Cold Call Dialer with Odoo CRM to:
1. Load contacts from Odoo saved searches/filters
2. Use Odoo's custom `x_cold_call_status` field for call outcomes
3. Save call notes to Odoo contact activity log

### Key Benefits
- Eliminate manual CSV uploads
- Maintain single source of truth in Odoo
- Full audit trail of all calls in CRM
- Dynamic status options that stay in sync with Odoo
- Faster access in production via internal VPC

### Research Conclusion
All three integration points are **fully supported** by Odoo's JSON-RPC API:
- ✅ Load presaved searches via `ir.filters` model
- ✅ Dynamic status field via `fields_get()` and `write()`
- ✅ Activity logging via `message_post()` method

---

## Research Findings

### 1. Loading Presaved Searches from Odoo

**Answer: YES - Via `ir.filters` Model**

Odoo stores all favorite/saved searches in the `ir.filters` model. The screenshots show filters like "d2d-251101-4" which are user-created saved searches.

**How It Works:**
```python
# Step 1: Get list of available favorite filters
filters = odoo_client.search_read(
    'ir.filters',
    domain=[
        ('model_id', '=', 'res.partner'),  # Contact model
        ('user_id', 'in', [uid, False])    # User's filters + shared
    ],
    fields=['id', 'name', 'domain', 'context', 'sort']
)

# Step 2: Parse selected filter's domain and load contacts
import ast
domain = ast.literal_eval(filters[0]['domain'])
contacts = odoo_client.search_read(
    'res.partner',
    domain=domain,
    fields=['id', 'name', 'phone', 'company_name', 'function', 'x_cold_call_status'],
    limit=50,
    offset=0
)
```

**Key Fields:**
- `name`: Filter display name (e.g., "d2d-251101-4")
- `domain`: Search criteria as Python list (stored as string)
- `model_id`: Always 'res.partner' for contacts
- `user_id`: False = shared with all users

---

### 2. Custom Field `x_cold_call_status`

**Answer: YES - Read Definition & Update Values via API**

The screenshot shows a custom selection field with predefined values like:
- "No Answer - No Voicemail"
- "No Answer - Voicemail Left"
- "Connected - Not Interested"
- "Gatekeeper Block"
- "Meeting Booked"
- "Dead / Do Not Call"
- etc.

**How to Read Field Definition:**
```python
# Get field metadata including selection options
field_info = odoo_client.execute_kw(
    'res.partner',
    'fields_get',
    [],
    {'allfields': ['x_cold_call_status']}
)

# Extract selection options
selection = field_info['x_cold_call_status']['selection']
# Returns: [('value', 'Display Name'), ('value2', 'Display Name 2'), ...]

# Example result:
# [
#   ('no_answer_no_voicemail', 'No Answer - No Voicemail'),
#   ('no_answer_voicemail', 'No Answer - Voicemail Left'),
#   ('connected_not_interested', 'Connected - Not Interested'),
#   ('gatekeeper_block', 'Gatekeeper Block'),
#   ('meeting_booked', 'Meeting Booked'),
#   ('dead_dnc', 'Dead / Do Not Call'),
#   ...
# ]
```

**How to Update Field:**
```python
# Update contact's status (use VALUE, not display name)
odoo_client.write(
    'res.partner',
    [contact_id],
    {'x_cold_call_status': 'meeting_booked'}  # Use the value
)
```

**Critical Implementation Detail:**
- **Store TWO mappings:**
  - `value_to_name = {'meeting_booked': 'Meeting Booked', ...}` - for UI display
  - `name_to_value = {'Meeting Booked': 'meeting_booked', ...}` - for Odoo updates
- **Display**: Show the name in dropdown
- **Update**: Send the value to Odoo

---

### 3. Saving Notes to Odoo Contact Log

**Answer: YES - Use `message_post()` Method**

The screenshot shows Odoo's "Log note" tab where internal notes appear. This uses Odoo's mail/chatter system.

**Recommended Method: `message_post()`**
```python
# Create internal note on contact
odoo_client.execute_kw(
    'res.partner',
    'message_post',
    [contact_id],
    {
        'body': '<p><strong>Cold Call - Meeting Booked</strong></p>'
                '<p>Duration: 180s</p>'
                '<p>Timestamp: 2025-01-13 14:30:00</p>'
                '<p>Notes: Very interested in our services...</p>',
        'message_type': 'comment'  # Creates internal note
    }
)
```

**Where Notes Appear:**
- In the contact's "Log note" tab
- Same location as manual Odoo notes
- Visible to all users with contact access
- Full audit trail with timestamp and author

**Note Format:**
- Accepts HTML for formatting
- Can include call metadata (outcome, duration, timestamp)
- Automatically tracks who created the note
- Immutable (can't be edited after creation)

---

## Implementation Plan

### Phase 1: Setup Odoo Client in Admin-Board

**Tasks:**
1. Copy existing Odoo client code:
   - Source: `services/nextjs-frontend/docs/marketing/scripts/odoo_upload/lib/`
   - Destination: `services/admin-board/lib/`
   - Files: `odoo_client.py`, `rate_limiter.py`, and dependencies

2. Add environment variables:
   ```bash
   # In .env file
   ODOO_URL=https://odoo.julya.ai  # Local/testing (public URL)
   ODOO_DB=odoo
   ODOO_USERNAME=admin
   ODOO_PASSWORD=<password>
   ```

3. Production configuration:
   - Use internal VPC URL for faster access
   - Example: `ODOO_URL=http://odoo.aicallgo-internal.svc.cluster.local`
   - Avoids routing through public internet and back
   - Update Kubernetes deployment manifests with environment-specific URLs

4. Create helper module:
   - File: `services/admin-board/components/cold_call/odoo_integration.py`
   - Functions: `get_odoo_client()`, `load_filters()`, `load_contacts()`, etc.

**Deliverables:**
- ✅ Working Odoo client in admin-board
- ✅ Environment-specific URL configuration
- ✅ Helper functions ready for use

---

### Phase 2: Load Contacts from Odoo Filters (with Pagination)

**Tasks:**
1. Add UI option "Load from Odoo Filter" to contact upload screen

2. Fetch available filters:
   ```python
   def get_available_filters():
       client = get_odoo_client()
       filters = client.search_read(
           'ir.filters',
           domain=[
               ('model_id', '=', 'res.partner'),
               ('user_id', 'in', [client.uid, False])
           ],
           fields=['id', 'name', 'domain'],
           order='name asc'
       )
       return filters
   ```

3. Display filter selection dropdown:
   - Show filter names (e.g., "d2d-251101-4", "Hot Leads")
   - Add filter preview (show first 5 contacts)
   - Display total count

4. Implement pagination:
   ```python
   def load_contacts_paginated(filter_id, page=1, page_size=50):
       # Get filter domain
       filter_record = client.read('ir.filters', [filter_id], ['domain'])[0]
       domain = ast.literal_eval(filter_record['domain'])

       # Get total count
       total = client.search_count('res.partner', domain=domain)

       # Calculate pagination
       offset = (page - 1) * page_size
       total_pages = math.ceil(total / page_size)

       # Load page of contacts
       contacts = client.search_read(
           'res.partner',
           domain=domain,
           fields=['id', 'name', 'phone', 'company_name', 'function', 'x_cold_call_status'],
           limit=page_size,
           offset=offset,
           order='name asc'
       )

       return {
           'contacts': contacts,
           'page': page,
           'page_size': page_size,
           'total': total,
           'total_pages': total_pages
       }
   ```

5. Pagination UI controls:
   - Page size selector: 25, 50, 100, 200
   - Current page indicator: "Page 2 of 7 (347 total contacts)"
   - Navigation: Previous, Next, First, Last buttons
   - "Load All" option with warning for large lists
   - Loading progress bar for batch operations

6. Store Odoo contact IDs:
   - Add `odoo_id` field to contact records in session state
   - Required for updating contacts after calls

**Deliverables:**
- ✅ Filter selection dropdown
- ✅ Paginated contact loading
- ✅ Progress indicators
- ✅ Odoo IDs tracked for each contact

**Pagination Rationale:**
- Filters may contain 100+ or even 1000+ contacts
- Loading all at once causes:
  - Long initial wait times
  - High memory usage
  - Poor user experience
- Pagination provides:
  - Fast initial load
  - Responsive UI
  - Ability to start calling immediately
  - Progressive loading as needed

---

### Phase 3: Dynamic Call Status Integration

**Tasks:**
1. On app startup, fetch field definition:
   ```python
   def load_call_status_options():
       client = get_odoo_client()
       field_info = client.execute_kw(
           'res.partner',
           'fields_get',
           [],
           {'allfields': ['x_cold_call_status']}
       )

       if 'x_cold_call_status' in field_info:
           selection = field_info['x_cold_call_status']['selection']
           # selection = [('value', 'Name'), ...]

           # Create bidirectional mappings
           value_to_name = dict(selection)
           name_to_value = {name: value for value, name in selection}

           return {
               'options': selection,
               'value_to_name': value_to_name,
               'name_to_value': name_to_value
           }
       else:
           # Fallback if field doesn't exist
           return None
   ```

2. Build dynamic status dropdown:
   - Display names in dropdown (e.g., "Meeting Booked")
   - Store value-name mapping in session state
   - No hardcoded status options

3. Handle status selection:
   ```python
   # User selects from dropdown (sees display name)
   selected_name = "Meeting Booked"

   # Convert to value for Odoo update
   selected_value = name_to_value[selected_name]  # "meeting_booked"
   ```

4. Update Odoo after call:
   ```python
   def update_call_status(contact_odoo_id, status_value):
       client = get_odoo_client()
       client.write(
           'res.partner',
           [contact_odoo_id],
           {'x_cold_call_status': status_value}  # Use VALUE
       )
   ```

5. Error handling:
   - If `x_cold_call_status` field doesn't exist, fallback to notes-only
   - If field exists but no selection options, log warning
   - Validate selected value exists before updating

**Deliverables:**
- ✅ Dynamic status dropdown always in sync with Odoo
- ✅ Proper value/name mapping
- ✅ Graceful fallback if field missing
- ✅ No hardcoded status values

**Benefits:**
- If Odoo admin adds new status options, they appear automatically
- No code changes needed when statuses change
- Consistent with Odoo UI

---

### Phase 4: Save Call Notes to Odoo

**Tasks:**
1. After call ends, collect data:
   - Call outcome (from status dropdown)
   - Duration (in seconds)
   - User notes (text input)
   - Timestamp (auto-generated)

2. Format note as HTML:
   ```python
   def create_call_note(outcome_name, duration, notes, timestamp):
       return f"""
       <p><strong>Cold Call - {outcome_name}</strong></p>
       <p><strong>Duration:</strong> {duration}s ({duration // 60}m {duration % 60}s)</p>
       <p><strong>Timestamp:</strong> {timestamp}</p>
       <hr/>
       <p>{notes}</p>
       """
   ```

3. Send to Odoo:
   ```python
   def save_call_note(contact_odoo_id, outcome_name, duration, notes):
       client = get_odoo_client()

       timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
       body = create_call_note(outcome_name, duration, notes, timestamp)

       client.execute_kw(
           'res.partner',
           'message_post',
           [contact_odoo_id],
           {
               'body': body,
               'message_type': 'comment'
           }
       )
   ```

4. Complete post-call flow:
   ```python
   def complete_call(contact_odoo_id, status_value, status_name, duration, notes):
       # Update status field
       update_call_status(contact_odoo_id, status_value)

       # Create activity note
       save_call_note(contact_odoo_id, status_name, duration, notes)

       return True
   ```

5. UI feedback:
   - Show "Saving to Odoo..." spinner
   - Success: "✓ Saved to Odoo"
   - Error: Show error message, allow retry

**Deliverables:**
- ✅ Call notes saved to Odoo contact log
- ✅ Notes appear in same location as manual Odoo notes
- ✅ Full call metadata captured
- ✅ Error handling and retry logic

---

## Technical Details

### Architecture

```
Admin Board (Streamlit)
    ↓
odoo_integration.py (Helper Module)
    ↓
lib/odoo_client.py (JSON-RPC Client)
    ↓
ODOO_URL (Environment Variable)
    ↓
┌─────────────────────────────────┐
│ Local/Testing:                  │
│ https://odoo.julya.ai (public)  │
└─────────────────────────────────┘
┌─────────────────────────────────┐
│ Production:                     │
│ http://odoo.internal (VPC)      │
│ Faster, no public routing       │
└─────────────────────────────────┘
    ↓
Odoo CRM (JSON-RPC API)
```

### API Methods Used

| Operation | Odoo Model | Method | Purpose |
|-----------|------------|--------|---------|
| List filters | `ir.filters` | `search_read()` | Get saved searches |
| Count contacts | `res.partner` | `search_count()` | Total for pagination |
| Load contacts | `res.partner` | `search_read()` | Get contact data |
| Get field def | `res.partner` | `fields_get()` | Status options |
| Update status | `res.partner` | `write()` | Set call outcome |
| Save note | `res.partner` | `message_post()` | Log activity |

### Data Flow

```
1. User selects Odoo filter
   ↓
2. Fetch filter domain from ir.filters
   ↓
3. Count total contacts (pagination)
   ↓
4. Load first page of contacts
   ↓
5. User makes calls
   ↓
6. After each call:
   - User selects status (display name)
   - Convert to value
   - Update x_cold_call_status field
   - Create internal note with message_post
   ↓
7. Notes appear in Odoo contact log
```

### Session State Structure

```python
st.session_state.odoo_config = {
    'status_options': [
        ('meeting_booked', 'Meeting Booked'),
        ('connected_interested', 'Connected - Interested'),
        ...
    ],
    'value_to_name': {...},
    'name_to_value': {...}
}

st.session_state.contacts = [
    {
        'odoo_id': 12345,
        'name': 'John Doe',
        'phone': '+1234567890',
        'company': 'Acme Corp',
        'title': 'CEO',
        'status': 'pending',
        'notes': '',
        'call_outcome': ''
    },
    ...
]

st.session_state.pagination = {
    'current_page': 1,
    'page_size': 50,
    'total_contacts': 347,
    'total_pages': 7,
    'filter_id': 123,
    'filter_name': 'd2d-251101-4'
}
```

### Error Handling

**Network Errors:**
- Retry logic with exponential backoff
- Show error messages to user
- Allow manual retry
- Fallback to local-only mode if Odoo unavailable

**Field Missing:**
- Check if `x_cold_call_status` exists before using
- Graceful degradation to notes-only if missing
- Log warning for admin review

**Rate Limiting:**
- Existing RateLimiter class handles 120 req/min limit
- Batch operations where possible
- Show "Rate limit reached, waiting..." message

**Invalid Data:**
- Validate phone numbers before loading
- Filter out contacts without phone numbers
- Show warnings for incomplete data

---

## Future Improvements

### Priority 1: Enhanced User Experience

#### Scheduled Activities for Follow-ups
**Objective:** Automatically create Odoo activities for callbacks and interested leads

**Implementation:**
```python
def create_followup_activity(contact_id, outcome_value, notes):
    if outcome_value in ['callback_requested', 'connected_interested']:
        client = get_odoo_client()

        # Get "Call" activity type
        activity_type = client.search_read(
            'mail.activity.type',
            domain=[('name', '=', 'Call')],
            fields=['id'],
            limit=1
        )

        if activity_type:
            # Create activity due in 7 days
            client.create(
                'mail.activity',
                {
                    'res_model': 'res.partner',
                    'res_id': contact_id,
                    'activity_type_id': activity_type[0]['id'],
                    'summary': 'Follow up from cold call',
                    'note': f'Previous outcome: {outcome_name}\n{notes}',
                    'user_id': client.uid,
                    'date_deadline': (datetime.now() + timedelta(days=7)).date().isoformat()
                }
            )
```

**Benefits:**
- Automatic reminder in Odoo for follow-ups
- Appears in user's activity calendar
- Can reassign to other team members
- Tracks lead nurturing workflow

**UI Changes:**
- Checkbox: "Create follow-up activity" (auto-checked for certain outcomes)
- Date picker: "Follow-up date" (default: +7 days)
- User selector: "Assign to" (default: current user)

---

### Priority 2: Two-Way Sync

#### Sync Status Updates from Odoo
**Objective:** Reflect changes made in Odoo back to admin-board

**Implementation:**
```python
def refresh_contact_statuses(odoo_ids):
    """Refresh status for contacts in current session"""
    client = get_odoo_client()

    contacts = client.read(
        'res.partner',
        odoo_ids,
        ['id', 'x_cold_call_status', 'write_date']
    )

    for contact in contacts:
        # Update session state if changed
        if contact['write_date'] > last_refresh:
            update_local_contact(contact)
```

**Use Cases:**
- Multiple team members calling same list
- Changes made in Odoo appear in dialer
- Avoid duplicate calls

**UI:**
- "Refresh from Odoo" button
- Auto-refresh every 5 minutes
- Show "(Updated in Odoo)" indicator

---

### Priority 3: Advanced Features

#### Call Recording Integration
**Objective:** Link call recordings to Odoo notes

**Implementation:**
- Upload recording file to Odoo
- Attach to contact using `ir.attachment` model
- Link attachment to activity note

#### Call Analytics Dashboard
**Objective:** Track performance metrics

**Metrics:**
- Calls per hour/day
- Conversion rates by status
- Average call duration
- Best performing filters/campaigns

**Implementation:**
- Query Odoo for historical call notes
- Parse outcomes from notes/status field
- Generate charts and reports

#### Bulk Operations
**Objective:** Mass actions on contact lists

**Features:**
- Bulk status updates
- Bulk tag assignment
- Export call results to CSV
- Mass create activities

#### Smart Filters
**Objective:** Enhance filter capabilities

**Features:**
- Create new filters from dialer
- Save current filter with modifications
- Quick filters: "Never called", "Callbacks due", "Hot leads"

#### Voice Notes Transcription
**Objective:** Auto-transcribe voice notes to text

**Implementation:**
- Record voice note after call
- Transcribe using speech-to-text API
- Save transcription to Odoo note

---

### Priority 4: Integration Enhancements

#### CRM Pipeline Integration
**Objective:** Move contacts through sales pipeline

**Implementation:**
- Create opportunities from "Connected - Interested"
- Link opportunity to contact
- Set initial stage based on outcome

#### Calendar Integration
**Objective:** Book meetings directly

**Implementation:**
- If outcome is "Meeting Booked"
- Show calendar picker
- Create calendar event in Odoo
- Send invite to contact

#### Email Integration
**Objective:** Send follow-up emails

**Implementation:**
- After call, option to send email
- Use Odoo email templates
- Track email opens/clicks
- Link email to activity log

---

### Priority 5: Performance Optimizations

#### Caching Strategy
**Objective:** Reduce API calls

**Implementation:**
- Cache filter list (TTL: 1 hour)
- Cache field definitions (TTL: 24 hours)
- Cache contact data (refresh on demand)

#### Batch Operations
**Objective:** Reduce API overhead

**Implementation:**
- Batch status updates (every 5 contacts)
- Batch note creation
- Background sync queue

#### Offline Mode
**Objective:** Work without internet

**Implementation:**
- Local SQLite cache
- Sync when connection restored
- Conflict resolution

---

## Appendix: Code Examples

### Complete Odoo Integration Module

```python
# services/admin-board/components/cold_call/odoo_integration.py

import os
import ast
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import sys

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lib'))
from odoo_client import OdooClient

class OdooIntegration:
    """Handles all Odoo CRM integration for cold calling"""

    def __init__(self):
        self.client = None
        self.status_mapping = None
        self._initialize_client()
        self._load_field_definitions()

    def _initialize_client(self):
        """Initialize Odoo client with environment config"""
        self.client = OdooClient(
            url=os.getenv('ODOO_URL', 'https://odoo.julya.ai'),
            db=os.getenv('ODOO_DB', 'odoo'),
            username=os.getenv('ODOO_USERNAME'),
            password=os.getenv('ODOO_PASSWORD')
        )
        self.client.authenticate()

    def _load_field_definitions(self):
        """Load x_cold_call_status field definition"""
        try:
            field_info = self.client.execute_kw(
                'res.partner',
                'fields_get',
                [],
                {'allfields': ['x_cold_call_status']}
            )

            if 'x_cold_call_status' in field_info:
                selection = field_info['x_cold_call_status']['selection']

                self.status_mapping = {
                    'options': selection,  # [('value', 'Name'), ...]
                    'value_to_name': dict(selection),
                    'name_to_value': {name: value for value, name in selection}
                }
            else:
                print("Warning: x_cold_call_status field not found in Odoo")
                self.status_mapping = None

        except Exception as e:
            print(f"Error loading field definitions: {e}")
            self.status_mapping = None

    def get_available_filters(self) -> List[Dict]:
        """Get list of available contact filters"""
        filters = self.client.search_read(
            'ir.filters',
            domain=[
                ('model_id', '=', 'res.partner'),
                ('user_id', 'in', [self.client.uid, False])
            ],
            fields=['id', 'name', 'domain', 'context'],
            order='name asc'
        )
        return filters

    def get_filter_contact_count(self, filter_id: int) -> int:
        """Get total number of contacts in a filter"""
        filter_record = self.client.read('ir.filters', [filter_id], ['domain'])[0]
        domain = ast.literal_eval(filter_record['domain'])
        count = self.client.search_count('res.partner', domain=domain)
        return count

    def load_contacts_from_filter(
        self,
        filter_id: int,
        page: int = 1,
        page_size: int = 50
    ) -> Dict:
        """Load contacts from filter with pagination"""

        # Get filter domain
        filter_record = self.client.read('ir.filters', [filter_id], ['domain', 'name'])[0]
        domain = ast.literal_eval(filter_record['domain'])

        # Get total count
        total = self.client.search_count('res.partner', domain=domain)

        # Calculate pagination
        offset = (page - 1) * page_size
        total_pages = math.ceil(total / page_size)

        # Load contacts
        contacts = self.client.search_read(
            'res.partner',
            domain=domain,
            fields=[
                'id', 'name', 'phone', 'mobile',
                'company_name', 'function', 'x_cold_call_status'
            ],
            limit=page_size,
            offset=offset,
            order='name asc'
        )

        # Format for admin-board
        formatted_contacts = []
        for c in contacts:
            # Prefer mobile over phone
            phone = c.get('mobile') or c.get('phone') or ''

            # Skip contacts without phone
            if not phone:
                continue

            formatted_contacts.append({
                'odoo_id': c['id'],
                'name': c.get('name', ''),
                'company': c.get('company_name', ''),
                'phone': phone,
                'title': c.get('function', ''),
                'status': 'pending',
                'notes': '',
                'call_outcome': '',
                'current_odoo_status': c.get('x_cold_call_status', '')
            })

        return {
            'contacts': formatted_contacts,
            'filter_name': filter_record['name'],
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': total_pages
        }

    def get_status_options(self) -> Optional[List[Tuple[str, str]]]:
        """Get available call status options"""
        if self.status_mapping:
            return self.status_mapping['options']
        return None

    def get_status_display_names(self) -> List[str]:
        """Get list of status display names for dropdown"""
        if self.status_mapping:
            return [name for _, name in self.status_mapping['options']]
        return []

    def status_name_to_value(self, name: str) -> str:
        """Convert display name to Odoo value"""
        if self.status_mapping:
            return self.status_mapping['name_to_value'].get(name, '')
        return ''

    def status_value_to_name(self, value: str) -> str:
        """Convert Odoo value to display name"""
        if self.status_mapping:
            return self.status_mapping['value_to_name'].get(value, '')
        return ''

    def update_contact_status(self, odoo_id: int, status_value: str):
        """Update contact's cold call status"""
        self.client.write(
            'res.partner',
            [odoo_id],
            {'x_cold_call_status': status_value}
        )

    def create_call_note(
        self,
        odoo_id: int,
        outcome_name: str,
        duration: int,
        notes: str
    ):
        """Create internal note on contact"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Format duration
        minutes = duration // 60
        seconds = duration % 60
        duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

        # Build HTML note
        body = f"""
        <p><strong>Cold Call - {outcome_name}</strong></p>
        <p><strong>Duration:</strong> {duration_str}</p>
        <p><strong>Timestamp:</strong> {timestamp}</p>
        <hr/>
        <p>{notes if notes else '<i>No notes</i>'}</p>
        """

        # Create note
        self.client.execute_kw(
            'res.partner',
            'message_post',
            [odoo_id],
            {
                'body': body,
                'message_type': 'comment'
            }
        )

    def complete_call(
        self,
        odoo_id: int,
        status_name: str,
        duration: int,
        notes: str
    ) -> bool:
        """Complete post-call actions: update status and create note"""
        try:
            # Convert status name to value
            status_value = self.status_name_to_value(status_name)

            # Update status field
            if status_value:
                self.update_contact_status(odoo_id, status_value)

            # Create activity note
            self.create_call_note(odoo_id, status_name, duration, notes)

            return True

        except Exception as e:
            print(f"Error completing call in Odoo: {e}")
            return False
```

### Usage in Streamlit App

```python
# In 16_📞_Cold_Call_Dialer.py

import streamlit as st
from components.cold_call.odoo_integration import OdooIntegration

# Initialize
if 'odoo' not in st.session_state:
    st.session_state.odoo = OdooIntegration()

odoo = st.session_state.odoo

# Filter selection
st.subheader("Load Contacts from Odoo")

filters = odoo.get_available_filters()
filter_options = {f['name']: f['id'] for f in filters}

selected_filter_name = st.selectbox(
    "Select Odoo Filter",
    options=list(filter_options.keys())
)

if selected_filter_name:
    filter_id = filter_options[selected_filter_name]
    total_contacts = odoo.get_filter_contact_count(filter_id)

    st.info(f"This filter contains {total_contacts} contacts")

    # Pagination controls
    col1, col2 = st.columns(2)
    with col1:
        page_size = st.selectbox("Contacts per page", [25, 50, 100, 200], index=1)
    with col2:
        page = st.number_input("Page", min_value=1, value=1)

    if st.button("Load Contacts"):
        with st.spinner("Loading contacts from Odoo..."):
            result = odoo.load_contacts_from_filter(filter_id, page, page_size)
            st.session_state.contacts = result['contacts']
            st.session_state.pagination = {
                'page': result['page'],
                'total_pages': result['total_pages'],
                'total': result['total'],
                'filter_name': result['filter_name']
            }
            st.success(f"Loaded {len(result['contacts'])} contacts from '{result['filter_name']}'")

# Status selection (dynamic from Odoo)
status_options = odoo.get_status_display_names()

if status_options:
    call_outcome = st.selectbox("Call Outcome", status_options)
else:
    # Fallback
    call_outcome = st.selectbox("Call Outcome", [
        "Connected", "Voicemail", "No Answer", "Busy"
    ])

# After call ends
if st.button("Save Call Result"):
    if 'current_contact' in st.session_state:
        contact = st.session_state.current_contact

        if 'odoo_id' in contact:
            with st.spinner("Saving to Odoo..."):
                success = odoo.complete_call(
                    odoo_id=contact['odoo_id'],
                    status_name=call_outcome,
                    duration=call_duration,
                    notes=call_notes
                )

                if success:
                    st.success("✓ Saved to Odoo")
                else:
                    st.error("Failed to save to Odoo")
```

---

## Implementation Timeline

### Week 1: Foundation
- [ ] Copy Odoo client code
- [ ] Add environment variables
- [ ] Create odoo_integration.py module
- [ ] Test basic connectivity

### Week 2: Filter Loading
- [ ] Implement filter listing
- [ ] Add pagination logic
- [ ] Build filter selection UI
- [ ] Test with real filters

### Week 3: Status Integration
- [ ] Load field definitions dynamically
- [ ] Build status dropdown
- [ ] Implement status updates
- [ ] Test status synchronization

### Week 4: Notes Integration
- [ ] Implement message_post integration
- [ ] Build note formatting
- [ ] Add post-call UI
- [ ] End-to-end testing

### Week 5: Testing & Deployment
- [ ] Integration testing
- [ ] Update Kubernetes configs for VPC URL
- [ ] Deploy to staging
- [ ] User acceptance testing
- [ ] Deploy to production

---

## Success Criteria

### Functional Requirements
- ✅ Users can load contacts from Odoo saved searches
- ✅ Pagination works for large contact lists (100+)
- ✅ Call status options match Odoo field exactly
- ✅ Status updates appear in Odoo immediately
- ✅ Call notes appear in Odoo contact log
- ✅ No manual CSV uploads needed

### Performance Requirements
- ✅ Filter loading: < 2 seconds
- ✅ Contact loading (50 per page): < 3 seconds
- ✅ Status update: < 1 second
- ✅ Note creation: < 1 second
- ✅ Production VPC access faster than public URL

### Reliability Requirements
- ✅ Graceful handling of network errors
- ✅ Retry logic for failed updates
- ✅ Fallback mode if Odoo unavailable
- ✅ No data loss on connection failure

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Odoo API rate limit | High | Medium | Use existing rate limiter, batch operations |
| Network latency | Medium | Low | Use VPC URL in production, cache where possible |
| Field doesn't exist | Medium | Low | Check field existence, fallback to notes-only |
| Large filter (1000+) | Medium | Medium | Implement pagination, show warnings |
| API authentication fails | High | Low | Retry with backoff, clear error messages |
| Data sync conflicts | Low | Low | Last-write-wins, show update timestamps |

---

## References

- [Odoo External API Documentation](https://www.odoo.com/documentation/16.0/developer/api/external_api.html)
- [Odoo JSON-RPC Examples](https://www.odoo.com/documentation/16.0/developer/misc/api/odoo.html)
- [Existing Odoo Integration](../../../nextjs-frontend/docs/marketing/scripts/odoo_upload/)
- [Cold Call Dialer Implementation](../../pages/16_📞_Cold_Call_Dialer.py)

---

**Document Version**: 1.0
**Last Updated**: 2025-01-13
**Next Review**: After Phase 1 completion
