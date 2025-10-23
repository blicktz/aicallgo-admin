"""
Entitlement service for feature access management.

Provides data access layer for feature entitlement operations,
wrapping web-backend's CRUD operations with admin-specific logic.
"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select
import logging
import redis

# Add web-backend to path for CRUD imports
backend_path = Path(__file__).parent.parent.parent / "web-backend"
sys.path.insert(0, str(backend_path))

from app.crud.crud_feature_sync import feature_sync
from app.crud.crud_user_feature_override_sync import user_feature_override_sync
from app.crud.crud_plan_sync import plan_sync
from app.crud.crud_plan_feature_sync import plan_feature_sync
from app.models import Feature, UserFeatureOverride, User, Subscription, Plan, PlanFeature

from services.audit_service import format_audit_trail, log_entitlement_action
from config.settings import settings

logger = logging.getLogger(__name__)


def _invalidate_entitlement_cache(user_id: UUID) -> None:
    """
    Invalidate entitlement cache for a user in Redis.

    This ensures that when admin-board modifies entitlements,
    the web-backend immediately reflects the changes.

    Args:
        user_id: User ID to invalidate cache for
    """
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        cache_key = f"{settings.ENTITLEMENT_CACHE_KEY_PREFIX}:{str(user_id)}"
        redis_client.delete(cache_key)
        redis_client.close()

        logger.info(
            "Invalidated entitlement cache",
            user_id=str(user_id),
            cache_key=cache_key,
        )
    except Exception as e:
        # Don't fail the operation if cache invalidation fails
        logger.error(
            "Failed to invalidate entitlement cache",
            user_id=str(user_id),
            error=str(e),
        )


def get_all_features(session: Session) -> List[Feature]:
    """
    Get all available features from the system.
    Uses: crud_feature_sync.get_multi()
    """
    try:
        features = feature_sync.get_multi(session, skip=0, limit=1000)
        return features
    except Exception as e:
        logger.error(f"Error fetching features: {e}")
        raise


def get_user_entitlements(session: Session, user_id: str) -> Dict[str, Any]:
    """
    Get comprehensive entitlement data for a user.

    Returns:
        {
            "plan": Plan object,
            "plan_features": [Feature objects from plan],
            "overrides": [UserFeatureOverride objects],
            "computed_access": {
                "feature_key": bool (final access)
            }
        }

    Logic:
    1. Get user's active subscription and plan
    2. Get plan's default features via plan_features junction
    3. Get user's active overrides
    4. Compute final access (override > plan default)
    """
    try:
        # Get user's active subscription
        subscription_query = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status.in_(["active", "trialing"])
        ).order_by(Subscription.created_at.desc())

        subscription = session.execute(subscription_query).scalar_one_or_none()

        plan = None
        plan_features = []

        if subscription and subscription.stripe_plan_id:
            # Get plan by stripe_price_id
            plan = plan_sync.get_by_stripe_price_id(
                session, stripe_price_id=subscription.stripe_plan_id
            )

            if plan:
                # Get feature IDs for this plan
                feature_ids = plan_feature_sync.get_features_for_plan(
                    session, plan_id=plan.id
                )

                # Get Feature objects for each feature_id
                plan_features = []
                for feature_id in feature_ids:
                    feature = feature_sync.get(session, id=feature_id)
                    if feature:
                        plan_features.append(feature)

        # Get user's overrides (all overrides, not just active ones, for display)
        overrides = user_feature_override_sync.get_multi_by_user(
            session, user_id=user_id, limit=1000
        )

        # Compute final access for each feature
        computed_access = {}

        # Start with plan features (if any)
        for feature in plan_features:
            computed_access[feature.feature_key] = True

        # Apply overrides (overrides take precedence)
        now = datetime.utcnow()
        for override in overrides:
            # Only apply active overrides to computed access
            if override.expires_at is None or override.expires_at > now:
                if override.feature and override.feature.feature_key:
                    computed_access[override.feature.feature_key] = override.has_access

        return {
            "plan": plan,
            "plan_features": plan_features,
            "overrides": overrides,
            "computed_access": computed_access
        }

    except Exception as e:
        logger.error(f"Error fetching user entitlements for {user_id}: {e}")
        raise


def create_feature_override(
    session: Session,
    user_id: str,
    feature_key: str,
    has_access: bool,
    expires_at: Optional[datetime],
    notes: str,
    admin_username: str
) -> UserFeatureOverride:
    """
    Create or update a feature override for a user.

    Steps:
    1. Validate user exists and is active
    2. Get feature by feature_key
    3. Check if override exists (get_by_user_and_feature)
    4. If exists: update; if not: create
    5. Log audit trail
    6. Return created/updated override

    Uses:
    - crud_feature_sync.get_by_feature_key()
    - crud_user_feature_override_sync.get_by_user_and_feature()
    - crud_user_feature_override_sync.create() or update()
    """
    try:
        # Validate user exists and is active
        user_query = select(User).where(User.id == user_id)
        user = session.execute(user_query).scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        if not user.is_active:
            raise ValueError(f"Cannot modify inactive user {user.email}")

        # Validate feature exists
        feature = feature_sync.get_by_feature_key(session, feature_key=feature_key)
        if not feature:
            raise ValueError(f"Feature '{feature_key}' not found")

        # Validate notes
        if not notes or len(notes.strip()) < 10:
            raise ValueError("Notes must be at least 10 characters")

        # Validate expiration date
        if expires_at and expires_at <= datetime.utcnow():
            raise ValueError("Expiration date must be in the future")

        # Format notes with audit trail
        structured_notes = format_audit_trail(notes, admin_username)

        # Check if override exists
        existing_override = user_feature_override_sync.get_by_user_and_feature(
            session, user_id=user.id, feature_id=feature.id
        )

        if existing_override:
            # Update existing override
            override = user_feature_override_sync.update(
                session,
                db_obj=existing_override,
                obj_in={
                    "has_access": has_access,
                    "expires_at": expires_at,
                    "notes": structured_notes
                }
            )
        else:
            # Create new override
            override = user_feature_override_sync.create(
                session,
                obj_in={
                    "user_id": user.id,
                    "feature_id": feature.id,
                    "has_access": has_access,
                    "expires_at": expires_at,
                    "notes": structured_notes
                }
            )

        # Log action
        log_entitlement_action(
            session=session,
            action_type="grant" if has_access else "revoke",
            admin_username=admin_username,
            user_id=str(user_id),
            feature_key=feature_key,
            has_access=has_access,
            notes=notes
        )

        # Invalidate user's cache so changes are immediately visible
        _invalidate_entitlement_cache(user_id=user_id)

        return override

    except Exception as e:
        logger.error(f"Error creating feature override: {e}")
        raise


def delete_feature_override(
    session: Session,
    user_id: str,
    feature_key: str,
    admin_username: str,
    reason: str
) -> bool:
    """
    Remove a feature override (revert to plan default).

    Steps:
    1. Get feature by feature_key
    2. Delete override
    3. Log audit trail
    4. Return success/failure

    Uses:
    - crud_user_feature_override_sync.delete_by_user_and_feature()
    """
    try:
        # Validate reason
        if not reason or len(reason.strip()) < 10:
            raise ValueError("Reason must be at least 10 characters")

        # Get feature
        feature = feature_sync.get_by_feature_key(session, feature_key=feature_key)
        if not feature:
            raise ValueError(f"Feature '{feature_key}' not found")

        # Get existing override for audit
        override = user_feature_override_sync.get_by_user_and_feature(
            session, user_id=user_id, feature_id=feature.id
        )

        # Delete override
        success = user_feature_override_sync.delete_by_user_and_feature(
            session, user_id=user_id, feature_id=feature.id
        )

        if success:
            # Log deletion
            log_entitlement_action(
                session=session,
                action_type="delete",
                admin_username=admin_username,
                user_id=str(user_id),
                feature_key=feature_key,
                has_access=override.has_access if override else None,
                notes=reason
            )

            # Invalidate user's cache so changes are immediately visible
            _invalidate_entitlement_cache(user_id=user_id)

        return success

    except Exception as e:
        logger.error(f"Error deleting feature override: {e}")
        raise


def get_override_history(session: Session, user_id: str) -> List[Dict]:
    """
    Get audit history of entitlement changes for a user.

    For Phase 3: Return overrides with created_at/updated_at
    For Phase 4+: Query dedicated audit log table
    """
    try:
        overrides = user_feature_override_sync.get_multi_by_user(
            session, user_id=user_id, limit=1000
        )

        history = []
        for override in overrides:
            history.append({
                "id": str(override.id),
                "feature_key": override.feature.feature_key if override.feature else "Unknown",
                "feature_description": override.feature.description if override.feature else "",
                "has_access": override.has_access,
                "expires_at": override.expires_at,
                "notes": override.notes,
                "created_at": override.created_at,
                "updated_at": override.updated_at
            })

        # Sort by created_at descending
        history.sort(key=lambda x: x["created_at"], reverse=True)

        return history

    except Exception as e:
        logger.error(f"Error fetching override history for {user_id}: {e}")
        raise
