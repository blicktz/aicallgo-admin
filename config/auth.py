"""
Authentication module for admin board.
Uses Streamlit session state, browser cookies, and bcrypt password verification.
Matches security pattern from web-backend/app/core/security.py
"""
import streamlit as st
from passlib.context import CryptContext
from datetime import datetime, timedelta
import uuid
import json
import logging
import base64
from config.settings import settings
import extra_streamlit_components as stx
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configure logging
logger = logging.getLogger(__name__)

# Password hashing context (matches web-backend)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Cookie manager instance (persistent across refreshes)
_cookie_manager = None

# Fernet cipher for encrypting session data
_cipher = None


def get_cipher():
    """
    Get or create the Fernet cipher for encrypting/decrypting session data.

    Returns:
        Fernet: Cipher instance for encryption/decryption
    """
    global _cipher
    if _cipher is None:
        # Derive a key from the SESSION_SECRET_KEY
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'aicallgo_admin_salt',  # Fixed salt for consistency
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(settings.SESSION_SECRET_KEY.encode()))
        _cipher = Fernet(key)
    return _cipher


def encrypt_session_data(data: dict) -> str:
    """
    Encrypt session data for storage in cookies.

    Args:
        data: Session data dictionary

    Returns:
        str: Encrypted and base64-encoded session data
    """
    cipher = get_cipher()
    json_str = json.dumps(data)
    encrypted = cipher.encrypt(json_str.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_session_data(encrypted_data: str) -> dict | None:
    """
    Decrypt session data from cookies.

    Args:
        encrypted_data: Encrypted and base64-encoded session data

    Returns:
        dict: Decrypted session data, or None if decryption fails
    """
    try:
        cipher = get_cipher()
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = cipher.decrypt(encrypted_bytes)
        return json.loads(decrypted.decode())
    except Exception as e:
        logger.error(f"🔒 Failed to decrypt session data: {e}")
        return None


def get_cookie_manager():
    """
    Get or initialize the cookie manager.

    Returns:
        CookieManager: The cookie manager instance
    """
    global _cookie_manager
    if _cookie_manager is None:
        logger.info("🍪 Initializing cookie manager (extra-streamlit-components)")
        _cookie_manager = stx.CookieManager()

    return _cookie_manager


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


def generate_session_token(username: str) -> dict:
    """
    Generate a session token with timestamp.

    Returns:
        dict: Session data with token, username, and login time
    """
    return {
        'token': str(uuid.uuid4()),
        'username': username,
        'login_time': datetime.now().isoformat()
    }


def validate_session_token(session_data: dict) -> bool:
    """
    Validate a session token and check if it's expired.

    Args:
        session_data: Session data dict with token, username, login_time

    Returns:
        bool: True if session is valid and not expired, False otherwise
    """
    if not session_data or not isinstance(session_data, dict):
        return False

    required_keys = {'token', 'username', 'login_time'}
    if not all(key in session_data for key in required_keys):
        return False

    try:
        login_time = datetime.fromisoformat(session_data['login_time'])
        timeout = timedelta(hours=settings.SESSION_TIMEOUT_HOURS)

        # Check if session has expired
        if datetime.now() - login_time > timeout:
            return False

        return True
    except (ValueError, TypeError):
        return False


def save_session_to_cookie(session_data: dict):
    """
    Save session data to browser cookie.

    Encrypts the session data before storing.
    """
    logger.info(f"💾 Attempting to save session to cookie for user: {session_data.get('username')}")

    try:
        cookies = get_cookie_manager()
        encrypted_data = encrypt_session_data(session_data)

        # Set cookie with 8 hour expiry (matches session timeout)
        cookies.set('session', encrypted_data, max_age=settings.SESSION_TIMEOUT_HOURS * 3600)

        logger.info(f"💾 SUCCESS: Session saved to cookie for user: {session_data.get('username')}")
    except Exception as e:
        logger.error(f"💾 ERROR: Failed to save session to cookie: {e}")


def load_session_from_cookie() -> dict | None:
    """
    Load session data from browser cookie.

    Returns:
        dict: Session data if found and valid, None otherwise
    """
    logger.info("📖 Attempting to load session from cookie")

    try:
        cookies = get_cookie_manager()
        encrypted_data = cookies.get('session')

        if not encrypted_data:
            logger.info("📖 No session cookie found")
            return None

        session_data = decrypt_session_data(encrypted_data)

        if session_data and validate_session_token(session_data):
            logger.info(f"📖 SUCCESS: Loaded valid session for user: {session_data.get('username')}")
            return session_data
        else:
            logger.warning("📖 Session cookie found but token validation failed (expired or invalid)")
            return None

    except Exception as e:
        logger.error(f"📖 ERROR: Failed to load session from cookie: {e}")
        return None


def clear_session_cookie():
    """
    Clear session cookie from browser.
    """
    try:
        cookies = get_cookie_manager()
        cookies.delete('session')
        logger.info("🗑️  Session cookie cleared")
    except Exception as e:
        logger.error(f"🗑️  ERROR: Failed to clear session cookie: {e}")


def init_session_state():
    """
    Initialize session state variables if not present.
    Attempts to restore session from browser cookie if available.
    """
    logger.info("🔄 Initializing session state")

    # Initialize state variables if not present
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None

    logger.info(f"🔄 Current session state: authenticated={st.session_state.authenticated}, username={st.session_state.username}")

    # Try to restore session from cookie if not already authenticated
    if not st.session_state.authenticated:
        logger.info("🔄 Not authenticated, attempting to restore from cookie")
        session_data = load_session_from_cookie()
        if session_data:
            # Restore session from cookie
            st.session_state.authenticated = True
            st.session_state.username = session_data['username']
            st.session_state.login_time = datetime.fromisoformat(session_data['login_time'])
            logger.info(f"🔄 SUCCESS: Session restored from cookie for user: {session_data['username']}")
        else:
            logger.info("🔄 No valid session found in cookie")
    else:
        logger.info(f"🔄 Already authenticated as: {st.session_state.username}")


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
    Saves session to browser cookie on success.

    Returns:
        bool: True if authentication successful, False otherwise
    """
    logger.info(f"🔐 Login attempt for username: {username}")

    if username == settings.ADMIN_USERNAME:
        if verify_password(password, settings.ADMIN_PASSWORD_HASH):
            # Update session state
            login_time = datetime.now()
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.login_time = login_time

            logger.info(f"🔐 SUCCESS: Login successful for user: {username}")

            # Save session to cookie for persistence
            session_data = generate_session_token(username)
            save_session_to_cookie(session_data)

            return True
        else:
            logger.warning(f"🔐 FAILED: Invalid password for user: {username}")
    else:
        logger.warning(f"🔐 FAILED: Unknown username: {username}")

    return False


def logout():
    """Clear session state and browser cookie, then log out user."""
    logger.info(f"🚪 Logout requested for user: {st.session_state.get('username', 'unknown')}")

    # Clear session state
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.login_time = None

    # Clear browser cookie
    clear_session_cookie()

    logger.info("🚪 Logout complete")


def require_auth() -> bool:
    """
    Check if user is authenticated and session is valid.
    If not authenticated, displays login form and stops execution.

    Automatically restores session from browser cookie if available.

    Use this as a gate on protected pages.

    Returns:
        bool: True if authenticated and session valid, False otherwise
    """
    init_session_state()

    # Check if authenticated (may have been restored from cookie)
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
        submit = st.form_submit_button("Login", width='stretch')

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
