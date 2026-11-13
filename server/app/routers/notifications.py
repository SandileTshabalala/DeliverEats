from fastapi import APIRouter, Depends

from app.core.dependencies import require_role
from app.core.roles import Role
from app.services import messaging
from app.services.notification_service import send_notification

router = APIRouter(tags=["Notifications"])


@router.get("/status")
def provider_status(admin=Depends(require_role(Role.SUPER_ADMIN))):
    """Which message providers are configured (admin only)."""
    return {"sms": messaging.sms_configured(), "email": messaging.email_configured()}


@router.post("/test")
def send_test(admin=Depends(require_role(Role.SUPER_ADMIN))):
    """
    Send a test SMS and email to the signed-in admin, to check the provider keys.
    (The old /send endpoint let ANY signed-in user send any text, at our cost.)
    """
    send_notification(admin.id, "Test message", "Your SMS and email settings are working.", sms=True, email=True)
    return {"sms": messaging.sms_configured(), "email": messaging.email_configured()}
