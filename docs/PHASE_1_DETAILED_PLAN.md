# Phase 1 Detailed Implementation Plan: Admin Board Core Setup

**Document Version:** 1.0
**Date:** 2025-10-22
**Status:** Approved for Implementation

---

## Framework Decision

### Selected Approach: Hybrid - Streamlit First, Evaluate Later

**Decision Summary:**
- ✅ **Phase 1-2**: Implement with Streamlit (fast development, 3-4 days total)
- ✅ **Evaluation Checkpoint**: Before Phase 3, assess if Streamlit meets needs
- ✅ **Migration Option**: Can migrate to Flask-Admin if needed (2-3 days, database layer reusable)

### Rationale

Based on project requirements analysis:

| Requirement | Streamlit Fit | Decision Weight |
|-------------|---------------|-----------------|
| **Speed to first version** | ⭐⭐⭐⭐⭐ Fastest | High priority (hybrid approach) |
| **Design consistency** | ⭐⭐⭐⭐ Good with CSS | Important (can achieve with custom CSS) |
| **Simple auth** | ⭐⭐⭐⭐⭐ Perfect fit | Sufficient (username/password) |
| **Production readiness** | ⭐⭐⭐ Adequate | Can evaluate after Phase 2 |

### Framework Comparison

#### Streamlit (Selected for Phase 1-2)
**Pros:**
- ⚡ 50% faster development than Flask/Django
- 📊 Built-in components: tables, charts, forms
- 🔄 Auto-refresh and real-time updates
- 🎨 Can customize with CSS to match frontend theme

**Cons:**
- 🎨 Less design control than Flask
- 🔒 Basic auth only (adequate for our needs)
- 📱 Desktop-first (OK for admin tool)

#### Flask-Admin (Migration Option)
**Pros:**
- 🔧 Full HTML/CSS/JS control
- 🔐 Mature authentication (Flask-Login, RBAC)
- ⚡ Better performance with large datasets
- 🎨 Can perfectly match Next.js frontend

**Cons:**
- ⏱️ 2-3x longer development time
- 📝 More boilerplate (templates, forms, routes)

#### Django Admin (Rejected)
**Reason:** Framework mismatch - backend is FastAPI with SQLAlchemy, not Django ORM

---

## Phase 1 Implementation Plan

### Overview
**Goal:** Create working admin board with authentication, database connection, and design system.

**Timeline:** 8.5 hours (~1-1.5 days of focused work)

**Deliverables:**
- ✅ Working authentication system
- ✅ Database connection established
- ✅ Custom CSS matching nextjs-frontend theme
- ✅ Project structure complete

---

## Task Breakdown

### Task 1: Project Directory Structure (30 mins)

Create the following directory structure:

```
/services/admin-board/
├── app.py                    # Main Streamlit entry point
├── requirements.txt          # Python dependencies
├── Dockerfile               # Container definition (Phase 6)
├── .env.example             # Example environment variables
├── .streamlit/
│   └── config.toml          # Streamlit configuration
├── config/
│   ├── __init__.py
│   ├── settings.py          # Environment variable management
│   └── auth.py              # Authentication logic
├── database/
│   ├── __init__.py
│   ├── connection.py        # Async SQLAlchemy setup
│   └── models.py            # Import models from web-backend
├── static/
│   └── custom.css           # Design system CSS (purple/green theme)
├── components/              # Reusable UI components (Phase 2+)
│   └── __init__.py
├── services/                # Business logic services (Phase 2+)
│   └── __init__.py
├── utils/                   # Helper functions (Phase 2+)
│   └── __init__.py
└── pages/                   # Streamlit pages (Phase 2+)
    └── __init__.py
```

**Commands:**
```bash
cd /services/admin-board
mkdir -p .streamlit config database static components services utils pages
touch app.py requirements.txt .env.example
touch .streamlit/config.toml
touch config/{__init__.py,settings.py,auth.py}
touch database/{__init__.py,connection.py,models.py}
touch static/custom.css
touch components/__init__.py services/__init__.py utils/__init__.py pages/__init__.py
```

---

### Task 2: Requirements.txt (20 mins)

Create `requirements.txt` with matching versions from web-backend:

```txt
# Core Framework
streamlit==1.32.0
streamlit-authenticator==0.3.2

# Database (matching web-backend pyproject.toml)
sqlalchemy==2.0.23
asyncpg==0.30.0
psycopg2-binary==2.9.9

# Security (matching web-backend)
passlib[bcrypt]==1.7.4
bcrypt==4.1.2

# Environment & Config
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0

# Data Processing (for Phase 2+)
pandas==2.1.4
numpy==1.26.3

# Charts & Visualization (for Phase 2+)
plotly==5.18.0
altair==5.2.0

# Utilities
pytz==2023.3
phonenumbers==8.13.26
```

