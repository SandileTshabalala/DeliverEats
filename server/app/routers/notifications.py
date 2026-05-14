from fastapi import APIRouter, Depends
from app.services.notification_service import send_notification
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.post("/send")
def notify_user(title: str, message: str, user=Depends(get_current_user)):
    send_notification(user.id, title, message)
    return {"message": "Notification sent"}
