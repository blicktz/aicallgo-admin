# AICallGO Admin Board - Implementation Plan

## Table of Contents
1. [Overview](#overview)
2. [UI Organization](#ui-organization)
3. [Design System](#design-system)
4. [Technical Implementation](#technical-implementation)
5. [Priority Features](#priority-features)
6. [Kubernetes Deployment](#kubernetes-deployment)
7. [Implementation Phases](#implementation-phases)
8. [Testing Strategy](#testing-strategy)
9. [Success Metrics](#success-metrics)

---

## Overview

### Purpose
The Admin Board is a Streamlit-based administrative interface for AICallGO that provides:
- **Data Display**: Comprehensive view of users, businesses, call logs, billing, and system data
- **Data Manipulation**: Focused on entitlements and credit management
- **Direct Database Access**: Connects directly to PostgreSQL within the same Kubernetes cluster
- **Production-Ready**: Deployed as a containerized service with proper security and monitoring

### Key Principles
- **Desktop-First Design**: Optimized for 1280px+ viewports
- **Mirror Frontend Aesthetics**: Match nextjs-frontend color scheme and component styling
- **Leverage Existing Libraries**: Minimize custom code, use Streamlit components
- **Security-Focused**: Environment-based authentication, transaction safety, audit logging
- **Performance-Optimized**: Periodic refresh, query caching, connection pooling

---

## UI Organization

### Navigation Structure

**Sidebar Navigation** (250px width, always visible):
```
📊 Dashboard          - Overview metrics and recent activity
👥 Users              - User management and search
🏢 Businesses         - Business profiles and configuration
📞 Call Logs          - Call history and transcripts
💳 Billing            - Subscriptions, invoices, usage (read-only)
⚡ Entitlements       - Feature access management (PRIORITY)
💰 Credits            - Credit balances and adjustments (PRIORITY)
🎟️ Promotions         - Promotion codes tracking
📅 Appointments       - Booking management
🔧 System             - Health checks and configurations
```

---

### Page Layouts

#### 1. Dashboard Page (`1_📊_Dashboard.py`)

**Purpose**: High-level overview of system health and key metrics

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ AICallGO Admin Dashboard                    🔄 Auto-refresh │
├─────────────────────────────────────────────────────────────┤
│ KPI Cards (4 columns)                                        │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│ │ 1,247    │ │ 892      │ │ 3,421    │ │ $24,567  │       │
│ │ Users    │ │ Active   │ │ Calls    │ │ Revenue  │       │
│ │ +12 (7d) │ │ Subs     │ │ (30d)    │ │ (30d)    │       │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├─────────────────────────────────────────────────────────────┤
│ Charts (2 columns)                                           │
│ ┌─────────────────────────┐ ┌─────────────────────────┐   │
│ │ Calls Over Time (30d)   │ │ Revenue Trend (30d)     │   │
│ │ [Line Chart]            │ │ [Area Chart]            │   │
│ └─────────────────────────┘ └─────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│ Recent Activity Feed (2 columns)                             │
│ ┌─────────────────────────┐ ┌─────────────────────────┐   │
│ │ 🆕 New Signups          │ │ ⚠️ Alerts               │   │
│ │ - user@example.com      │ │ - 5 trials expiring     │   │
│ │   2 hours ago           │ │   in 24h                │   │
│ │ - another@test.com      │ │ - 2 failed payments     │   │
│ │   5 hours ago           │ │ - 1 low credit alert    │   │
│ └─────────────────────────┘ └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Features**:
- Auto-refresh every 60 seconds
- KPI cards with trend indicators (+/- change over 7 days)
- Interactive charts (hover tooltips, zoom)
- Click-through to relevant pages from alerts

**Metrics Displayed**:
- **Total Users**: Count with 7-day growth
- **Active Subscriptions**: Non-trial, active status only
- **Total Calls (30d)**: All answered calls in last 30 days
- **Revenue (30d)**: Sum of paid invoices
- **Recent Signups**: Last 10 users, ordered by created_at
- **Alerts**: Trial expirations (<24h), failed payments, low credits (<$5 equivalent)

---

#### 2. Users Page (`2_👥_Users.py`)

**Purpose**: Search, view, and manage user accounts

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ Users                                          🔄 Refresh    │
├─────────────────────────────────────────────────────────────┤
│ Search & Filters                                             │
│ ┌────────────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐  │
│ │ 🔍 Email/Name  │ │ Plan ▼   │ │ Status ▼│ │ [Search] │  │
│ └────────────────┘ └──────────┘ └─────────┘ └──────────┘  │
├─────────────────────────────────────────────────────────────┤
│ Users Table (70% width)          │ Detail Panel (30% width) │
│ ┌──────────────────────────────┐ │ ┌────────────────────┐ │
│ │ Email         │ Name  │ Plan  │ │ │ Selected User      │ │
│ │───────────────┼───────┼───────│ │ │                    │ │
│ │ user@test.com │ John  │ Pro   │ │ │ Email: user@...    │ │
│ │ jane@test.com │ Jane  │ Trial │ │ │ Plan: Professional │ │
│ │ ...           │ ...   │ ...   │ │ │ Status: Active     │ │
│ │                                │ │ │ Created: 2024-01-15│ │
│ │ [Load More]                    │ │ │                    │ │
│ └──────────────────────────────┘ │ │ Businesses (2)     │ │
│                                    │ │ - Tech Support Inc │ │
│                                    │ │ - Sales Corp       │ │
│                                    │ │                    │ │
│                                    │ │ Credit Balance     │ │
│                                    │ │ $45.50             │ │
│                                    │ │                    │ │
│                                    │ │ Quick Actions:     │ │
│                                    │ │ [Edit Entitlements]│ │
│                                    │ │ [Adjust Credits]   │ │
│                                    │ │ [View Call Logs]   │ │
│                                    │ └────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Features**:
- Real-time search (debounced 500ms)
- Multi-select filters: Plan (all/trial/professional/scale/growth), Status (all/active/inactive)
- Sortable columns: Email, Name, Plan, Created Date, Credits
- Click row to load detail panel
- Pagination: 50 users per page
- Export to CSV button

**Table Columns**:
1. Email (primary identifier, clickable)
2. Full Name
3. Plan (badge with color coding)
4. Status (active/inactive badge)
5. Created Date (formatted)
6. Credit Balance (currency format)
7. Actions (dropdown: View Details, Edit, Delete - disabled)

**Detail Panel Sections**:
- User Info: Email, Full Name, Google ID, Stripe Customer ID
- Account Status: is_active, is_superuser, onboarding_status
- Subscription: Plan, Status, Period Start/End
- Businesses: List with click-through to Business page
- Credit Balance: Total with breakdown (trial, subscription, pack, adjustment)
- Recent Activity: Last 5 call logs
- Quick Action Buttons: Link to Entitlements/Credits pages with user pre-selected

---

#### 3. Businesses Page (`3_🏢_Businesses.py`)

**Purpose**: View and search business profiles

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ Businesses                                     🔄 Refresh    │
├─────────────────────────────────────────────────────────────┤
│ Search & Filters                                             │
│ ┌──────────────────┐ ┌──────────┐ ┌──────────┐            │
│ │ 🔍 Business Name │ │ Industry ▼│ │ [Search] │            │
│ └──────────────────┘ └──────────┘ └──────────┘            │
├─────────────────────────────────────────────────────────────┤
│ Business Table (65%)             │ Detail Panel (35%)       │
│ ┌──────────────────────────────┐ │ ┌────────────────────┐ │
│ │ Business      │ Owner │ Calls │ │ │ Tech Support Inc   │ │
│ │ Name          │ Email │ (30d) │ │ │                    │ │
│ │───────────────┼───────┼───────│ │ │ Owner: user@...    │ │
│ │ Tech Support  │ john@ │ 145   │ │ │ Industry: Tech     │ │
│ │ Sales Corp    │ jane@ │ 89    │ │ │ Phone: +1234567890 │ │
│ │ ...           │ ...   │ ...   │ │ │                    │ │
│ └──────────────────────────────┘ │ │ Business Hours:    │ │
│                                    │ │ Mon-Fri: 9am-5pm   │ │
│                                    │ │ Sat-Sun: Closed    │ │
│                                    │ │                    │ │
│                                    │ │ Core Services (3): │ │
│                                    │ │ - Technical Support│ │
│                                    │ │ - Sales Inquiries  │ │
│                                    │ │ - Billing Help     │ │
│                                    │ │                    │ │
│                                    │ │ AI Configuration:  │ │
│                                    │ │ Agent: Sarah       │ │
│                                    │ │ Tone: Professional │ │
│                                    │ │ Forwarding: On     │ │
│                                    │ └────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Features**:
- Search by business name, owner email, or phone number
- Filter by industry
- Sort by calls (30d), created date, business name
- Detail panel with full business configuration
- Link to Call Logs filtered by business

**Table Columns**:
1. Business Name
2. Owner Email
3. Industry
4. Primary Phone Number
5. Calls (30d count)
6. Status (active badge if has recent calls)

**Detail Panel Sections**:
- Business Info: Name, Industry, Website, Address, Timezone
- Contact: Primary phone, owner email
- Operating Hours: Grid of 7 days with open/close times
- Core Services: Bulleted list
- AI Agent Configuration: Agent name, tone, greeting message (truncated), forwarding enabled
- Statistics: Total calls (all-time), avg duration, answered vs forwarded ratio

---

#### 4. Call Logs Page (`4_📞_Call_Logs.py`)

**Purpose**: Advanced search and view of call records

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ Call Logs                                      🔄 Refresh    │
├─────────────────────────────────────────────────────────────┤
│ Advanced Filters (collapsible)                               │
│ ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌────────────┐ │
│ │ Date Range │ │ Business ▼ │ │ Status ▼ │ │ Caller #   │ │
│ └────────────┘ └────────────┘ └──────────┘ └────────────┘ │
│ ┌────────────┐ ┌────────────┐ ┌──────────┐               │
│ │ Min Dur.   │ │ Max Dur.   │ │ [Search] │               │
│ └────────────┘ └────────────┘ └──────────┘               │
├─────────────────────────────────────────────────────────────┤
│ Call Logs Table (full width)                                │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Date/Time  │ Business  │ Caller    │ Dur.│ Status│ Sum. ││
│ │────────────┼───────────┼───────────┼─────┼───────┼──────││
│ │ 2024-01-15 │ Tech Sup. │ +123...   │ 4:32│ Ans.  │ Cust ││
│ │ 14:32      │           │           │     │ by AI │ had..││
│ │ 2024-01-15 │ Sales     │ +456...   │ 2:15│ Fwd.  │ Info ││
│ │ 12:15      │           │           │     │       │ req..││
│ │ ...        │ ...       │ ...       │ ... │ ...   │ ...  ││
│ └──────────────────────────────────────────────────────────┘│
│ [Show 25 / 50 / 100 per page]                 Page 1 of 42  │
└─────────────────────────────────────────────────────────────┘
```

**Click Row → Opens Detail Modal**:
```
┌─────────────────────────────────────────────┐
│ Call Details                           [X]   │
├─────────────────────────────────────────────┤
│ Call ID: abc-123-def                         │
│ Date/Time: 2024-01-15 14:32:15 PST          │
│ Duration: 4:32                               │
│ Status: Answered by AI                       │
├─────────────────────────────────────────────┤
│ Caller Information                           │
│ Phone: +1 (234) 567-8900                    │
│ Name: John Customer                          │
├─────────────────────────────────────────────┤
│ Business Information                         │
│ Business: Tech Support Inc                   │
│ Receiving #: +1 (800) 555-0123              │
├─────────────────────────────────────────────┤
│ AI Summary                                   │
│ Customer called regarding billing issue...   │
│ [Full summary text]                          │
├─────────────────────────────────────────────┤
│ Full Transcript                              │
│ [Collapsible section with full text]         │
│                                              │
├─────────────────────────────────────────────┤
│ Recording (if available)                     │
│ [🔊 Play Recording]                          │
├─────────────────────────────────────────────┤
│ Related Appointment                          │
│ [Link to appointment if exists]              │
├─────────────────────────────────────────────┤
│ Call Notes (editable - future feature)       │
│ [Empty or existing notes]                    │
│                                              │
│ [Close]                                      │
└─────────────────────────────────────────────┘
```

**Features**:
- Date range picker (default: last 7 days)
- Multi-filter: Business, Status (answered_by_ai/forwarded/missed/voicemail)
- Duration filters (min/max in minutes)
- Caller phone number search (partial match)
- Full-text search in AI summaries (future enhancement)
- Export filtered results to CSV
- Pagination with configurable page size

**Table Columns**:
1. Date/Time (formatted with timezone)
2. Business Name
3. Caller Phone (formatted)
4. Duration (MM:SS format)
5. Status (badge with color coding)
6. AI Summary (truncated to 50 chars with tooltip)
7. Actions (View Details icon)

**Status Color Coding**:
- Answered by AI: Green
- Forwarded: Blue
- Missed: Yellow
- Voicemail: Gray
- Error: Red

---

#### 5. Billing Page (`5_💳_Billing.py`)

**Purpose**: Read-only monitoring of subscriptions, invoices, and usage

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ Billing & Usage                                🔄 Refresh    │
├─────────────────────────────────────────────────────────────┤
│ ⚠️ Note: Product and pricing managed via Stripe Dashboard   │
├─────────────────────────────────────────────────────────────┤
│ Tabs: [Subscriptions] [Invoices] [Usage] [Payment Methods]  │
├─────────────────────────────────────────────────────────────┤
│ === SUBSCRIPTIONS TAB ===                                    │
│ Filters: [Status ▼] [Plan ▼]                                │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ User Email │ Plan    │ Status │ Period End  │ Cancel @   ││
│ │────────────┼─────────┼────────┼─────────────┼────────────││
│ │ user@ex.com│ Prof.   │ Active │ 2024-02-15  │ No         ││
│ │ jane@ex.com│ Scale   │ Past Due│ 2024-01-20 │ Yes        ││
│ │ ...        │ ...     │ ...    │ ...         │ ...        ││
│ └──────────────────────────────────────────────────────────┘│
│                                                               │
│ === INVOICES TAB ===                                         │
│ Filters: [Status ▼] [Date Range]                            │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ User Email │ Amount  │ Status │ Due Date    │ Paid Date  ││
│ │────────────┼─────────┼────────┼─────────────┼────────────││
│ │ user@ex.com│ $29.00  │ Paid   │ 2024-01-15  │ 2024-01-15 ││
│ │ jane@ex.com│ $99.00  │ Open   │ 2024-01-20  │ -          ││
│ │ [View Invoice] (link to Stripe hosted URL)               ││
│ └──────────────────────────────────────────────────────────┘│
│                                                               │
│ === USAGE TAB ===                                            │
│ Search: [User Email]  [Billing Period ▼]                    │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ User       │ Period        │ Used   │ Limit  │ Overage   ││
│ │────────────┼───────────────┼────────┼────────┼───────────││
│ │ user@ex.com│ 2024-01-01 to │ 245 min│ 250 min│ $0.00     ││
│ │            │ 2024-01-31    │        │        │           ││
│ │ jane@ex.com│ 2024-01-01 to │ 512 min│ 500 min│ $2.40     ││
│ │            │ 2024-01-31    │        │        │           ││
│ └──────────────────────────────────────────────────────────┘│
│                                                               │
│ === PAYMENT METHODS TAB ===                                  │
│ Search: [User Email]                                         │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ User       │ Type  │ Last 4 │ Status │ Default │ Added   ││
│ │────────────┼───────┼────────┼────────┼─────────┼─────────││
│ │ user@ex.com│ Card  │ 4242   │ Active │ Yes     │ 2024-01 ││
│ │ jane@ex.com│ Card  │ 5555   │ Active │ Yes     │ 2024-01 ││
│ └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Features**:
- **Subscriptions Tab**: View all subscriptions, filter by status/plan, see next billing date
- **Invoices Tab**: View invoice history, link to Stripe hosted invoice (PDF)
- **Usage Tab**: Monthly usage summaries, highlight overage users
- **Payment Methods Tab**: Active payment methods, identify users without valid payment
- Export each tab to CSV
- No edit functionality (managed via Stripe)

**Use Cases**:
- Identify past_due subscriptions for follow-up
- Monitor usage patterns and overage trends
- Verify payment method issues
- Generate billing reports

---

#### 6. Entitlements Page (`6_⚡_Entitlements.py`) **[PRIORITY]**

**Purpose**: Manage user feature access overrides

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ Feature Entitlements Management                              │
├─────────────────────────────────────────────────────────────┤
│ User Selection (Left 40%)       │ Feature Management (60%)  │
│ ┌─────────────────────────────┐ │ ┌──────────────────────┐ │
│ │ Search User                  │ │ │ Selected: user@ex.com│ │
│ │ ┌─────────────────────────┐ │ │ │ Plan: Professional   │ │
│ │ │ 🔍 Email or Name        │ │ │ └──────────────────────┘ │
│ │ └─────────────────────────┘ │ │                          │
│ │                              │ │ Feature Access Table     │
│ │ Recent Searches:             │ │ ┌──────────────────────┐ │
│ │ • user@example.com           │ │ │Feature│Plan│Over│Act││ │
│ │ • jane@test.com              │ │ │──────┼────┼────┼────││ │
│ │ • admin@corp.com             │ │ │Appt  │ ✓  │ -  │ ✓ ││ │
│ │                              │ │ │Fwd   │ ✗  │ ✓  │ ✓ ││ │
│ │ Current Plan: Professional   │ │ │Custom│ ✓  │ ✗  │ ✗ ││ │
│ │ Plan includes 8 features:    │ │ │...   │... │... │...││ │
│ │ ✓ Appointment Booking        │ │ └──────────────────────┘ │
│ │ ✓ Custom Questions           │ │                          │
│ │ ✓ Call Forwarding            │ │ Add/Edit Override        │
│ │ ✓ ...                        │ │ ┌──────────────────────┐ │
│ │                              │ │ │ Feature: [Select ▼]  │ │
│ │ Active Overrides (3):        │ │ │ Access: [ ] Grant    │ │
│ │ • Call Forwarding (granted)  │ │ │         [✓] Revoke   │ │
│ │   Expires: 2024-03-01        │ │ │ Expires: [Date]      │ │
│ │ • Analytics (revoked)        │ │ │ Notes: [Required]    │ │
│ │   No expiration              │ │ │ [____________]       │ │
│ └─────────────────────────────┘ │ │                      │ │
│                                  │ │ [Cancel] [Save]      │ │
│                                  │ └──────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Workflow**:
1. **Search User**: Type email/name, autocomplete suggestions appear
2. **View Current State**:
   - Display user's current plan
   - Show all features included in plan (checked green)
   - Show active overrides (highlighted yellow for grants, red for revocations)
3. **Add Override**:
   - Select feature from dropdown (all features in system)
   - Choose Grant (give access) or Revoke (remove access)
   - Optional expiration date (datetime picker)
   - Required notes field (min 10 chars) for audit trail
4. **Save**:
   - Confirmation dialog shows before/after comparison
   - Creates UserFeatureOverride record
   - Logs action in audit trail

**Feature Access Logic**:
- **Plan Default**: Feature included in user's current plan (based on plan_features junction)
- **Override**: UserFeatureOverride record for this user+feature
- **Actual Access**: Final computed access (plan + override logic)
  - If override exists: `has_access` from override
  - If no override: check if feature in plan
  - If expired override: fall back to plan default

**Table Columns**:
1. Feature Key (human-readable name)
2. Plan Default (✓ or ✗)
3. Override (✓ grant, ✗ revoke, - none)
4. Actual Access (final result, color-coded)
5. Actions (Edit/Delete override button)

**Safety Features**:
- Warn if granting feature already in plan (redundant)
- Warn if revoking critical feature (e.g., basic_call_handling)
- Require notes for all overrides (audit purposes)
- Confirmation dialog with clear before/after state
- Transaction rollback on error

**Audit Trail**:
- Every override change logged to separate audit table
- Admin username (from env var)
- Timestamp
- Action (grant/revoke/delete)
- Notes from admin
- Previous and new values

**Common Use Cases**:
- Grant trial user access to premium feature for testing
- Temporarily revoke feature due to abuse
- Extend feature access for VIP customer
- Grant early access to beta features

---

#### 7. Credits Page (`7_💰_Credits.py`) **[PRIORITY]**

**Purpose**: View credit balances and perform manual adjustments

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ Credit Management                              🔄 Refresh    │
├─────────────────────────────────────────────────────────────┤
│ User Selection (Left 35%)       │ Credit Details (65%)      │
│ ┌─────────────────────────────┐ │ ┌──────────────────────┐ │
│ │ Search User                  │ │ │ user@example.com     │ │
│ │ ┌─────────────────────────┐ │ │ └──────────────────────┘ │
│ │ │ 🔍 Email or Name        │ │ │                          │
│ │ └─────────────────────────┘ │ │ Credit Balance Summary   │
│ │                              │ │ ┌──────────────────────┐ │
│ │ Recent:                      │ │ │ Total Balance:       │ │
│ │ • user@example.com           │ │ │ $45.50               │ │
│ │ • jane@test.com              │ │ │                      │ │
│ │                              │ │ │ Breakdown:           │ │
│ └─────────────────────────────┘ │ │ • Trial: $0.00       │ │
│                                  │ │ • Subscription: $25.00│ │
│                                  │ │ • Credit Pack: $20.50│ │
│                                  │ │ • Adjustments: $0.00 │ │
│                                  │ │                      │ │
│                                  │ │ Last Updated:        │ │
│                                  │ │ 2024-01-15 14:32     │ │
│                                  │ └──────────────────────┘ │
│                                  │                          │
│                                  │ Transaction History      │
│                                  │ Filters: [Type ▼] [Date]│
│                                  │ ┌──────────────────────┐ │
│                                  │ │Date│Type│Amt│Balance││ │
│                                  │ │────┼────┼───┼───────││ │
│                                  │ │1/15│Deduct│-2.50│45.50││
│                                  │ │1/10│Grant│+25.00│48.00││
│                                  │ │1/05│Pack│+20.50│23.00││
│                                  │ │...│...│...│...    ││ │
│                                  │ └──────────────────────┘ │
│                                  │ [Show 25/50/100]         │
├─────────────────────────────────────────────────────────────┤
│ Manual Credit Adjustment                                     │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Amount: [________] (Positive to add, negative to deduct) ││
│ │                                                           ││
│ │ Transaction Type: [Manual Adjustment ▼]                  ││
│ │                   Options: Manual Adjustment, Refund,    ││
│ │                           Grant Trial, Grant Subscription││
│ │                                                           ││
│ │ Reason (Required): [_________________________________]   ││
│ │                    [_________________________________]   ││
│ │                    Min 10 characters                     ││
│ │                                                           ││
│ │ Preview New Balance: $45.50 → $65.50 (+$20.00)          ││
│ │                                                           ││
│ │                            [Cancel] [Preview] [Confirm]  ││
│ └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Workflow**:
1. **Search User**: Autocomplete search by email/name
2. **View Balance**:
   - Total balance displayed prominently
   - Breakdown by source (trial/subscription/pack/adjustment)
   - Last updated timestamp
3. **Review History**:
   - Paginated transaction table
   - Filter by transaction type
   - Date range filter
   - Each row shows: date, type, amount (+/-), balance after
4. **Adjust Credits**:
   - Enter amount (positive or negative)
   - Select transaction type from dropdown
   - Enter required reason (audit trail)
   - Preview shows current → new balance calculation
5. **Confirm**:
   - Confirmation dialog for amounts > $100 equivalent
   - Warning dialog for negative balances
   - On confirm: Creates CreditTransaction and updates CreditBalance atomically

**Transaction Types**:
- `ADJUSTMENT` - Manual admin adjustment (default)
- `REFUND` - Refund credits to user
- `GRANT_TRIAL` - Grant additional trial credits
- `GRANT_SUBSCRIPTION` - Grant subscription credits outside billing cycle
- `GRANT_CREDIT_PACK` - Manual credit pack grant (e.g., promo)

**Credit Balance Calculation**:
- **Total Balance** = Sum of all transaction amounts
- **Breakdown**:
  - Trial Credits: Sum of GRANT_TRIAL transactions
  - Subscription Credits: Sum of GRANT_SUBSCRIPTION transactions
  - Credit Pack Credits: Sum of GRANT_CREDIT_PACK transactions
  - Adjustment Credits: Sum of ADJUSTMENT + REFUND transactions
  - (Deductions are negative amounts in transactions)

**Safety Features**:
- **Large Amount Warning**: Confirmation required for adjustments > $100 equivalent
- **Negative Balance Warning**: Alert shown if new balance would be negative
- **Reason Required**: Cannot submit without reason (min 10 chars)
- **Preview Before Confirm**: Shows exact new balance before save
- **Transaction Atomicity**: Database transaction wraps both CreditTransaction insert and CreditBalance update
- **Rollback on Error**: Any failure rolls back entire operation
- **Audit Trail**: Transaction metadata includes admin username, timestamp, reason

**Validation Rules**:
- Amount must be non-zero
- Reason must be >= 10 characters
- Transaction type must be selected
- Cannot adjust credits for deleted/inactive users

**Display Formatting**:
- Currency: $XX.XX format (2 decimal places)
- Dates: YYYY-MM-DD HH:MM timezone
- Positive amounts: Green with + prefix
- Negative amounts: Red with - prefix
- Balance after: Bold

**Common Use Cases**:
- Refund credits for service issues
- Grant promotional credits
- Adjust balance due to billing errors
- Compensate for system downtime
- Grant trial extension

---

#### 8. Promotions Page (`8_🎟️_Promotions.py`)

**Purpose**: View promotion code usage and tracking

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ Promotion Codes                                🔄 Refresh    │
├─────────────────────────────────────────────────────────────┤
│ Note: Promotion codes created in Stripe Dashboard           │
├─────────────────────────────────────────────────────────────┤
│ Promotion Codes (Read-Only)                                  │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Code       │ Stripe ID           │ Users │ Last Used    ││
│ │────────────┼─────────────────────┼───────┼──────────────││
│ │ SAVE20     │ promo_abc123def456  │ 45    │ 2024-01-15   ││
│ │ TRIAL30    │ promo_xyz789uvw012  │ 12    │ 2024-01-14   ││
│ │ ...        │ ...                 │ ...   │ ...          ││
│ └──────────────────────────────────────────────────────────┘│
│                                                               │
│ Click code to view usage details:                            │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ SAVE20 - Usage History                                   ││
│ │──────────────────────────────────────────────────────────││
│ │ User Email     │ Action    │ Date       │ Invoice       ││
│ │────────────────┼───────────┼────────────┼───────────────││
│ │ user@test.com  │ Applied   │ 2024-01-15 │ in_abc123     ││
│ │ jane@test.com  │ Validated │ 2024-01-14 │ -             ││
│ │ fail@test.com  │ Failed    │ 2024-01-13 │ - (Expired)   ││
│ └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Features**:
- Read-only view of promotion codes
- Usage count per code
- Detailed usage history per code
- Filter by date range
- Action types: validated, applied, cleared, failed
- Failure reasons displayed

---

#### 9. Appointments Page (`9_📅_Appointments.py`)

**Purpose**: View and manage appointment bookings

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ Appointments                                   🔄 Refresh    │
├─────────────────────────────────────────────────────────────┤
│ Filters: [Status ▼] [Date Range] [Business ▼] [Search]     │
├─────────────────────────────────────────────────────────────┤
│ Appointments Table                                           │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Date/Time   │ Business  │ Customer │ Status │ Source    ││
│ │─────────────┼───────────┼──────────┼────────┼───────────││
│ │ 2024-01-20  │ Tech Sup. │ John Doe │ Confirm│ AI Call   ││
│ │ 10:00 AM    │           │          │        │           ││
│ │ 2024-01-21  │ Sales     │ Jane S.  │ Cancel │ Manual    ││
│ │ 2:30 PM     │           │          │        │           ││
│ └──────────────────────────────────────────────────────────┘│
│                                                               │
│ Click row for details:                                       │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Appointment Details                                      ││
│ │ Title: Initial Consultation                              ││
│ │ Description: Customer called to schedule...              ││
│ │ Start: 2024-01-20 10:00 AM PST                          ││
│ │ End: 2024-01-20 11:00 AM PST                            ││
│ │ Status: Confirmed                                        ││
│ │                                                          ││
│ │ Customer: John Doe (john@example.com)                   ││
│ │ Business: Tech Support Inc                               ││
│ │ Booked via: AI Call (Call ID: abc123)                   ││
│ │                                                          ││
│ │ Notifications:                                           ││
│ │ • Confirmation sent: 2024-01-15 14:35                   ││
│ │ • Reminder sent: Not yet                                ││
│ └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Features**:
- Filter by status (confirmed/cancelled/completed/no_show)
- Date range filter
- Business filter
- Search by customer name/email
- View Nylas calendar event details
- Link to associated call log
- Display notification history

---

#### 10. System Page (`10_🔧_System.py`)

**Purpose**: System health monitoring and configuration

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ System Status                                  🔄 Refresh    │
├─────────────────────────────────────────────────────────────┤
│ Database Connection                                          │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Status: ✓ Connected                                      ││
│ │ Host: postgres.aicallgo-staging.svc.cluster.local        ││
│ │ Database: aicallgo_staging                               ││
│ │ Pool Size: 5 / 10 connections active                     ││
│ │ Last Query: 0.02s ago                                    ││
│ └──────────────────────────────────────────────────────────┘│
│                                                               │
│ Database Statistics                                          │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Total Users: 1,247                                       ││
│ │ Total Businesses: 892                                    ││
│ │ Total Call Logs: 45,231                                  ││
│ │ Total Appointments: 1,205                                ││
│ │ Active Subscriptions: 856                                ││
│ │ Database Size: 2.4 GB                                    ││
│ └──────────────────────────────────────────────────────────┘│
│                                                               │
│ Feature Flags (future)                                       │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ [Placeholder for feature flag management]                ││
│ └──────────────────────────────────────────────────────────┘│
│                                                               │
│ Admin Audit Log (recent actions)                             │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Timestamp       │ Admin │ Action         │ Details       ││
│ │─────────────────┼───────┼────────────────┼───────────────││
│ │ 2024-01-15 14:32│ admin │ Credit Adjust  │ user@test +$20││
│ │ 2024-01-15 12:15│ admin │ Entitlement    │ jane@ grant...││
│ └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Features**:
- Database connection health check
- Connection pool monitoring
- Table row counts
- Database size
- Admin action audit log
- System configuration display (read-only)

---

## Design System

### Color Palette (Mirroring nextjs-frontend)

**CSS Variables** (to be defined in `static/custom.css`):
```css
:root {
  /* Primary Colors - Dark Green-ish Purple */
  --color-primary-50: #f1f9ef;
  --color-primary-500: #5f8a4e;
  --color-primary-600: #456535;
  --color-primary-950: #1a2114;

  /* Semantic Colors */
  --color-background: #ffffff;
  --color-card: #f9fafb;
  --color-card-border: #e5e7eb;
  --color-text-primary: #1f2937;
  --color-text-muted: #6b7280;
  --color-border: #e5e7eb;

  /* Status Colors */
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-info: #3b82f6;

  /* Spacing */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;

  /* Border Radius */
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;

  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
}
```

### Typography

**Font Stack**:
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
```

**Type Scale**:
- **Display**: 2rem (32px) - Page titles
- **Heading 1**: 1.5rem (24px) - Section headers
- **Heading 2**: 1.25rem (20px) - Card titles
- **Heading 3**: 1rem (16px) - Subheadings
- **Body**: 1rem (16px) - Main content
- **Small**: 0.875rem (14px) - Labels, captions
- **Tiny**: 0.75rem (12px) - Metadata

**Font Weights**:
- Regular: 400
- Medium: 500
- Semibold: 600
- Bold: 700

### Component Styling Guidelines

#### Cards
```python
# Streamlit custom container styled as card
st.markdown("""
<div class="custom-card">
    <div class="card-header">
        <h2>Card Title</h2>
    </div>
    <div class="card-content">
        <!-- Content here -->
    </div>
</div>
""", unsafe_allow_html=True)
```

**CSS**:
```css
.custom-card {
  background: var(--color-card);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
  box-shadow: var(--shadow-sm);
}

.card-header {
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-border);
}

.card-content {
  color: var(--color-text-primary);
}
```

#### Buttons
```python
# Use Streamlit's native buttons with custom CSS classes
st.button("Primary Action", key="primary-btn", use_container_width=False)
st.button("Secondary Action", key="secondary-btn", use_container_width=False)
```

**CSS**:
```css
/* Primary Button */
div[data-testid="stButton"] button[kind="primary"] {
  background-color: var(--color-primary-600);
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

div[data-testid="stButton"] button[kind="primary"]:hover {
  background-color: var(--color-primary-950);
}

/* Secondary Button */
div[data-testid="stButton"] button[kind="secondary"] {
  background-color: transparent;
  color: var(--color-primary-600);
  border: 1px solid var(--color-primary-600);
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
}
```

#### Tables
```python
# Styled dataframe
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "email": st.column_config.TextColumn("Email", width="medium"),
        "status": st.column_config.TextColumn("Status", width="small"),
    }
)
```

**CSS**:
```css
/* Table styling */
div[data-testid="stDataFrame"] {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

div[data-testid="stDataFrame"] table {
  font-size: 0.875rem;
}

div[data-testid="stDataFrame"] thead {
  background-color: var(--color-card);
  font-weight: 600;
  color: var(--color-text-primary);
}

div[data-testid="stDataFrame"] tbody tr:hover {
  background-color: var(--color-card);
}

div[data-testid="stDataFrame"] tbody tr:nth-child(even) {
  background-color: #fafafa;
}
```

#### Forms
```python
with st.form("adjustment-form"):
    amount = st.number_input("Amount", step=0.01)
    reason = st.text_area("Reason", max_chars=500)
    submit = st.form_submit_button("Submit")
```

**CSS**:
```css
/* Form styling */
div[data-testid="stForm"] {
  background: var(--color-card);
  padding: var(--spacing-lg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

div[data-testid="stForm"] label {
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

div[data-testid="stForm"] input,
div[data-testid="stForm"] textarea {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 0.5rem;
  font-size: 1rem;
}

div[data-testid="stForm"] input:focus,
div[data-testid="stForm"] textarea:focus {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}
```

#### Status Badges
```python
def status_badge(status: str) -> str:
    """Generate HTML for status badge"""
    colors = {
        "active": "success",
        "inactive": "error",
        "pending": "warning",
        "trial": "info"
    }
    badge_class = colors.get(status.lower(), "info")
    return f'<span class="badge badge-{badge_class}">{status}</span>'

st.markdown(status_badge("active"), unsafe_allow_html=True)
```

**CSS**:
```css
.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge-success {
  background-color: #d1fae5;
  color: #065f46;
}

.badge-error {
  background-color: #fee2e2;
  color: #991b1b;
}

.badge-warning {
  background-color: #fef3c7;
  color: #92400e;
}

.badge-info {
  background-color: #dbeafe;
  color: #1e40af;
}
```

### Charts (Plotly styled like Recharts)

```python
import plotly.graph_objects as go

def create_styled_line_chart(df, x_col, y_col, title):
    """Create line chart matching nextjs-frontend Recharts style"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df[x_col],
        y=df[y_col],
        mode='lines',
        line=dict(color='#5f8a4e', width=2),
        fill='tozeroy',
        fillcolor='rgba(95, 138, 78, 0.1)'
    ))

    fig.update_layout(
        title=title,
        title_font=dict(size=16, color='#1f2937', family='Arial'),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(
            showgrid=True,
            gridcolor='#e5e7eb',
            linecolor='#e5e7eb'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#e5e7eb',
            linecolor='#e5e7eb'
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor='white',
            font_size=12,
            font_family='Arial'
        )
    )

    return fig

st.plotly_chart(create_styled_line_chart(df, 'date', 'calls', 'Calls Over Time'),
                use_container_width=True)
```

### Sidebar Styling

**CSS**:
```css
/* Sidebar */
section[data-testid="stSidebar"] {
  background-color: var(--color-primary-950);
  padding: var(--spacing-lg);
}

section[data-testid="stSidebar"] .sidebar-content {
  color: white;
}

section[data-testid="stSidebar"] a {
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  display: block;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-sm);
  transition: background-color 0.2s;
}

section[data-testid="stSidebar"] a:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: white;
}

section[data-testid="stSidebar"] .active-page {
  background-color: var(--color-primary-600);
  color: white;
}
```

---

## Technical Implementation

### Tech Stack

**Core Technologies**:
- **Python 3.11+** - Match web-backend version
- **Streamlit 1.30+** - Web framework for admin UI
- **SQLAlchemy 2.0** - ORM for database access
- **Asyncpg** - Async PostgreSQL driver
- **Pandas 2.0+** - Data manipulation and display
- **Plotly 5.0+** - Interactive charts
- **Bcrypt** - Password hashing (via passlib)

**Additional Libraries**:
- **python-dotenv** - Environment variable management
- **pydantic** - Data validation and settings
- **pytz** - Timezone handling
- **phonenumbers** - Phone number formatting
- **humanize** - Human-readable formatting (dates, file sizes)

### Project Structure

```
/services/admin-board/
│
├── app.py                              # Main Streamlit app entry point
├── requirements.txt                    # Python dependencies
├── Dockerfile                          # Container build configuration
├── .dockerignore                       # Docker build exclusions
├── .gitignore                          # Git exclusions
├── README.md                           # Setup and usage documentation
│
├── .streamlit/
│   ├── config.toml                     # Streamlit UI configuration
│   └── secrets.toml.example            # Secret template (not committed)
│
├── config/
│   ├── __init__.py
│   ├── settings.py                     # Environment configuration
│   └── auth.py                         # Admin authentication logic
│
├── database/
│   ├── __init__.py
│   ├── connection.py                   # Database session management
│   ├── models.py                       # Import or symlink web-backend models
│   └── queries.py                      # Common query helpers
│
├── pages/
│   ├── 1_📊_Dashboard.py               # Dashboard page
│   ├── 2_👥_Users.py                   # Users management
│   ├── 3_🏢_Businesses.py              # Business profiles
│   ├── 4_📞_Call_Logs.py               # Call logs viewer
│   ├── 5_💳_Billing.py                 # Billing read-only
│   ├── 6_⚡_Entitlements.py            # Feature entitlements (PRIORITY)
│   ├── 7_💰_Credits.py                 # Credit management (PRIORITY)
│   ├── 8_🎟️_Promotions.py             # Promotion codes
│   ├── 9_📅_Appointments.py            # Appointments
│   └── 10_🔧_System.py                 # System status
│
├── components/
│   ├── __init__.py
│   ├── charts.py                       # Reusable chart components
│   ├── tables.py                       # Styled dataframe wrappers
│   ├── forms.py                        # Form helpers with validation
│   ├── cards.py                        # Card layout helpers
│   └── badges.py                       # Status badge generators
│
├── services/
│   ├── __init__.py
│   ├── user_service.py                 # User CRUD operations
│   ├── business_service.py             # Business operations
│   ├── call_log_service.py             # Call log queries
│   ├── entitlement_service.py          # Feature override management
│   ├── credit_service.py               # Credit adjustments
│   ├── billing_service.py              # Billing queries
│   └── audit_service.py                # Audit logging
│
├── static/
│   ├── custom.css                      # Custom CSS (design system)
│   └── logo.png                        # AICallGO logo
│
├── utils/
│   ├── __init__.py
│   ├── formatters.py                   # Date, currency, phone formatting
│   ├── validators.py                   # Input validation
│   └── filters.py                      # Query filter builders
│
├── kubernetes/
│   ├── deployment.yaml                 # K8s deployment manifest
│   ├── service.yaml                    # K8s service manifest
│   ├── ingress.yaml                    # K8s ingress manifest
│   ├── configmap.yaml                  # K8s configmap
│   └── secret.yaml.example             # K8s secret template
│
└── docs/
    ├── IMPLEMENTATION_PLAN.md          # This document
    ├── DEPLOYMENT.md                   # Deployment instructions
    └── USER_GUIDE.md                   # Admin user guide
```

### Key Files Detail

#### `app.py` (Main Entry Point)
```python
import streamlit as st
from config.auth import check_authentication
from config.settings import settings

# Page configuration
st.set_page_config(
    page_title="AICallGO Admin Board",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
with open("static/custom.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Authentication check
if not check_authentication():
    st.stop()

# Home page content
st.title("AICallGO Admin Board")
st.markdown("Welcome to the administrative interface for AICallGO.")

# Quick links
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("### 👥 Users")
    st.markdown("[View Users →](Users)")
with col2:
    st.markdown("### ⚡ Entitlements")
    st.markdown("[Manage Features →](Entitlements)")
with col3:
    st.markdown("### 💰 Credits")
    st.markdown("[Adjust Credits →](Credits)")
```

#### `config/settings.py` (Configuration)
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5

    # Admin Auth
    ADMIN_USERNAME: str
    ADMIN_PASSWORD_HASH: str  # bcrypt hash

    # App Config
    APP_ENV: str = "production"
    SESSION_TIMEOUT_HOURS: int = 8

    # External URLs (for links)
    WEB_FRONTEND_URL: str = "https://staging.aicallgo.com"
    STRIPE_DASHBOARD_URL: str = "https://dashboard.stripe.com"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

#### `config/auth.py` (Authentication)
```python
import streamlit as st
from passlib.context import CryptContext
from datetime import datetime, timedelta
from config.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def check_authentication() -> bool:
    """Check if user is authenticated, show login form if not"""

    # Check if already logged in
    if "authenticated" in st.session_state and st.session_state.authenticated:
        # Check session timeout
        if "login_time" in st.session_state:
            login_time = st.session_state.login_time
            timeout = timedelta(hours=settings.SESSION_TIMEOUT_HOURS)
            if datetime.now() - login_time > timeout:
                st.session_state.authenticated = False
                st.warning("Session expired. Please log in again.")
                return False
        return True

    # Show login form
    st.title("Admin Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if (username == settings.ADMIN_USERNAME and
                pwd_context.verify(password, settings.ADMIN_PASSWORD_HASH)):
                st.session_state.authenticated = True
                st.session_state.admin_username = username
                st.session_state.login_time = datetime.now()
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")

    return False

def logout():
    """Clear authentication state"""
    st.session_state.authenticated = False
    if "admin_username" in st.session_state:
        del st.session_state.admin_username
    if "login_time" in st.session_state:
        del st.session_state.login_time
```

#### `database/connection.py` (Database Connection)
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config.settings import settings

# Async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=False
)

# Async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        yield session
```

#### `.streamlit/config.toml` (Streamlit Configuration)
```toml
[theme]
primaryColor = "#5f8a4e"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f9fafb"
textColor = "#1f2937"
font = "sans serif"

[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = true
maxUploadSize = 10

[browser]
gatherUsageStats = false

[runner]
fastReruns = true
```

### Authentication Implementation

**Environment Variable Approach**:

1. **Generate Password Hash** (one-time setup):
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed = pwd_context.hash("your-secure-password")
print(hashed)
# Output: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5UpV.o/...
```

2. **Set Environment Variables**:
```bash
# In Kubernetes Secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5UpV.o/...
```

3. **Login Flow**:
   - User enters username and password
   - `check_authentication()` verifies against env vars
   - On success, sets `st.session_state.authenticated = True`
   - Session persists for 8 hours (configurable)
   - All pages check authentication before rendering

**Security Features**:
- Bcrypt password hashing (same as web-backend)
- Session timeout after 8 hours
- No password stored in plaintext
- HTTPS-only (enforced by ingress)
- Optional IP whitelist via ingress annotations

### Database Connection Strategy

**Connection Configuration**:
- **URL**: Same PostgreSQL as web-backend (from Kubernetes secret)
- **Pool Size**: 5 connections (lighter than web-backend's 10)
- **Max Overflow**: 5 additional connections under load
- **Pre-ping**: Enabled to detect stale connections
- **Async**: Use asyncpg for non-blocking queries

**Access Pattern**:
- **Read-Heavy**: Most operations are reads (users, call logs, billing)
- **Write-Light**: Only entitlements and credits require writes
- **Transaction Safety**: Use SQLAlchemy transactions for all writes

**Connection Management**:
```python
# Example in a page
import asyncio
from database.connection import get_db
from services.user_service import get_users

async def load_users():
    async with get_db() as db:
        users = await get_users(db, limit=50)
        return users

# In Streamlit page
users = asyncio.run(load_users())
st.dataframe(users)
```

### Periodic Refresh Strategy

**Dashboard Auto-Refresh**:
```python
import time

# In Dashboard page
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# Check if 60 seconds elapsed
if time.time() - st.session_state.last_refresh > 60:
    st.session_state.last_refresh = time.time()
    st.rerun()

# Display countdown
time_until_refresh = int(60 - (time.time() - st.session_state.last_refresh))
st.sidebar.caption(f"Auto-refresh in {time_until_refresh}s")
```

**Manual Refresh**:
```python
# In all data pages
if st.button("🔄 Refresh", key="refresh-btn"):
    st.rerun()
```

**Query Caching**:
```python
@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_cached_users(limit: int):
    return asyncio.run(load_users(limit))
```

---

## Priority Features

### 6. Entitlements Management (PRIORITY)

#### Feature Access Logic

**Three-Layer System**:
1. **Feature**: Defined in `features` table (e.g., "appointment_booking", "call_forwarding")
2. **Plan Features**: Junction table `plan_features` (which features are in which plans)
3. **User Overrides**: Table `user_feature_overrides` (individual grants/revocations)

**Access Calculation**:
```python
def calculate_user_feature_access(user_id: str, feature_id: str) -> bool:
    """
    Calculate if user has access to a feature

    Logic:
    1. Check if user has active override (and not expired)
       - If yes: return override.has_access
    2. If no override: check if feature in user's current plan
       - If yes: return True
    3. Default: return False
    """

    # Check for active override
    override = await db.query(UserFeatureOverride).filter(
        UserFeatureOverride.user_id == user_id,
        UserFeatureOverride.feature_id == feature_id,
        or_(
            UserFeatureOverride.expires_at.is_(None),
            UserFeatureOverride.expires_at > datetime.now()
        )
    ).first()

    if override:
        return override.has_access

    # Check plan features
    user = await db.query(User).filter(User.id == user_id).first()
    subscription = await db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()

    if subscription:
        plan = await db.query(Plan).filter(
            Plan.stripe_price_id == subscription.stripe_plan_id
        ).first()

        if plan:
            plan_feature = await db.query(PlanFeature).filter(
                PlanFeature.plan_id == plan.id,
                PlanFeature.feature_id == feature_id
            ).first()

            return plan_feature is not None

    return False
```

#### Entitlement Service (`services/entitlement_service.py`)

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from database.models import User, Feature, Plan, PlanFeature, UserFeatureOverride
from datetime import datetime
from typing import List, Dict, Optional
import uuid

async def get_user_with_plan(db: AsyncSession, user_id: str) -> Dict:
    """Get user with current plan and features"""

    # Get user and subscription
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise ValueError("User not found")

    # Get subscription
    from database.models import Subscription
    sub_query = select(Subscription).where(Subscription.user_id == user_id)
    sub_result = await db.execute(sub_query)
    subscription = sub_result.scalar_one_or_none()

    # Get plan
    plan = None
    plan_features = []
    if subscription:
        plan_query = select(Plan).where(
            Plan.stripe_price_id == subscription.stripe_plan_id
        )
        plan_result = await db.execute(plan_query)
        plan = plan_result.scalar_one_or_none()

        if plan:
            # Get plan features
            pf_query = select(Feature).join(PlanFeature).where(
                PlanFeature.plan_id == plan.id
            )
            pf_result = await db.execute(pf_query)
            plan_features = pf_result.scalars().all()

    return {
        "user": user,
        "subscription": subscription,
        "plan": plan,
        "plan_features": plan_features
    }

async def get_user_overrides(db: AsyncSession, user_id: str) -> List[UserFeatureOverride]:
    """Get all active overrides for user"""

    query = select(UserFeatureOverride).where(
        UserFeatureOverride.user_id == user_id
    ).join(Feature)

    result = await db.execute(query)
    return result.scalars().all()

async def create_feature_override(
    db: AsyncSession,
    user_id: str,
    feature_id: str,
    has_access: bool,
    expires_at: Optional[datetime],
    notes: str,
    admin_username: str
) -> UserFeatureOverride:
    """Create or update feature override"""

    # Check if override already exists
    query = select(UserFeatureOverride).where(
        and_(
            UserFeatureOverride.user_id == user_id,
            UserFeatureOverride.feature_id == feature_id
        )
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing
        existing.has_access = has_access
        existing.expires_at = expires_at
        existing.notes = notes
        existing.updated_at = datetime.now()
        override = existing
    else:
        # Create new
        override = UserFeatureOverride(
            id=uuid.uuid4(),
            user_id=user_id,
            feature_id=feature_id,
            has_access=has_access,
            expires_at=expires_at,
            notes=notes
        )
        db.add(override)

    await db.commit()
    await db.refresh(override)

    # Log to audit trail
    await log_audit_action(
        db=db,
        admin_username=admin_username,
        action="entitlement_override",
        details={
            "user_id": user_id,
            "feature_id": feature_id,
            "has_access": has_access,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "notes": notes
        }
    )

    return override

async def delete_feature_override(
    db: AsyncSession,
    user_id: str,
    feature_id: str,
    admin_username: str
):
    """Delete feature override (revert to plan default)"""

    query = select(UserFeatureOverride).where(
        and_(
            UserFeatureOverride.user_id == user_id,
            UserFeatureOverride.feature_id == feature_id
        )
    )
    result = await db.execute(query)
    override = result.scalar_one_or_none()

    if override:
        await db.delete(override)
        await db.commit()

        # Log to audit trail
        await log_audit_action(
            db=db,
            admin_username=admin_username,
            action="entitlement_override_deleted",
            details={
                "user_id": user_id,
                "feature_id": feature_id
            }
        )

async def get_all_features(db: AsyncSession) -> List[Feature]:
    """Get all available features"""
    query = select(Feature).order_by(Feature.feature_key)
    result = await db.execute(query)
    return result.scalars().all()
```

#### Entitlements Page Implementation Snippet

```python
# pages/6_⚡_Entitlements.py

import streamlit as st
import asyncio
from config.auth import check_authentication
from services.entitlement_service import *

if not check_authentication():
    st.stop()

st.title("⚡ Feature Entitlements Management")

# Two-column layout
col1, col2 = st.columns([0.4, 0.6])

with col1:
    st.subheader("User Selection")

    # Search user
    search_term = st.text_input("🔍 Search by email or name")

    if search_term and len(search_term) >= 3:
        # Search users (autocomplete)
        users = asyncio.run(search_users(search_term))

        if users:
            selected_user = st.selectbox(
                "Select User",
                users,
                format_func=lambda u: f"{u.email} - {u.full_name}"
            )

            if selected_user:
                st.session_state.selected_user_id = selected_user.id
        else:
            st.info("No users found")

with col2:
    if "selected_user_id" in st.session_state:
        user_data = asyncio.run(get_user_with_plan(
            st.session_state.selected_user_id
        ))

        st.subheader(f"Managing: {user_data['user'].email}")

        # Display plan info
        if user_data['plan']:
            st.info(f"Current Plan: {user_data['plan'].name}")
            st.write("Plan includes:")
            for feature in user_data['plan_features']:
                st.write(f"✓ {feature.feature_key}")

        # Feature access table
        st.subheader("Feature Access")

        all_features = asyncio.run(get_all_features())
        overrides = asyncio.run(get_user_overrides(
            st.session_state.selected_user_id
        ))

        # Build table data
        table_data = []
        for feature in all_features:
            in_plan = feature in user_data['plan_features']
            override = next(
                (o for o in overrides if o.feature_id == feature.id),
                None
            )

            actual_access = override.has_access if override else in_plan

            table_data.append({
                "Feature": feature.feature_key,
                "Plan Default": "✓" if in_plan else "✗",
                "Override": "✓" if override and override.has_access else (
                    "✗" if override and not override.has_access else "-"
                ),
                "Actual Access": "✓" if actual_access else "✗"
            })

        st.dataframe(table_data, use_container_width=True)

        # Add/Edit override form
        st.subheader("Add/Edit Override")

        with st.form("override-form"):
            feature_options = {f.feature_key: f.id for f in all_features}
            selected_feature_key = st.selectbox("Feature", list(feature_options.keys()))
            selected_feature_id = feature_options[selected_feature_key]

            has_access = st.radio("Access", ["Grant", "Revoke"]) == "Grant"

            expires_at = st.date_input("Expires At (optional)", value=None)

            notes = st.text_area("Notes (required)", max_chars=500)

            submit = st.form_submit_button("Save Override")

            if submit:
                if len(notes) < 10:
                    st.error("Notes must be at least 10 characters")
                else:
                    # Confirmation dialog
                    if st.session_state.get("confirm_override"):
                        asyncio.run(create_feature_override(
                            user_id=st.session_state.selected_user_id,
                            feature_id=selected_feature_id,
                            has_access=has_access,
                            expires_at=expires_at,
                            notes=notes,
                            admin_username=st.session_state.admin_username
                        ))
                        st.success("Override saved!")
                        st.rerun()
                    else:
                        st.session_state.confirm_override = True
                        st.warning("Click Save Override again to confirm")
    else:
        st.info("Search and select a user to manage entitlements")
```

---

### 7. Credits Management (PRIORITY)

#### Credit Service (`services/credit_service.py`)

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database.models import User, CreditBalance, CreditTransaction
from datetime import datetime
from typing import List, Dict, Optional
from decimal import Decimal
import uuid

async def get_user_credit_balance(db: AsyncSession, user_id: str) -> Optional[CreditBalance]:
    """Get user's current credit balance"""

    query = select(CreditBalance).where(CreditBalance.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_credit_transactions(
    db: AsyncSession,
    user_id: str,
    limit: int = 100,
    transaction_type: Optional[str] = None
) -> List[CreditTransaction]:
    """Get credit transaction history"""

    query = select(CreditTransaction).where(
        CreditTransaction.user_id == user_id
    ).order_by(CreditTransaction.created_at.desc())

    if transaction_type:
        query = query.where(CreditTransaction.transaction_type == transaction_type)

    query = query.limit(limit)

    result = await db.execute(query)
    return result.scalars().all()

async def adjust_credits(
    db: AsyncSession,
    user_id: str,
    amount: Decimal,
    transaction_type: str,
    description: str,
    admin_username: str,
    metadata: Optional[Dict] = None
) -> CreditTransaction:
    """
    Adjust user credits (add or deduct)

    Args:
        amount: Positive to add, negative to deduct
        transaction_type: ADJUSTMENT, REFUND, GRANT_TRIAL, etc.
        description: Admin reason for adjustment
        admin_username: Admin performing action
        metadata: Additional context (JSON)

    Returns:
        Created CreditTransaction

    Raises:
        ValueError: If validation fails
    """

    # Validation
    if amount == 0:
        raise ValueError("Amount cannot be zero")

    if len(description) < 10:
        raise ValueError("Description must be at least 10 characters")

    # Start transaction
    async with db.begin():
        # Get or create credit balance
        balance = await get_user_credit_balance(db, user_id)

        if not balance:
            # Create new balance
            balance = CreditBalance(
                id=uuid.uuid4(),
                user_id=user_id,
                total_balance=Decimal('0.00'),
                trial_credits=Decimal('0.00'),
                subscription_credits=Decimal('0.00'),
                credit_pack_credits=Decimal('0.00'),
                adjustment_credits=Decimal('0.00')
            )
            db.add(balance)
            await db.flush()

        # Calculate new balance
        old_balance = balance.total_balance
        new_balance = old_balance + amount

        # Warn if negative (but allow)
        if new_balance < 0:
            # Log warning in metadata
            if metadata is None:
                metadata = {}
            metadata["warning"] = "Negative balance created"

        # Update balance
        balance.total_balance = new_balance
        balance.last_updated = datetime.now()

        # Update source bucket based on transaction type
        if transaction_type == "GRANT_TRIAL":
            balance.trial_credits += amount
        elif transaction_type == "GRANT_SUBSCRIPTION":
            balance.subscription_credits += amount
        elif transaction_type == "GRANT_CREDIT_PACK":
            balance.credit_pack_credits += amount
        elif transaction_type in ["ADJUSTMENT", "REFUND"]:
            balance.adjustment_credits += amount

        # Create transaction record
        if metadata is None:
            metadata = {}
        metadata["admin_username"] = admin_username
        metadata["old_balance"] = str(old_balance)
        metadata["new_balance"] = str(new_balance)

        transaction = CreditTransaction(
            id=uuid.uuid4(),
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=new_balance,
            description=description,
            transaction_metadata=str(metadata)  # JSON string
        )

        db.add(transaction)

        await db.commit()
        await db.refresh(transaction)

        # Log to audit trail
        await log_audit_action(
            db=db,
            admin_username=admin_username,
            action="credit_adjustment",
            details={
                "user_id": user_id,
                "amount": str(amount),
                "transaction_type": transaction_type,
                "old_balance": str(old_balance),
                "new_balance": str(new_balance),
                "description": description
            }
        )

        return transaction

async def search_users_for_credits(db: AsyncSession, search_term: str) -> List[User]:
    """Search users with credit balance info"""

    query = select(User).where(
        or_(
            User.email.ilike(f"%{search_term}%"),
            User.full_name.ilike(f"%{search_term}%")
        )
    ).limit(10)

    result = await db.execute(query)
    users = result.scalars().all()

    # Attach credit balance to each user
    for user in users:
        balance = await get_user_credit_balance(db, user.id)
        user.credit_balance = balance

    return users
```

#### Credits Page Implementation Snippet

```python
# pages/7_💰_Credits.py

import streamlit as st
import asyncio
from decimal import Decimal
from config.auth import check_authentication
from services.credit_service import *
from utils.formatters import format_currency

if not check_authentication():
    st.stop()

st.title("💰 Credit Management")

# Two-column layout
col1, col2 = st.columns([0.35, 0.65])

with col1:
    st.subheader("User Selection")

    search_term = st.text_input("🔍 Search by email or name")

    if search_term and len(search_term) >= 3:
        users = asyncio.run(search_users_for_credits(search_term))

        if users:
            selected_user = st.selectbox(
                "Select User",
                users,
                format_func=lambda u: (
                    f"{u.email} - "
                    f"{format_currency(u.credit_balance.total_balance) if u.credit_balance else '$0.00'}"
                )
            )

            if selected_user:
                st.session_state.selected_user_id = selected_user.id

with col2:
    if "selected_user_id" in st.session_state:
        user_id = st.session_state.selected_user_id
        balance = asyncio.run(get_user_credit_balance(user_id))

        st.subheader("Credit Balance Summary")

        if balance:
            # Balance card
            st.markdown(f"""
            <div class="custom-card">
                <h2 style="margin:0;">{format_currency(balance.total_balance)}</h2>
                <p style="color: var(--color-text-muted); margin:0;">Total Balance</p>

                <hr style="margin: 1rem 0;">

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div>
                        <strong>Trial:</strong> {format_currency(balance.trial_credits)}<br>
                        <strong>Subscription:</strong> {format_currency(balance.subscription_credits)}
                    </div>
                    <div>
                        <strong>Credit Pack:</strong> {format_currency(balance.credit_pack_credits)}<br>
                        <strong>Adjustments:</strong> {format_currency(balance.adjustment_credits)}
                    </div>
                </div>

                <p style="font-size: 0.75rem; color: var(--color-text-muted); margin-top: 1rem;">
                    Last Updated: {balance.last_updated.strftime('%Y-%m-%d %H:%M')}
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No credit balance found. Will be created on first adjustment.")

        # Transaction history
        st.subheader("Transaction History")

        trans_type_filter = st.selectbox(
            "Filter by Type",
            ["All", "ADJUSTMENT", "REFUND", "GRANT_TRIAL", "DEDUCT_USAGE"]
        )

        transactions = asyncio.run(get_credit_transactions(
            user_id,
            limit=100,
            transaction_type=trans_type_filter if trans_type_filter != "All" else None
        ))

        if transactions:
            trans_data = []
            for t in transactions:
                trans_data.append({
                    "Date": t.created_at.strftime('%Y-%m-%d %H:%M'),
                    "Type": t.transaction_type,
                    "Amount": format_currency(t.amount),
                    "Balance After": format_currency(t.balance_after),
                    "Description": t.description[:50] + "..." if len(t.description) > 50 else t.description
                })

            st.dataframe(trans_data, use_container_width=True)
        else:
            st.info("No transactions found")

        # Manual adjustment form
        st.subheader("Manual Credit Adjustment")

        with st.form("credit-adjustment-form"):
            amount_input = st.number_input(
                "Amount (positive to add, negative to deduct)",
                step=0.01,
                format="%.2f"
            )

            trans_type = st.selectbox(
                "Transaction Type",
                ["ADJUSTMENT", "REFUND", "GRANT_TRIAL", "GRANT_SUBSCRIPTION", "GRANT_CREDIT_PACK"]
            )

            description = st.text_area(
                "Reason (Required, min 10 characters)",
                max_chars=500
            )

            # Preview
            if amount_input != 0 and balance:
                current_balance = balance.total_balance
                new_balance = current_balance + Decimal(str(amount_input))

                st.info(f"""
                **Preview:**

                Current Balance: {format_currency(current_balance)}

                Adjustment: {format_currency(Decimal(str(amount_input)))}

                New Balance: {format_currency(new_balance)}
                """)

                if new_balance < 0:
                    st.warning("⚠️ This will create a negative balance!")

                if abs(amount_input) > 100:
                    st.warning("⚠️ Large amount adjustment (> $100)")

            col_btn1, col_btn2, col_btn3 = st.columns(3)

            with col_btn1:
                cancel = st.form_submit_button("Cancel", type="secondary")

            with col_btn3:
                confirm = st.form_submit_button("Confirm Adjustment", type="primary")

            if confirm:
                # Validation
                if amount_input == 0:
                    st.error("Amount cannot be zero")
                elif len(description) < 10:
                    st.error("Description must be at least 10 characters")
                else:
                    # Additional confirmation for large amounts
                    if abs(amount_input) > 100:
                        if not st.session_state.get("confirm_large_amount"):
                            st.session_state.confirm_large_amount = True
                            st.warning("Large amount detected. Click Confirm again to proceed.")
                        else:
                            # Perform adjustment
                            try:
                                transaction = asyncio.run(adjust_credits(
                                    user_id=user_id,
                                    amount=Decimal(str(amount_input)),
                                    transaction_type=trans_type,
                                    description=description,
                                    admin_username=st.session_state.admin_username
                                ))

                                st.success(f"""
                                Credit adjustment successful!

                                New Balance: {format_currency(transaction.balance_after)}
                                """)

                                # Clear confirmation flag
                                st.session_state.confirm_large_amount = False

                                # Refresh page
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    else:
                        # Normal amount, proceed directly
                        try:
                            transaction = asyncio.run(adjust_credits(
                                user_id=user_id,
                                amount=Decimal(str(amount_input)),
                                transaction_type=trans_type,
                                description=description,
                                admin_username=st.session_state.admin_username
                            ))

                            st.success(f"""
                            Credit adjustment successful!

                            New Balance: {format_currency(transaction.balance_after)}
                            """)

                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

            if cancel:
                st.session_state.confirm_large_amount = False
                st.rerun()
    else:
        st.info("Search and select a user to manage credits")
```

---

## Kubernetes Deployment

### Docker Configuration

#### `Dockerfile`
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### `requirements.txt`
```
streamlit==1.30.0
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
pandas==2.1.4
plotly==5.18.0
passlib[bcrypt]==1.7.4
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0
pytz==2023.3
phonenumbers==8.13.27
humanize==4.9.0
```

### Kubernetes Manifests

#### `kubernetes/deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: admin-board
  namespace: aicallgo-staging
  labels:
    app: admin-board
    component: admin-ui
spec:
  replicas: 1
  selector:
    matchLabels:
      app: admin-board
  template:
    metadata:
      labels:
        app: admin-board
        component: admin-ui
    spec:
      containers:
      - name: admin-board
        image: registry.digitalocean.com/aicallgo-registry/admin-board:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8501
          name: http
          protocol: TCP
        env:
        - name: APP_ENV
          value: "staging"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: admin-board-secrets
              key: database-url
        - name: ADMIN_USERNAME
          valueFrom:
            secretKeyRef:
              name: admin-board-secrets
              key: admin-username
        - name: ADMIN_PASSWORD_HASH
          valueFrom:
            secretKeyRef:
              name: admin-board-secrets
              key: admin-password-hash
        - name: WEB_FRONTEND_URL
          valueFrom:
            configMapKeyRef:
              name: admin-board-config
              key: web-frontend-url
        - name: STRIPE_DASHBOARD_URL
          value: "https://dashboard.stripe.com"
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
      imagePullSecrets:
      - name: registry-aicallgo-registry
```

#### `kubernetes/service.yaml`
```yaml
apiVersion: v1
kind: Service
metadata:
  name: admin-board
  namespace: aicallgo-staging
  labels:
    app: admin-board
spec:
  type: ClusterIP
  ports:
  - port: 8501
    targetPort: 8501
    protocol: TCP
    name: http
  selector:
    app: admin-board
```

#### `kubernetes/ingress.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: admin-board-ingress
  namespace: aicallgo-staging
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    # Optional: IP whitelist (uncomment and set IPs)
    # nginx.ingress.kubernetes.io/whitelist-source-range: "1.2.3.4/32,5.6.7.8/32"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - admin-staging.aicallgo.com
    secretName: admin-board-tls
  rules:
  - host: admin-staging.aicallgo.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: admin-board
            port:
              number: 8501
```

#### `kubernetes/configmap.yaml`
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: admin-board-config
  namespace: aicallgo-staging
data:
  web-frontend-url: "https://staging.aicallgo.com"
  session-timeout-hours: "8"
  db-pool-size: "5"
  db-max-overflow: "5"
```

#### `kubernetes/secret.yaml.example`
```yaml
# This is an example. Create actual secret using kubectl or Terraform
apiVersion: v1
kind: Secret
metadata:
  name: admin-board-secrets
  namespace: aicallgo-staging
type: Opaque
stringData:
  database-url: "postgresql+asyncpg://user:pass@postgres-host:5432/dbname"
  admin-username: "admin"
  admin-password-hash: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5UpV.o/..."
```

### Resource Allocation

**Staging Environment**:
- **Replicas**: 1 (sufficient for admin use)
- **CPU Request**: 500m (0.5 cores)
- **CPU Limit**: 1000m (1 core)
- **Memory Request**: 512Mi
- **Memory Limit**: 1Gi

**Production Environment** (future):
- **Replicas**: 2 (high availability)
- **CPU Request**: 500m
- **CPU Limit**: 2000m (2 cores)
- **Memory Request**: 1Gi
- **Memory Limit**: 2Gi

### Security Configuration

**Network Policy** (optional, for additional security):
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: admin-board-netpol
  namespace: aicallgo-staging
spec:
  podSelector:
    matchLabels:
      app: admin-board
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8501
  egress:
  # Allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
  # Allow PostgreSQL
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
```

### Deployment Commands

```bash
# Build and push Docker image
cd /Users/blickt/Documents/src/aicallgo-infra-repo/services/admin-board
docker build -t registry.digitalocean.com/aicallgo-registry/admin-board:latest .
docker push registry.digitalocean.com/aicallgo-registry/admin-board:latest

# Create Kubernetes secrets (one-time)
kubectl create secret generic admin-board-secrets \
  --from-literal=database-url="postgresql+asyncpg://user:pass@host:5432/db" \
  --from-literal=admin-username="admin" \
  --from-literal=admin-password-hash="$2b$12$..." \
  -n aicallgo-staging

# Apply Kubernetes manifests
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/ingress.yaml

# Check deployment status
kubectl get pods -n aicallgo-staging -l app=admin-board
kubectl logs -f deployment/admin-board -n aicallgo-staging

# Access admin board
# https://admin-staging.aicallgo.com
```

---

## Implementation Phases

### Phase 1: Core Setup (Foundation)
**Estimated Time: 2-3 days**

**Tasks**:
1. Create project directory structure at `/services/admin-board/`
2. Set up `requirements.txt` with all dependencies
3. Configure `config/settings.py` with environment variables
4. Implement `config/auth.py` with bcrypt authentication
5. Set up `database/connection.py` with async SQLAlchemy
6. Create `database/models.py` (import/symlink from web-backend)
7. Create `static/custom.css` with design system CSS
8. Build `app.py` main entry point with authentication
9. Test local setup with port-forward to staging database

**Deliverables**:
- ✅ Working authentication system
- ✅ Database connection established
- ✅ Custom CSS matching nextjs-frontend theme
- ✅ Project structure complete

---

### Phase 2: Read-Only Pages (Data Display)
**Estimated Time: 4-5 days**

**Tasks**:
10. Build `components/cards.py`, `components/tables.py`, `components/charts.py`
11. Implement `services/user_service.py` (read operations)
12. Implement `services/business_service.py` (read operations)
13. Implement `services/call_log_service.py` (read operations)
14. Implement `services/billing_service.py` (read operations)
15. Build `pages/1_📊_Dashboard.py` with KPIs and charts
16. Build `pages/2_👥_Users.py` with search and detail view
17. Build `pages/3_🏢_Businesses.py` with filtering
18. Build `pages/4_📞_Call_Logs.py` with transcript viewer
19. Build `pages/5_💳_Billing.py` (read-only monitoring)
20. Implement `utils/formatters.py` (currency, dates, phones)

**Deliverables**:
- ✅ Dashboard with live metrics
- ✅ User browsing and search
- ✅ Business profile viewing
- ✅ Call log viewing with transcripts
- ✅ Billing data display

---

### Phase 3: Priority Features (Data Manipulation)
**Estimated Time: 5-6 days**

**Tasks**:
21. Implement `services/entitlement_service.py` (full CRUD)
22. Build `pages/6_⚡_Entitlements.py` with feature override management
    - User search and selection
    - Current plan and features display
    - Override creation form
    - Confirmation dialogs
    - Validation logic
23. Implement `services/credit_service.py` (full CRUD)
24. Build `pages/7_💰_Credits.py` with credit adjustment
    - User credit balance display
    - Transaction history
    - Adjustment form with validation
    - Preview and confirmation
    - Large amount warnings
25. Implement `services/audit_service.py` for audit logging
26. Add audit trail logging to all mutations
27. Implement transaction safety (rollback on error)
28. Add comprehensive validation to all forms

**Deliverables**:
- ✅ Feature entitlement management (grant/revoke access)
- ✅ Credit adjustment with audit trail
- ✅ Transaction safety and rollback
- ✅ Validation and confirmation dialogs

---

### Phase 4: Additional Features
**Estimated Time: 2-3 days**

**Tasks**:
29. Build `pages/8_🎟️_Promotions.py` (read-only promo code tracking)
30. Build `pages/9_📅_Appointments.py` (appointment viewing)
31. Build `pages/10_🔧_System.py` (health checks, database stats)
32. Implement CSV export functionality for all tables
33. Add auto-refresh to Dashboard (60s interval)
34. Implement manual refresh buttons on all pages
35. Add error handling and user-friendly error messages
36. Optimize queries with proper indexing

**Deliverables**:
- ✅ Promotion code tracking
- ✅ Appointment management
- ✅ System health monitoring
- ✅ CSV export functionality

---

### Phase 5: Deployment
**Estimated Time: 2-3 days**

**Tasks**:
37. Create `Dockerfile` with multi-stage build
38. Build Docker image locally and test
39. Create Kubernetes manifests (deployment, service, ingress, secrets)
40. Configure Digital Ocean registry access
41. Push image to registry
42. Deploy to staging cluster
43. Configure DNS (admin-staging.aicallgo.com)
44. Set up SSL certificate via cert-manager
45. Test end-to-end functionality in staging
46. Implement IP whitelist (optional)
47. Create deployment documentation
48. Create user guide for admins

**Deliverables**:
- ✅ Docker image in DO registry
- ✅ Kubernetes deployment in staging
- ✅ DNS configured with SSL
- ✅ End-to-end tested
- ✅ Documentation complete

---

**Total Estimated Time: 15-20 days**

---

## Testing Strategy

### Local Testing (Pre-Deployment)

1. **Database Connection Test**:
   ```bash
   # Port-forward to staging PostgreSQL
   kubectl port-forward svc/postgres 5432:5432 -n aicallgo-staging

   # Set DATABASE_URL to localhost
   export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db"

   # Run Streamlit locally
   streamlit run app.py
   ```

2. **Authentication Test**:
   - Test valid login
   - Test invalid credentials
   - Test session timeout
   - Test logout functionality

3. **Read Operations Test**:
   - Search users with various filters
   - View business details
   - Load call logs with date range filters
   - Check billing data accuracy

4. **Write Operations Test** (on test users):
   - Create entitlement override
   - Delete entitlement override
   - Adjust credits (positive and negative)
   - Verify transaction creation
   - Test rollback on error

5. **Validation Test**:
   - Test required field validation
   - Test min/max constraints
   - Test confirmation dialogs
   - Test large amount warnings

### Integration Testing (Staging)

1. **Data Accuracy**:
   - Compare admin board data with web-backend API responses
   - Verify credit calculations match
   - Check entitlement logic matches backend

2. **Performance Testing**:
   - Load dashboard with 10k+ users
   - Search performance with large datasets
   - Query optimization verification
   - Connection pool behavior under load

3. **Mutation Testing**:
   - Create overrides on real staging users
   - Adjust credits and verify in web-backend
   - Test transaction atomicity
   - Verify audit trail creation

4. **UI/UX Testing**:
   - Test at different viewport sizes (1280px, 1440px, 1920px)
   - Verify color scheme matches nextjs-frontend
   - Check responsive tables
   - Validate chart rendering

### Security Testing

1. **Authentication**:
   - Verify HTTPS redirect works
   - Test session timeout enforcement
   - Verify password is never logged

2. **Authorization**:
   - Verify all pages require authentication
   - Test direct URL access without login

3. **Database Security**:
   - Verify SQL injection protection (SQLAlchemy ORM)
   - Test connection pool limits
   - Verify read-write access scope

4. **Network Security**:
   - Test ingress firewall (if IP whitelist enabled)
   - Verify network policy (if enabled)

### User Acceptance Testing

1. **Admin Workflows**:
   - Find user by email
   - Grant feature access for 30 days
   - Revoke feature access
   - Adjust credits for refund
   - View call log transcript
   - Export user list to CSV

2. **Error Handling**:
   - Test invalid inputs
   - Test database connection failure
   - Test large dataset handling

---

## Success Metrics

### Performance Metrics

- **Dashboard Load Time**: < 3 seconds with 10k users
- **User Search**: < 1 second response time
- **Credit Adjustment**: < 2 seconds transaction time
- **Call Log Search**: < 3 seconds with 50k+ logs
- **Page Navigation**: Instant (Streamlit multipage)

### Reliability Metrics

- **Database Connection**: 99.9% uptime
- **Transaction Success Rate**: 100% (with proper error handling)
- **Data Consistency**: 100% (atomic transactions)
- **Rollback Success**: 100% on error

### Security Metrics

- **Authentication Success**: Only valid credentials accepted
- **Session Security**: Auto-logout after 8 hours
- **HTTPS Enforcement**: 100% of requests
- **Audit Trail**: 100% coverage of mutations

### Usability Metrics

- **Time to Find User**: < 5 seconds (search + select)
- **Time to Adjust Credits**: < 30 seconds (search + adjust + confirm)
- **Time to Grant Feature**: < 30 seconds (search + grant + confirm)
- **Admin Satisfaction**: Gather feedback after 2 weeks

---

## Future Enhancements (Post-Launch)

1. **Advanced Features**:
   - Bulk operations (grant feature to multiple users)
   - Scheduled credit grants
   - Automated trial extensions
   - Email notifications for admin actions

2. **Analytics**:
   - Admin action analytics
   - Usage trend graphs
   - Revenue forecasting
   - Churn prediction

3. **Integrations**:
   - Slack notifications for critical actions
   - Export to Google Sheets
   - Webhook triggers for external systems

4. **Multi-Admin**:
   - Database-backed admin users (instead of env var)
   - Role-based access control (read-only vs full admin)
   - Admin activity audit log with user attribution

5. **Performance**:
   - Real-time updates via WebSocket
   - Redis caching for frequently accessed data
   - Materialized views for complex queries

---

## Appendix

### A. Useful Database Queries

**Get users with low credits**:
```sql
SELECT u.email, cb.total_balance
FROM users u
JOIN credit_balances cb ON u.id = cb.user_id
WHERE cb.total_balance < 5.00
ORDER BY cb.total_balance ASC
LIMIT 50;
```

**Get users with active overrides**:
```sql
SELECT u.email, f.feature_key, ufo.has_access, ufo.expires_at
FROM user_feature_overrides ufo
JOIN users u ON ufo.user_id = u.id
JOIN features f ON ufo.feature_id = f.id
WHERE ufo.expires_at IS NULL OR ufo.expires_at > NOW()
ORDER BY u.email;
```

**Get high-value users (by call volume)**:
```sql
SELECT u.email, COUNT(cl.id) as call_count
FROM users u
JOIN businesses b ON u.id = b.user_id
JOIN call_log cl ON b.id = cl.business_id
WHERE cl.call_start_time > NOW() - INTERVAL '30 days'
GROUP BY u.id, u.email
ORDER BY call_count DESC
LIMIT 50;
```

### B. Formatters Utility

**`utils/formatters.py`**:
```python
from decimal import Decimal
from datetime import datetime
import pytz
import phonenumbers
import humanize

def format_currency(amount: Decimal) -> str:
    """Format decimal as currency"""
    return f"${amount:,.2f}"

def format_datetime(dt: datetime, timezone: str = "America/Los_Angeles") -> str:
    """Format datetime with timezone"""
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    tz = pytz.timezone(timezone)
    local_dt = dt.astimezone(tz)
    return local_dt.strftime('%Y-%m-%d %H:%M %Z')

def format_phone(phone: str, region: str = "US") -> str:
    """Format phone number"""
    try:
        parsed = phonenumbers.parse(phone, region)
        return phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.NATIONAL
        )
    except:
        return phone

def format_duration(seconds: int) -> str:
    """Format duration in seconds to MM:SS"""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"

def format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time (e.g., '2 hours ago')"""
    return humanize.naturaltime(dt)

def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."
```

---

## Conclusion

This implementation plan provides a comprehensive roadmap for building the AICallGO Admin Board. The design mirrors the nextjs-frontend aesthetics while leveraging Streamlit's rapid development capabilities. The focus on entitlements and credits management addresses the highest priority admin needs, with transaction safety and audit logging ensuring data integrity.

**Key Success Factors**:
- ✅ Desktop-first design optimized for admin workflows
- ✅ Direct database access for real-time data
- ✅ Environment-based authentication for simplicity
- ✅ Transaction safety with rollback on errors
- ✅ Comprehensive audit trail for compliance
- ✅ Kubernetes deployment for production-readiness

**Next Steps**:
1. Review and approve this plan
2. Begin Phase 1 implementation
3. Iterative development with testing at each phase
4. Deploy to staging and gather admin feedback
5. Iterate based on real-world usage

This admin board will significantly improve operational efficiency by providing a powerful, safe, and intuitive interface for managing AICallGO's users, features, and credits.