**Why these versions:**
- SQLAlchemy 2.0.23: Matches web-backend for model compatibility
- Streamlit 1.32.0: Latest stable with async support
- Pydantic 2.5.0: Matches web-backend settings pattern

---

### Task 3: .streamlit/config.toml (15 mins)

Configure Streamlit appearance to match Next.js frontend:

```toml
[theme]
# Colors matching tailwind.config.ts
primaryColor = "#5f8a4e"        # purple-500 from frontend
backgroundColor = "#ffffff"      # white
secondaryBackgroundColor = "#f9fafb"  # gray-50
textColor = "#111827"           # gray-900
font = "sans serif"

[server]
port = 8501
enableCORS = false
enableXsrfProtection = true
maxUploadSize = 200

[browser]
gatherUsageStats = false
serverAddress = "localhost"
serverPort = 8501

[runner]
magicEnabled = false
fastReruns = true
```

**Color Rationale:**
- Primary: `#5f8a4e` matches the purple-500 from Next.js frontend (actually green-toned)
- Background colors match the gray scale from frontend
- Consistent with `services/nextjs-frontend/tailwind.config.ts`

---

### Task 4: Config/Settings.py (45 mins)

Environment-based configuration using Pydantic (matches web-backend pattern):

```python
"""
Application settings using Pydantic Settings.
Matches pattern from web-backend/app/core/config.py
"""
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App Configuration
    APP_ENV: str = "development"
    APP_NAME: str = "AICallGO Admin Board"
    DEBUG: bool = True

    # Database Configuration (reuse from web-backend)
    DATABASE_URL: PostgresDsn

    @property
    def async_database_url(self) -> str:
        """Convert DATABASE_URL to async format for SQLAlchemy async engine."""
        url = str(self.DATABASE_URL)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            if "sslmode=" in url:
                url = url.replace("sslmode=", "ssl=")
        return url

    # Admin Authentication
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str  # bcrypt hash
    SESSION_TIMEOUT_HOURS: int = 8

    # Streamlit Configuration
    STREAMLIT_SERVER_PORT: int = 8501
    STREAMLIT_SERVER_ADDRESS: str = "0.0.0.0"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
```

**Environment Variables Required:**
```env
DATABASE_URL=postgresql://user:password@host:5432/database
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$...
APP_ENV=development
DEBUG=true
SESSION_TIMEOUT_HOURS=8
```

---

### Task 5: Config/Auth.py (1 hour)

Simple session-based authentication with bcrypt:

```python
"""
Authentication module for admin board.
Uses Streamlit session state and bcrypt password verification.
Matches security pattern from web-backend/app/core/security.py
"""
import streamlit as st
from passlib.context import CryptContext
from datetime import datetime, timedelta
from config.settings import settings

# Password hashing context (matches web-backend)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its bcrypt hash.
    Matches web-backend/app/core/security.py:verify_password()
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """
    Generate bcrypt hash for a password.
    Use this to generate ADMIN_PASSWORD_HASH for .env file.
    """
    return pwd_context.hash(password)


def init_session_state():
    """Initialize session state variables if not present."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None


def check_session_timeout() -> bool:
    """
    Check if session has timed out.
    Returns True if session is still valid, False if timed out.
    """
    if st.session_state.login_time:
        timeout = timedelta(hours=settings.SESSION_TIMEOUT_HOURS)
        if datetime.now() - st.session_state.login_time > timeout:
            logout()
            return False
    return True


def login(username: str, password: str) -> bool:
    """
    Authenticate user with username and password.
    Returns True if authentication successful, False otherwise.
    """
    if username == settings.ADMIN_USERNAME:
        if verify_password(password, settings.ADMIN_PASSWORD_HASH):
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.login_time = datetime.now()
            return True
    return False


def logout():
    """Clear session state and log out user."""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.login_time = None


def require_auth() -> bool:
    """
    Check if user is authenticated and session is valid.
    Use this as a gate on protected pages.

    Returns:
        bool: True if authenticated and session valid, False otherwise
    """
    init_session_state()
    if not st.session_state.authenticated:
        return False
    return check_session_timeout()


def login_form():
    """
    Display login form and handle authentication.
    Call this when require_auth() returns False.
    """
    st.title("🔐 AICallGO Admin Login")
    st.markdown("### Access restricted to authorized administrators")

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        submit = st.form_submit_button("Login", use_container_width=True)

        if submit:
            if not username or not password:
                st.error("❌ Please enter both username and password")
            elif login(username, password):
                st.success("✅ Login successful! Redirecting...")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")

    # Help text
    with st.expander("Need help?"):
        st.markdown("""
        **Forgot credentials?**
        Contact your system administrator to reset your password.

        **Security note:**
        Sessions expire after 8 hours of inactivity.
        """)
```

