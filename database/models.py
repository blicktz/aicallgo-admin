"""
Database models imported from web-backend.
This ensures schema consistency - admin board uses exact same models.
"""
import sys
from pathlib import Path

# Add web-backend to Python path
backend_path = Path(__file__).parent.parent / "web-backend"
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
    "CustomQuestion",
    # Billing
    "Subscription",
    "SubscriptionAudit",
    "Invoice",
    "Product",
    "Price",
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
    "AppointmentEndUser",
    "AppointmentSchedulingConfig",
    "NylasConnection",
    # Events
    "EventNotification",
    "EventType",
    "NonCustomerEvent",
    "NonCustomerEventType",
    "CustomerEvent",
    "CustomerEventConfig",
    # Webhooks
    "WebhookEvent",
    # Analytics
    "IntegrationInterest",
    "CustomIntegrationRequest",
    "SignupEvent",
    "ConversionMetric",
    "ABTestResult",
    "DeviceFingerprint",
    "UserDeviceFingerprint",
    "MetaPixelEvent",
    "UserMetaTracking",
    # Human Agents
    "HumanAgent",
    # FAQ
    "FAQ",
]
