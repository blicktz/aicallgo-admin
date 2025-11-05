"""
AICallGO Admin Board - Main Application
Entry point for Streamlit admin dashboard with persistent sidebar
"""
import streamlit as st
from config.settings import settings
from config.auth import require_auth, login_form, logout
from database.connection import check_db_health, get_db_info, get_session
from services.system_service import generate_system_report

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
    """Home page - System status and operations overview"""
    st.title("📊 AICallGO Admin Dashboard")
    st.markdown("### Welcome to the Admin Board")

    # Welcome message
    st.info("👋 **Quick system overview and health status**")

    # Load system report
    @st.cache_data(ttl=60)
    def load_system_data():
        """Load system report with caching"""
        with get_session() as session:
            return generate_system_report(session)

    with st.spinner("Loading system status..."):
        try:
            report = load_system_data()
        except Exception as e:
            st.error(f"Failed to load system data: {str(e)}")
            st.stop()

    # System status card
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### ✅ Authentication")
        st.success("Working")
        st.caption("Session-based auth with bcrypt")

    with col2:
        db_health = report.get("database_health", {})
        if db_health.get("status") == "connected":
            st.markdown("### ✅ Database")
            st.success(f"Connected ({db_health.get('response_time_ms', 0)}ms)")
            st.caption(f"PostgreSQL")
        else:
            st.markdown("### ❌ Database")
            st.error("Connection failed")
            st.caption(db_health.get("error", "Unknown error"))

    with col3:
        st.markdown("### ✅ Design System")
        st.success("Applied")
        st.caption("Matching Next.js frontend")

    # System Health Dashboard
    st.markdown("---")
    st.markdown("## 🏥 System Health Dashboard")

    growth = report.get("growth_stats", {})

    health_col1, health_col2, health_col3, health_col4 = st.columns(4)

    with health_col1:
        st.metric(
            "New Users Today",
            growth.get("new_users_today", 0),
            help="Users created today"
        )

    with health_col2:
        st.metric(
            "New Calls Today",
            growth.get("new_calls_today", 0),
            help="Calls logged today"
        )

    with health_col3:
        st.metric(
            "New Businesses Today",
            growth.get("new_businesses_today", 0),
            help="Businesses created today"
        )

    with health_col4:
        st.metric(
            "7-Day Growth",
            f"{growth.get('new_users_7d', 0)} users",
            help="New users in last 7 days"
        )

    # Data Quality & Engagement Metrics
    st.markdown("---")
    st.markdown("## 📈 User Engagement & Data Quality")

    quality = report.get("data_quality", {})
    counts = report.get("table_counts", {})

    engage_col1, engage_col2 = st.columns(2)

    with engage_col1:
        st.markdown("#### Engagement Rates")

        # Users with businesses
        pct_businesses = quality.get("users_with_businesses_pct", 0)
        st.metric(
            "Users with Businesses",
            f"{pct_businesses}%",
            f"{quality.get('users_with_businesses_count', 0)} of {counts.get('users_total', 0)}"
        )
        st.progress(pct_businesses / 100)

        # Users with agents
        pct_agents = quality.get("users_with_agents_pct", 0)
        st.metric(
            "Users with AI Agents",
            f"{pct_agents}%",
            f"{quality.get('users_with_agents_count', 0)} of {counts.get('users_total', 0)}"
        )
        st.progress(pct_agents / 100)

        # Users with subscriptions
        pct_subs = quality.get("users_with_subscriptions_pct", 0)
        st.metric(
            "Users with Active Subscriptions",
            f"{pct_subs}%",
            f"{quality.get('users_with_subscriptions_count', 0)} of {counts.get('users_total', 0)}"
        )
        st.progress(pct_subs / 100)

    with engage_col2:
        st.markdown("#### Quick Stats")

        stat_col_a, stat_col_b = st.columns(2)

        with stat_col_a:
            st.metric("Total Users", counts.get("users_total", 0))
            st.metric("Total Businesses", counts.get("businesses", 0))
            st.metric("AI Agents", counts.get("ai_agents", 0))

        with stat_col_b:
            st.metric("Active Subscriptions", counts.get("subscriptions_active", 0))
            st.metric("Trial Subscriptions", counts.get("subscriptions_trial", 0))
            st.metric("Total Call Logs", counts.get("call_logs_total", 0))

    # Quick Access Navigation
    st.markdown("---")
    st.markdown("## 🚀 Quick Access")

    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)

    with nav_col1:
        if st.button("👥 View All Users", use_container_width=True):
            st.switch_page("pages/2_👥_Users.py")

    with nav_col2:
        if st.button("📞 Recent Call Logs", use_container_width=True):
            st.switch_page("pages/5_📞_Call_Logs.py")

    with nav_col3:
        if st.button("💳 Monitor Billing", use_container_width=True):
            st.switch_page("pages/6_💳_Billing.py")

    with nav_col4:
        if st.button("🔧 System Diagnostics", use_container_width=True):
            st.switch_page("pages/10_🔧_System.py")

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
            db_url = str(settings.DATABASE_URL_SYNC)
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
        st.Page("pages/9_📅_Appointments.py", title="Appointments", icon="📅"),
    ],
    "Telephony": [
        st.Page("pages/12_📞_Twilio.py", title="Twilio Pool", icon="📞"),
    ],
    "Billing": [
        st.Page("pages/6_💳_Billing.py", title="Billing", icon="💳"),
        st.Page("pages/6_⚡_Entitlements.py", title="Entitlements", icon="⚡"),
        st.Page("pages/7_💰_Credits.py", title="Credits", icon="💰"),
        st.Page("pages/8_🎟️_Promotions.py", title="Promotions", icon="🎟️"),
    ],
    "System": [
        st.Page("pages/10_🔧_System.py", title="System", icon="🔧"),
        st.Page("pages/11_📋_Logs.py", title="Logs", icon="📋"),
        st.Page("pages/13_📊_Performance.py", title="Performance", icon="📊"),
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