**Generate Password Hash:**
```bash
python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('YourSecurePassword123!'))"
```

---

### Task 6: Database/Connection.py (1 hour)

Async SQLAlchemy database connection:

```python
"""
Database connection module using async SQLAlchemy.
Matches pattern from web-backend but uses async engine.
"""
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from sqlalchemy import text
from contextlib import asynccontextmanager
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Create async engine
# Configuration matches web-backend connection pooling strategy
engine = create_async_engine(
    settings.async_database_url,
    pool_size=5,              # Smaller pool for admin tool
    max_overflow=10,          # Total connections: 15
    pool_pre_ping=True,       # Check connections before use
    pool_recycle=300,         # Recycle after 5 minutes
    echo=settings.DEBUG       # Log SQL in debug mode
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@asynccontextmanager
async def get_async_session():
    """
    Get async database session.

    Usage:
        async with get_async_session() as session:
            result = await session.execute(query)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def check_db_health() -> tuple[bool, str]:
    """
    Check database connection health.

    Returns:
        tuple: (is_healthy: bool, message: str)
    """
    try:
        async with get_async_session() as session:
            # Simple query to test connection
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()

            # Also check critical tables exist
            tables_query = text("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('users', 'businesses', 'call_log', 'subscriptions')
            """)
            table_count = await session.execute(tables_query)
            tables_exist = table_count.scalar()

            if tables_exist < 4:
                return False, f"Missing critical tables (found {tables_exist}/4)"

            return True, f"✅ Connected - {count} users, all critical tables present"

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False, f"❌ Connection failed: {str(e)[:100]}"


async def get_db_info() -> dict:
    """
    Get database information for system info display.

    Returns:
        dict: Database statistics
    """
    try:
        async with get_async_session() as session:
            queries = {
                "users": "SELECT COUNT(*) FROM users",
                "businesses": "SELECT COUNT(*) FROM businesses",
                "call_logs": "SELECT COUNT(*) FROM call_log",
                "subscriptions": "SELECT COUNT(*) FROM subscriptions WHERE status = 'active'"
            }

            info = {}
            for key, query in queries.items():
                result = await session.execute(text(query))
                info[key] = result.scalar()

            return info
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {}
```

---

### Task 7: Database/Models.py (30 mins)

Import models from web-backend (single source of truth):

```python
"""
Database models imported from web-backend.
This ensures schema consistency - admin board uses exact same models.
"""
import sys
from pathlib import Path

# Add web-backend to Python path
backend_path = Path(__file__).parent.parent.parent / "web-backend"
sys.path.insert(0, str(backend_path))

# Import all models from web-backend
# See: services/web-backend/app/models/__init__.py for full list
from app.models import (
    # Core models
    User,
    Business,
    BusinessHour,
    CoreService,

    # Call & Communication
    CallLog,
    Recording,
    AIAgentConfiguration,
    CustomQuestion,

    # Billing & Subscriptions
    Subscription,
    SubscriptionAudit,
    Invoice,
    Product,
    Price,
    UsageRecord,
    UsageSummary,

    # Credits
    CreditBalance,
    CreditTransaction,
    PaymentMethod,

    # Features & Plans
    Feature,
    Plan,
    PlanFeature,
    UserFeatureOverride,

    # Phone & Twilio
    TwilioPhoneNumber,

    # Promotions
    PromotionCode,
    PromotionCodeUsage,

    # Appointments
    Appointment,
    AppointmentEndUser,
    AppointmentSchedulingConfig,
    NylasConnection,

    # Events & Notifications
    EventNotification,
    EventType,
    NonCustomerEvent,
    NonCustomerEventType,
    CustomerEvent,
    CustomerEventConfig,

    # Webhooks
    WebhookEvent,

    # Analytics & Tracking
    IntegrationInterest,
    CustomIntegrationRequest,
    SignupEvent,
    ConversionMetric,
    ABTestResult,
    DeviceFingerprint,
    UserDeviceFingerprint,
    MetaPixelEvent,
    UserMetaTracking,

    # Human Agents
    HumanAgent,

    # FAQ
    FAQ,
)

from app.db.base_class import Base

# Export all models
__all__ = [
    "Base",
    # Core
    "User",
    "Business",
    "BusinessHour",
    "CoreService",
    # Call
    "CallLog",
    "Recording",
    "AIAgentConfiguration",
    # Billing
    "Subscription",
    "Invoice",
    "UsageRecord",
    "UsageSummary",
    # Credits
    "CreditBalance",
    "CreditTransaction",
    "PaymentMethod",
    # Features
    "Feature",
    "Plan",
    "PlanFeature",
    "UserFeatureOverride",
    # Phone
    "TwilioPhoneNumber",
    # Promotions
    "PromotionCode",
    "PromotionCodeUsage",
    # Appointments
    "Appointment",
    "AppointmentSchedulingConfig",
    # Events
    "EventNotification",
    "CustomerEvent",
    # All others as needed
]
```

