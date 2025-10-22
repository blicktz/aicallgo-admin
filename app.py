"""
AICallGO Admin Board - Main Application
Entry point for Streamlit admin dashboard with persistent sidebar
"""
import streamlit as st
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
# Define Home Page Content
# ====================
def home_page():
    """Home page content (Phase 1 completion status)"""
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
        st.caption(f"PostgreSQL (sync)")

    with col3:
        st.markdown("### ✅ Design System")
        st.success("Applied")
        st.caption("Matching Next.js frontend")

    # Phase 1 completion checklist
    st.markdown("---")
    st.markdown("## Phase 1 Deliverables")

    checklist = [
        ("✅", "Working authentication system", "Login/logout with bcrypt password verification"),
        ("✅", "Database connection established", "Sync SQLAlchemy with connection pooling"),
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

# ====================
# Define Page Navigation
# ====================
pages = {
    "app": [
        st.Page(home_page, title="Home", icon="🏠"),
    ],
    "Dashboard": [
        st.Page("pages/1_📊_Dashboard.py", title="Dashboard", icon="📊"),
        st.Page("pages/2_👥_Users.py", title="Users", icon="👥"),
        st.Page("pages/3_🏢_Businesses.py", title="Businesses", icon="🏢"),
        st.Page("pages/4_🤖_Agents.py", title="Agents", icon="🤖"),
        st.Page("pages/5_📞_Call_Logs.py", title="Call Logs", icon="📞"),
    ],
    "Billing": [
        st.Page("pages/6_💳_Billing.py", title="Billing", icon="💳"),
        st.Page("pages/6_⚡_Entitlements.py", title="Entitlements", icon="⚡"),
        st.Page("pages/7_💰_Credits.py", title="Credits", icon="💰"),
        st.Page("pages/8_🎟️_Promotions.py", title="Promotions", icon="🎟️"),
    ],
    "System": [
        st.Page("pages/9_📅_Appointments.py", title="Appointments", icon="📅"),
        st.Page("pages/10_🔧_System.py", title="System", icon="🔧"),
    ],
}

# ====================
# Persistent Sidebar
# ====================
with st.sidebar:
    # Header
    st.header("📊 Admin Board")
    st.write(f"👤 **{st.session_state.username}**")
    st.caption(f"Environment: {settings.APP_ENV}")
    st.divider()

    # Navigation info
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
            is_healthy, message = check_db_health()
            if is_healthy:
                st.success(message)

                # Show database stats
                with st.expander("Database Statistics"):
                    db_info = get_db_info()
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
# Run Navigation
# ====================
pg = st.navigation(pages)
pg.run()
