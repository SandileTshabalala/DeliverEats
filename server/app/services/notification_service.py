"""
Tell a user something happened: by SMS (Africa's Talking) and/or email (Resend).

Messages are sent from a small background thread pool, so the request that
triggered them (accepting an order, a payment arriving) returns immediately and
is never slowed down or broken by a slow or failing provider. This runs inside
the API process on purpose: it does not depend on a Celery worker being up.

SMS costs money per message, so each call says which channels it wants. As a
rule: time-critical things go by SMS, records and receipts go by email.
"""
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable, Optional

from app.core.locger import logger
from app.core.config import settings
from app.services import inbox, messaging

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="notify")


def _submit(function, *args) -> None:
    """Indirection so tests can run deliveries inline."""
    _pool.submit(function, *args)


def deliver(user_id: str, title: str, message: str, sms: bool, email: bool,
            button_label: Optional[str] = None, button_url: Optional[str] = None) -> None:
    """Runs in a worker thread with its own database session."""
    from app.db.session import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return
        phone, address = user.contact_number, user.email
    except Exception as exc:
        logger.error(f"Notification for user {user_id} could not load the user: {exc}")
        return
    finally:
        db.close()

    if sms:
        messaging.send_sms(phone, f"{title}: {message}" if title else message)
    if email:
        messaging.send_email(address, title, message, button_label, button_url)


def send_notification(user_id: Optional[str], title: str, message: str, *,
                      sms: bool = True, email: bool = False,
                      button_label: Optional[str] = None, button_url: Optional[str] = None) -> None:
    """Queue a message to one user. Never raises."""
    if not user_id:
        return
    # Always goes to the bell in the app, whether or not SMS / email are set up
    link = None
    if button_url and settings.FRONTEND_URL and button_url.startswith(settings.FRONTEND_URL.rstrip("/")):
        link = button_url[len(settings.FRONTEND_URL.rstrip("/")):] or "/"
    if "reset-password" not in (link or ""):  # never keep a password reset link in the inbox
        inbox.add(user_id, title, message, link)
    sms = sms and messaging.sms_configured()
    email = email and messaging.email_configured()
    if not (sms or email):
        logger.info(f"[NOTIFY not sent: no provider configured] {user_id}: {title} - {message}")
        return
    try:
        _submit(deliver, user_id, title, message, sms, email, button_label, button_url)
    except Exception as exc:  # e.g. pool shut down during interpreter exit
        logger.error(f"Could not queue notification for {user_id}: {exc}")


def notify_many(user_ids: Iterable[Optional[str]], title: str, message: str, **options) -> None:
    for user_id in {uid for uid in user_ids if uid}:
        send_notification(user_id, title, message, **options)