**Why Import Instead of Duplicate:**
- ✅ Single source of truth for database schema
- ✅ Automatic updates when web-backend models change
- ✅ No risk of schema drift between services
- ✅ Reuses all relationships and constraints

---

### Task 8: Static/Custom.css (1.5 hours)

CSS matching Next.js frontend design system:

```css
/*
 * AICallGO Admin Board Custom Styles
 * Matches color scheme from services/nextjs-frontend/tailwind.config.ts
 *
 * Color Palette:
 * - Primary (purple/green): #5f8a4e (purple-500), #456535 (purple-600)
 * - Gray scale: #f9fafb (50), #e5e7eb (200), #6b7280 (500), #111827 (900)
 * - Accent: #f1f9ef (purple-50), #dff1d9 (purple-100)
 */

/* ==================== CSS Variables ==================== */
:root {
    /* Primary Colors (purple in config, but actually green-toned) */
    --purple-50: #f1f9ef;
    --purple-100: #dff1d9;
    --purple-200: #beddad;
    --purple-500: #5f8a4e;
    --purple-600: #456535;
    --purple-700: #3b542d;

    /* Gray Scale */
    --gray-50: #f9fafb;
    --gray-100: #f3f4f6;
    --gray-200: #e5e7eb;
    --gray-300: #d1d5db;
    --gray-400: #9ca3af;
    --gray-500: #6b7280;
    --gray-600: #4b5563;
    --gray-900: #111827;

    /* Semantic Colors */
    --success-bg: var(--purple-50);
    --success-border: var(--purple-500);
    --success-text: var(--purple-700);
    --error-bg: #fef2f2;
    --error-border: #dc2626;
    --error-text: #991b1b;
    --warning-bg: #fffbeb;
    --warning-border: #f59e0b;

    /* Spacing & Sizing */
    --radius: 0.5rem;
    --spacing-xs: 0.5rem;
    --spacing-sm: 1rem;
    --spacing-md: 1.5rem;
    --spacing-lg: 2rem;
    --spacing-xl: 3rem;

    /* Typography */
    --font-size-xs: 0.75rem;
    --font-size-sm: 0.875rem;
    --font-size-base: 1rem;
    --font-size-lg: 1.125rem;
    --font-size-xl: 1.25rem;
    --font-size-2xl: 1.5rem;
}

/* ==================== Global Styles ==================== */
.main {
    background-color: var(--gray-50) !important;
    padding: var(--spacing-lg);
}

/* ==================== Sidebar Styling ==================== */
[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid var(--gray-200) !important;
    padding-top: var(--spacing-md);
}

[data-testid="stSidebar"] .block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}

/* Sidebar header */
[data-testid="stSidebar"] h2 {
    font-size: var(--font-size-xl);
    font-weight: 600;
    color: var(--gray-900);
    margin-bottom: var(--spacing-sm);
}

/* Sidebar dividers */
[data-testid="stSidebar"] hr {
    margin: var(--spacing-md) 0;
    border-color: var(--gray-200);
}

/* ==================== Typography ==================== */
h1, h2, h3, h4, h5, h6 {
    color: var(--gray-900) !important;
    font-weight: 600 !important;
}

h1 {
    font-size: var(--font-size-2xl) !important;
    margin-bottom: var(--spacing-md) !important;
}

h2 {
    font-size: var(--font-size-xl) !important;
}

h3 {
    font-size: var(--font-size-lg) !important;
}

p {
    color: var(--gray-600);
    line-height: 1.6;
}

/* ==================== Buttons ==================== */
.stButton button {
    background-color: var(--purple-500) !important;
    color: white !important;
    border-radius: var(--radius) !important;
    border: none !important;
    padding: 0.5rem 1rem !important;
    font-weight: 500 !important;
    font-size: var(--font-size-sm) !important;
    transition: background-color 0.2s ease !important;
}

.stButton button:hover {
    background-color: var(--purple-600) !important;
    border: none !important;
}

.stButton button:active {
    background-color: var(--purple-700) !important;
}

/* Secondary button style */
.stButton button[kind="secondary"] {
    background-color: var(--gray-200) !important;
    color: var(--gray-900) !important;
}

.stButton button[kind="secondary"]:hover {
    background-color: var(--gray-300) !important;
}

/* ==================== Cards & Containers ==================== */
/* Expanders (collapsible sections) */
.stExpander {
    background-color: white !important;
    border: 1px solid var(--gray-200) !important;
    border-radius: var(--radius) !important;
    margin-bottom: var(--spacing-sm);
}

.stExpander [data-testid="stExpanderDetails"] {
    padding: var(--spacing-md);
}

/* Containers */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
    background-color: white;
    padding: var(--spacing-md);
    border-radius: var(--radius);
    border: 1px solid var(--gray-200);
}

/* ==================== Alerts & Messages ==================== */
/* Success messages */
.stSuccess {
    background-color: var(--success-bg) !important;
    border-left: 4px solid var(--success-border) !important;
    border-radius: var(--radius) !important;
    padding: var(--spacing-sm) var(--spacing-md) !important;
    color: var(--success-text) !important;
}

/* Error messages */
.stError, .stException {
    background-color: var(--error-bg) !important;
    border-left: 4px solid var(--error-border) !important;
    border-radius: var(--radius) !important;
    padding: var(--spacing-sm) var(--spacing-md) !important;
    color: var(--error-text) !important;
}

/* Warning messages */
.stWarning {
    background-color: var(--warning-bg) !important;
    border-left: 4px solid var(--warning-border) !important;
    border-radius: var(--radius) !important;
    padding: var(--spacing-sm) var(--spacing-md) !important;
}

/* Info messages */
.stInfo {
    background-color: #eff6ff !important;
    border-left: 4px solid #3b82f6 !important;
    border-radius: var(--radius) !important;
    padding: var(--spacing-sm) var(--spacing-md) !important;
}

/* ==================== Forms & Inputs ==================== */
/* Text inputs */
.stTextInput input, .stTextArea textarea {
    border: 1px solid var(--gray-200) !important;
    border-radius: var(--radius) !important;
    padding: 0.5rem !important;
    font-size: var(--font-size-base) !important;
}

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--purple-500) !important;
    box-shadow: 0 0 0 3px rgba(95, 138, 78, 0.1) !important;
    outline: none !important;
}

/* Select boxes */
.stSelectbox select {
    border: 1px solid var(--gray-200) !important;
    border-radius: var(--radius) !important;
    padding: 0.5rem !important;
}

.stSelectbox select:focus {
    border-color: var(--purple-500) !important;
    box-shadow: 0 0 0 3px rgba(95, 138, 78, 0.1) !important;
}

/* Number inputs */
.stNumberInput input {
    border: 1px solid var(--gray-200) !important;
    border-radius: var(--radius) !important;
}

/* Date inputs */
.stDateInput input {
    border: 1px solid var(--gray-200) !important;
    border-radius: var(--radius) !important;
}

/* ==================== Tables & DataFrames ==================== */
.dataframe {
    border: 1px solid var(--gray-200) !important;
    border-radius: var(--radius) !important;
    overflow: hidden;
    font-size: var(--font-size-sm) !important;
}

.dataframe thead th {
    background-color: var(--gray-50) !important;
    color: var(--gray-900) !important;
    font-weight: 600 !important;
    border-bottom: 2px solid var(--gray-200) !important;
    padding: 0.75rem !important;
    text-align: left !important;
}

.dataframe tbody tr {
    border-bottom: 1px solid var(--gray-200) !important;
}

.dataframe tbody tr:hover {
    background-color: var(--gray-50) !important;
}

.dataframe tbody td {
    padding: 0.75rem !important;
    color: var(--gray-700) !important;
}

/* Alternating row colors */
.dataframe tbody tr:nth-child(even) {
    background-color: var(--gray-50) !important;
}

/* ==================== Status Badges ==================== */
.badge-success {
    background-color: var(--purple-100) !important;
    color: var(--purple-700) !important;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: var(--font-size-xs);
    font-weight: 500;
    display: inline-block;
}

.badge-error {
    background-color: var(--error-bg) !important;
    color: var(--error-text) !important;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: var(--font-size-xs);
    font-weight: 500;
    display: inline-block;
}

.badge-warning {
    background-color: var(--warning-bg) !important;
    color: #92400e !important;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: var(--font-size-xs);
    font-weight: 500;
    display: inline-block;
}

.badge-info {
    background-color: #e0f2fe !important;
    color: #075985 !important;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: var(--font-size-xs);
    font-weight: 500;
    display: inline-block;
}

/* ==================== Charts (Plotly/Altair) ==================== */
.js-plotly-plot {
    border-radius: var(--radius);
    border: 1px solid var(--gray-200);
}

/* ==================== Spinner ==================== */
.stSpinner > div {
    border-top-color: var(--purple-500) !important;
}

/* ==================== Tabs ==================== */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
}

.stTabs [data-baseweb="tab"] {
    color: var(--gray-600) !important;
    border-bottom: 2px solid transparent !important;
    padding: 0.5rem 1rem !important;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--purple-600) !important;
}

.stTabs [aria-selected="true"] {
    color: var(--purple-600) !important;
    border-bottom-color: var(--purple-500) !important;
}

/* ==================== Metrics ==================== */
[data-testid="stMetricValue"] {
    font-size: var(--font-size-2xl) !important;
    font-weight: 600 !important;
    color: var(--gray-900) !important;
}

[data-testid="stMetricLabel"] {
    font-size: var(--font-size-sm) !important;
    color: var(--gray-500) !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

[data-testid="stMetricDelta"] {
    font-size: var(--font-size-sm) !important;
}

/* ==================== Code Blocks ==================== */
code {
    background-color: var(--gray-100) !important;
    color: var(--gray-900) !important;
    padding: 0.2rem 0.4rem !important;
    border-radius: 0.25rem !important;
    font-size: var(--font-size-sm) !important;
}

pre {
    background-color: var(--gray-900) !important;
    color: var(--gray-100) !important;
    padding: var(--spacing-md) !important;
    border-radius: var(--radius) !important;
    overflow-x: auto;
}

/* ==================== Links ==================== */
a {
    color: var(--purple-600) !important;
    text-decoration: none !important;
}

a:hover {
    color: var(--purple-700) !important;
    text-decoration: underline !important;
}

/* ==================== Scrollbar ==================== */
::-webkit-scrollbar {
    width: 10px;
    height: 10px;
}

::-webkit-scrollbar-track {
    background: var(--gray-100);
}

::-webkit-scrollbar-thumb {
    background: var(--gray-300);
    border-radius: 5px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--gray-400);
}
```

