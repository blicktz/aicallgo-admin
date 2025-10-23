"""
Entitlements - Feature access management with override creation
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from config.auth import require_auth
from database.connection import get_session
from services.user_service import get_users, get_user_by_id
from services.entitlement_service import (
    get_all_features,
    get_user_entitlements,
    create_feature_override,
    delete_feature_override
)
from utils.formatters import format_datetime, format_status_badge
import logging
import os

logger = logging.getLogger(__name__)

# Auth check
if not require_auth():
    st.stop()

st.title("⚡ Entitlements")
st.markdown("Manage feature access overrides")

# Refresh button
col1, col2 = st.columns([8, 2])
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Initialize session state
if "selected_user_id" not in st.session_state:
    st.session_state.selected_user_id = None
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = None

# Main layout: user search (30%) + entitlement management (70%)
search_col, manage_col = st.columns([3, 7])

# Section 1: User Search (Left Column)
with search_col:
    st.markdown("### User Search")

    search_query = st.text_input(
        "🔍 Search by email or name",
        placeholder="Enter email or name...",
        key="user_search"
    )

    # Load users
    @st.cache_data(ttl=60)
    def load_users(search, status, per_page):
        """Load users with filters"""
        with get_session() as session:
            return get_users(
                session,
                limit=per_page,
                offset=0,
                search_query=search if search else None,
                status_filter=status
            )

    try:
        users = load_users(search_query, "active", 50)

        if not users:
            st.info("No users found")
        else:
            # Convert to DataFrame
            users_df = pd.DataFrame([
                {
                    "Email": u.email,
                    "Name": u.full_name or "N/A",
                    "ID": str(u.id)
                }
                for u in users
            ])

            st.markdown("*Click on a row to select user*")

            # Display DataFrame with row selection
            event = st.dataframe(
                users_df.drop(columns=["ID"]),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                height=600
            )

            # Update selected user ID
            if event and "selection" in event and "rows" in event["selection"]:
                if len(event["selection"]["rows"]) > 0:
                    selected_idx = event["selection"]["rows"][0]
                    selected_user_id = users_df.iloc[selected_idx]["ID"]
                    st.session_state.selected_user_id = selected_user_id

            st.caption(f"Showing {len(users)} users")

    except Exception as e:
        st.error(f"Failed to load users: {str(e)}")
        logger.exception("Failed to load users")

# Section 2: Entitlement Management (Right Column)
with manage_col:
    st.markdown("### Entitlement Management")

    if not st.session_state.selected_user_id:
        st.info("👈 Select a user to manage entitlements")
    else:
        # Load user details and entitlements
        @st.cache_data(ttl=30)
        def load_entitlements(user_id):
            """Load user entitlements"""
            with get_session() as session:
                user = get_user_by_id(session, user_id)
                if not user:
                    return None

                entitlements = get_user_entitlements(session, user_id)
                return {
                    "user": user,
                    **entitlements
                }

        try:
            data = load_entitlements(st.session_state.selected_user_id)

            if not data or not data["user"]:
                st.warning("User not found")
            else:
                user = data["user"]
                plan = data["plan"]
                plan_features = data["plan_features"]
                overrides = data["overrides"]
                computed_access = data["computed_access"]

                # User header
                st.markdown(f"**User:** {user.email}")
                st.markdown(f"**Name:** {user.full_name or 'N/A'}")
                st.divider()

                # Panel A: Current State Display
                st.markdown("#### Current Plan & Features")

                if plan:
                    st.markdown(f"**Plan:** {plan.name}")
                    st.markdown(f"**Plan Key:** {plan.plan_key}")

                    if plan_features:
                        st.markdown("**Plan Features:**")
                        for feature in plan_features:
                            st.markdown(f"- ✅ {feature.feature_key}: {feature.description or 'No description'}")
                    else:
                        st.info("No default features in this plan")
                else:
                    st.info("User has no active subscription")

                st.divider()

                # Active Overrides
                st.markdown("#### Active Overrides")

                now = datetime.utcnow()
                active_overrides = [o for o in overrides if o.expires_at is None or o.expires_at > now]

                if active_overrides:
                    for override in active_overrides:
                        feature_key = override.feature.feature_key if override.feature else "Unknown"
                        access_badge = "🟢 Grant" if override.has_access else "🔴 Deny"

                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"**{feature_key}** - {access_badge}")
                            if override.expires_at:
                                st.caption(f"Expires: {format_datetime(override.expires_at)}")
                            if override.notes:
                                with st.expander("View notes"):
                                    st.text(override.notes)
                        with col2:
                            if st.button("Delete", key=f"delete_{override.id}"):
                                st.session_state.confirm_delete = str(override.id)
                                st.rerun()

                        # Delete confirmation
                        if st.session_state.confirm_delete == str(override.id):
                            st.warning("⚠️ Confirm deletion?")
                            delete_reason = st.text_input(
                                "Reason for deletion (min 10 chars)",
                                key=f"reason_{override.id}"
                            )

                            col_cancel, col_confirm = st.columns(2)
                            with col_cancel:
                                if st.button("Cancel", key=f"cancel_{override.id}"):
                                    st.session_state.confirm_delete = None
                                    st.rerun()
                            with col_confirm:
                                if st.button("✅ Confirm", key=f"confirm_{override.id}", type="primary"):
                                    if len(delete_reason) < 10:
                                        st.error("Reason must be at least 10 characters")
                                    else:
                                        try:
                                            with get_session() as session:
                                                success = delete_feature_override(
                                                    session=session,
                                                    user_id=user.id,
                                                    feature_key=feature_key,
                                                    admin_username=os.getenv("ADMIN_USERNAME", "admin"),
                                                    reason=delete_reason
                                                )
                                            if success:
                                                st.success(f"✅ Override deleted: {feature_key}")
                                                st.session_state.confirm_delete = None
                                                st.cache_data.clear()
                                                st.rerun()
                                            else:
                                                st.error("Failed to delete override")
                                        except Exception as e:
                                            st.error(f"❌ Failed to delete override: {str(e)}")
                                            logger.exception("Failed to delete override")

                        st.divider()
                else:
                    st.info("No active overrides")

                st.divider()

                # Computed Access
                st.markdown("#### Computed Access")

                if computed_access:
                    computed_df = pd.DataFrame([
                        {
                            "Feature": key,
                            "Access": "✅ Yes" if value else "❌ No"
                        }
                        for key, value in computed_access.items()
                    ])
                    st.dataframe(computed_df, hide_index=True, use_container_width=True)
                else:
                    st.info("No feature access")

                st.divider()

                # Panel B: Create/Update Override Form
                st.markdown("#### Grant/Revoke Feature Access")

                # Load all features
                @st.cache_data(ttl=300)
                def load_all_features():
                    """Load all features"""
                    with get_session() as session:
                        return get_all_features(session)

                all_features = load_all_features()

                with st.form("override_form"):
                    # Feature selection
                    if not all_features:
                        st.warning("No features available in the system")
                        st.stop()

                    feature_options = {f"{f.feature_key} - {f.description or 'No description'}": f.feature_key for f in all_features}
                    selected_feature_label = st.selectbox(
                        "Feature",
                        options=list(feature_options.keys())
                    )
                    selected_feature_key = feature_options[selected_feature_label]

                    # Access toggle
                    has_access = st.radio(
                        "Access",
                        options=["Grant", "Deny"],
                        horizontal=True
                    )

                    # Optional expiration
                    set_expiration = st.checkbox("Set expiration date")
                    expires_at = None
                    if set_expiration:
                        expires_date = st.date_input(
                            "Expires At",
                            min_value=datetime.now().date() + timedelta(days=1)
                        )
                        expires_at = datetime.combine(expires_date, datetime.min.time())

                    # Required notes
                    notes = st.text_area(
                        "Notes (required, min 10 characters)",
                        placeholder="Explain why this override is needed...",
                        max_chars=500
                    )

                    # Preview
                    if notes and len(notes) >= 10:
                        with st.expander("📋 Preview Changes"):
                            st.markdown(f"**User**: {user.email}")
                            st.markdown(f"**Feature**: {selected_feature_key}")
                            st.markdown(f"**Action**: {has_access}")
                            st.markdown(f"**New Access**: {'✅ Yes' if has_access == 'Grant' else '❌ No'}")
                            if expires_at:
                                st.markdown(f"**Expires**: {format_datetime(expires_at)}")
                            st.markdown(f"**Notes**: {notes}")

                    # Confirmation checkbox
                    confirm_change = st.checkbox("⚠️ I confirm this override change")

                    submitted = st.form_submit_button("Save Override", type="primary")

                    if submitted:
                        # Validation
                        if len(notes) < 10:
                            st.error("Notes must be at least 10 characters")
                            st.stop()

                        if not confirm_change:
                            st.error("Please confirm the override change by checking the box above")
                            st.stop()

                        # Execute
                        try:
                            with get_session() as session:
                                override = create_feature_override(
                                    session=session,
                                    user_id=user.id,
                                    feature_key=selected_feature_key,
                                    has_access=(has_access == "Grant"),
                                    expires_at=expires_at,
                                    notes=notes,
                                    admin_username=os.getenv("ADMIN_USERNAME", "admin")
                                )

                            st.success(f"✅ Override created: {selected_feature_key}")
                            st.cache_data.clear()
                            st.rerun()

                        except ValueError as e:
                            st.error(f"❌ Validation error: {str(e)}")
                        except Exception as e:
                            st.error(f"❌ Failed to create override: {str(e)}")
                            logger.exception("Failed to create override")

        except Exception as e:
            st.error(f"Failed to load entitlements: {str(e)}")
            logger.exception("Failed to load entitlements")
