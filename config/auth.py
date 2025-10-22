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
    If not authenticated, displays login form and stops execution.

    Use this as a gate on protected pages.

    Returns:
        bool: True if authenticated and session valid, False otherwise
    """
    init_session_state()

    # Check if authenticated
    if not st.session_state.authenticated:
        login_form()
        st.stop()
        return False

    # Check session timeout
    if not check_session_timeout():
        st.warning("⚠️ Your session has expired. Please login again.")
        login_form()
        st.stop()
        return False

    return True


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