---

### Task 9: App.py Main Entry Point (2 hours)

Main Streamlit application with authentication:

```python
"""
AICallGO Admin Board - Main Application
Entry point for Streamlit admin dashboard
"""
import streamlit as st
import asyncio
from config.settings import settings
from config.auth import require_auth, login_form, logout
from database.connection import check_db_health, get_db_info

# ====================
# Page Configuration
# ====================
st.set_page_config(
    page_title="AICallGO Admin Board",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "AICallGO Admin Board - Internal administration tool"
    }
)

# ====================
# Load Custom CSS
# ====================
with open("static/custom.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ====================
# Authentication Gate
# ====================
if not require_auth():
    login_form()
    st.stop()

# ====================
# Sidebar
# ====================
with st.sidebar:
    # Header
    st.header("📊 Admin Board")
    st.write(f"👤 **{st.session_state.username}**")
    st.caption(f"Environment: {settings.APP_ENV}")
    st.divider()

    # Navigation (Phase 2+)
    st.markdown("### Navigation")
    st.info("""
    **Phase 2 Pages** (Coming Soon):
    - 📊 Dashboard
    - 👥 Users
    - 🏢 Businesses
    - 📞 Call Logs
    - 💳 Billing

    **Phase 3 Pages** (Coming Later):
    - ⚡ Entitlements
    - 💰 Credits
    """)
    st.divider()

    # System Health Check
    st.markdown("### System Health")
    if st.button("Check Database", use_container_width=True):
        with st.spinner("Checking connection..."):
            is_healthy, message = asyncio.run(check_db_health())
            if is_healthy:
                st.success(message)

                # Show database stats
                with st.expander("Database Statistics"):
                    db_info = asyncio.run(get_db_info())
                    if db_info:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Users", db_info.get('users', 0))
                            st.metric("Businesses", db_info.get('businesses', 0))
                        with col2:
                            st.metric("Call Logs", db_info.get('call_logs', 0))
                            st.metric("Active Subs", db_info.get('subscriptions', 0))
            else:
                st.error(message)

    st.divider()

    # Logout
    if st.button("🚪 Logout", use_container_width=True, type="secondary"):
        logout()
        st.rerun()

# ====================
# Main Content
# ====================
st.title("📊 AICallGO Admin Dashboard")
st.markdown("### Welcome to the Admin Board")

# Welcome message
st.info("""
**👋 Phase 1 Complete!**

This admin board is now connected to the database and ready for development.
Use the sidebar to navigate between pages (coming in Phase 2).
""")

# System status card
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### ✅ Authentication")
    st.success("Working")
    st.caption("Session-based auth with bcrypt")

with col2:
    st.markdown("### ✅ Database")
    st.success("Connected")
    st.caption(f"PostgreSQL (async)")

with col3:
    st.markdown("### ✅ Design System")
    st.success("Applied")
    st.caption("Matching Next.js frontend")

# Phase 1 completion checklist
st.markdown("---")
st.markdown("## Phase 1 Deliverables")

checklist = [
    ("✅", "Working authentication system", "Login/logout with bcrypt password verification"),
    ("✅", "Database connection established", "Async SQLAlchemy with connection pooling"),
    ("✅", "Custom CSS matching frontend", "Purple/green theme from tailwind.config.ts"),
    ("✅", "Project structure complete", "All directories and base files created"),
]

for status, title, description in checklist:
    with st.expander(f"{status} {title}"):
        st.write(description)

# Next steps
st.markdown("---")
st.markdown("## 🔜 Next Steps: Phase 2")

st.markdown("""
**Phase 2 will add read-only pages:**

1. **Dashboard** - KPIs, recent activity, charts
2. **Users** - Search, view, and browse users
3. **Businesses** - Business profiles and configuration
4. **Call Logs** - Call history with transcripts
5. **Billing** - Subscription and invoice monitoring

**Timeline:** 4-5 days

After Phase 2, we'll evaluate if Streamlit meets needs or if we should migrate to Flask-Admin for Phase 3 (data manipulation features).
""")

# System information
st.markdown("---")
with st.expander("🔧 System Information"):
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Environment:**", settings.APP_ENV)
        st.write("**App Name:**", settings.APP_NAME)
        st.write("**Debug Mode:**", settings.DEBUG)
        st.write("**Session Timeout:**", f"{settings.SESSION_TIMEOUT_HOURS} hours")

    with col2:
        # Hide credentials from database URL
        db_url = str(settings.DATABASE_URL)
        db_parts = db_url.split('@')
        if len(db_parts) > 1:
            db_display = f"...@{db_parts[1]}"
        else:
            db_display = "Connected"
        st.write("**Database:**", db_display)
        st.write("**Streamlit Version:**", st.__version__)
        st.write("**Python Version:**", "3.12+")
```

