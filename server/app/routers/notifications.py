from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, require_role
from app.core.roles import Role
from app.services import inbox, messaging
from app.services.notification_service import send_notification

router = APIRouter(tags=["Notifications"])


@router.get("")
def my_notifications(user=Depends(get_current_user)):
    """The signed-in person's latest notifications and how many are unread."""
    return inbox.read(user.id)


@router.post("/read")
def mark_notifications_read(user=Depends(get_current_user)):
    inbox.mark_read(user.id)
    return {"unread": 0}


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