---

### Task 10: Local Testing (1 hour)

#### Step 1: Generate Admin Password Hash

```bash
# Install passlib if not already installed
pip install "passlib[bcrypt]"

# Generate password hash
python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('YourSecurePassword123!'))"

# Example output: $2b$12$KIX8tWq2mZQX5V...
```

#### Step 2: Create .env File

Create `/services/admin-board/.env`:

```env
# Database Connection
DATABASE_URL=postgresql://aicallgo_user:password@localhost:5432/aicallgo_staging

# Admin Authentication
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$... # paste hash from Step 1

# App Configuration
APP_ENV=development
DEBUG=true
SESSION_TIMEOUT_HOURS=8

# Streamlit Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost
```

#### Step 3: Port-Forward to Staging Database

```bash
# Set kubeconfig
export KUBECONFIG=~/staging-kubeconfig.txt

# Port-forward PostgreSQL
kubectl port-forward -n aicallgo-staging svc/postgres-postgresql 5432:5432

# Keep this terminal open
```

#### Step 4: Install Dependencies

```bash
cd /services/admin-board

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

#### Step 5: Run Streamlit

```bash
streamlit run app.py

# Should see:
#   You can now view your Streamlit app in your browser.
#   Local URL: http://localhost:8501
#   Network URL: http://192.168.x.x:8501
```

#### Step 6: Testing Checklist

**Authentication Tests:**
- [ ] Login page appears at `http://localhost:8501`
- [ ] Invalid username shows error message
- [ ] Invalid password shows error message
- [ ] Valid credentials grant access to dashboard
- [ ] Session persists across page refreshes
- [ ] Logout button clears session
- [ ] Can re-login after logout
- [ ] Session timeout works (wait 8+ hours or modify SESSION_TIMEOUT_HOURS=0.01 to test)

**Database Tests:**
- [ ] "Check Database" button works
- [ ] Database statistics display correctly
- [ ] User count matches staging database
- [ ] Business count matches staging database
- [ ] No connection errors in logs

**Design Tests:**
- [ ] Purple/green color scheme matches frontend
- [ ] Sidebar styling looks clean
- [ ] Buttons have correct hover states
- [ ] Success/error messages display correctly
- [ ] Expanders work and look styled
- [ ] Typography is consistent

**System Info:**
- [ ] Environment displays correctly
- [ ] Database connection info shows (without credentials)
- [ ] Debug mode indicator works
- [ ] Session timeout displays correctly

#### Step 7: Troubleshooting

**Database Connection Fails:**
```bash
# Check port-forward is running
lsof -i :5432

# Test direct connection
psql "postgresql://aicallgo_user:password@localhost:5432/aicallgo_staging"
```

**Login Fails:**
```bash
# Verify password hash in .env
echo $ADMIN_PASSWORD_HASH

# Test password verification in Python
python3 -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'])
hash = '$2b$12$...'  # your hash
plain = 'YourPassword'
print('Valid:', pwd_context.verify(plain, hash))
"
```

**CSS Not Loading:**
```bash
# Check file exists
ls -la static/custom.css

# Restart Streamlit
# Press Ctrl+C and run again
streamlit run app.py
```

**Import Errors:**
```bash
# Verify web-backend path
ls -la ../web-backend/app/models/

# Check Python path
python3 -c "import sys; print('\n'.join(sys.path))"
```

---

## Evaluation Checkpoint

### When to Evaluate (Before Phase 3)

After completing Phase 2 (read-only pages), evaluate Streamlit against these criteria:

#### Keep Streamlit If:
- ✅ UI feels intuitive and fast
- ✅ Stakeholders are satisfied with design
- ✅ Forms and tables work well
- ✅ Performance is adequate
- ✅ CSS customization meets design needs

#### Consider Flask-Admin If:
- ❌ Design control feels too limited
- ❌ Forms feel clunky or limited
- ❌ Need more complex UI interactions
- ❌ Performance issues with large datasets
- ❌ Stakeholders request pixel-perfect frontend match

### Migration Cost Estimate
If migrating to Flask-Admin:
- **Time:** 2-3 days
- **Reusable:** Database models, service layer logic
- **Rewrite:** UI components, templates, routing
- **Risk:** Low (can run both apps in parallel)

---

## Success Criteria

Phase 1 is complete when:

✅ **Authentication:**
- Admin can log in with username/password
- Session persists and times out correctly
- Logout clears session completely

✅ **Database:**
- Health check succeeds
- Can query users, businesses, subscriptions
- Connection pooling works without errors

✅ **Design:**
- Purple/green theme applied throughout
- Buttons, cards, and tables styled correctly
- Matches general look of Next.js frontend

✅ **Project Structure:**
- All directories created
- Dependencies installed
- Configuration files in place
- Models imported from web-backend

---

## Timeline Summary

| Task | Time | Cumulative |
|------|------|------------|
| Directory structure | 30 mins | 30 mins |
| Requirements.txt | 20 mins | 50 mins |
| Streamlit config | 15 mins | 1h 5m |
| Settings.py | 45 mins | 1h 50m |
| Auth.py | 1 hour | 2h 50m |
| Connection.py | 1 hour | 3h 50m |
| Models.py | 30 mins | 4h 20m |
| Custom CSS | 1.5 hours | 5h 50m |
| App.py | 2 hours | 7h 50m |
| Testing | 1 hour | **8h 50m** |

**Total: ~9 hours (1-1.5 days of focused work)**

---

## Next Phase Preview

**Phase 2: Read-Only Pages (4-5 days)**
- Dashboard with KPIs and charts
- Users page with search and detail view
- Businesses page with filtering
- Call Logs with transcript viewer
- Billing data display

**Phase 3: Data Manipulation (5-6 days)**
- Entitlements management (grant/revoke features)
- Credit adjustments with audit trail
- Transaction safety and validation

---

## Technical Notes

### Why Async SQLAlchemy?
- Matches web-backend patterns for consistency
- Better performance for read-heavy admin operations
- Non-blocking database queries in Streamlit

### Why Import Models?
- Single source of truth prevents schema drift
- Automatic updates when web-backend changes
- Reuses all relationships and constraints
- Zero maintenance overhead

### Why Custom CSS?
- Streamlit's default theme doesn't match frontend
- CSS overrides provide good-enough design consistency
- Much faster than building custom components
- Can be refined iteratively

### Security Considerations
- Bcrypt for password hashing (industry standard)
- Session timeout prevents unauthorized access
- XSRF protection enabled in Streamlit config
- Database credentials in environment variables only
- No sensitive data logged in debug mode

---

## Documentation

This document should be referenced throughout Phase 1 implementation. Update status as tasks complete:

- [ ] Task 1: Directory structure
- [ ] Task 2: Requirements.txt
- [ ] Task 3: Streamlit config
- [ ] Task 4: Settings.py
- [ ] Task 5: Auth.py
- [ ] Task 6: Connection.py
- [ ] Task 7: Models.py
- [ ] Task 8: Custom CSS
- [ ] Task 9: App.py
- [ ] Task 10: Testing

**Implementation Start Date:** ___________
**Phase 1 Complete Date:** ___________
**Implemented By:** ___________

---

**Document End**
