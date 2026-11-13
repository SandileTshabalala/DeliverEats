"""
Outgoing messages: SMS through Africa's Talking, email through Resend.

Both functions return True/False and NEVER raise: a failed SMS must not break
an order. Each provider is optional; with no keys set the message is only logged.

Africa's Talking: https://developers.africastalking.com/docs/sms/sending/bulk
Resend:           https://resend.com/docs/api-reference/emails/send-email
"""
import html
import re
from typing import Optional

import requests

from app.core.config import settings
from app.core.locger import logger

AT_LIVE_URL = "https://api.africastalking.com/version1/messaging"
AT_SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/messaging"
RESEND_URL = "https://api.resend.com/emails"

TIMEOUT_SECONDS = 10
# One SMS is 160 characters; longer texts are billed as several messages
SMS_MAX_LENGTH = 160


def sms_configured() -> bool:
    return bool(settings.AT_USERNAME and settings.AT_API_KEY)


def email_configured() -> bool:
    return bool(settings.RESEND_API_KEY and settings.EMAIL_FROM)


def normalize_phone(number: Optional[str]) -> Optional[str]:
    """
    South African numbers in any common spelling -> +27XXXXXXXXX.
    Returns None for anything that is clearly not a phone number, so we never
    pay for an SMS that cannot be delivered.
    """
    if not number:
        return None
    digits = re.sub(r"[^\d+]", "", number.strip())
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if digits.startswith("+"):
        candidate = "+" + re.sub(r"\D", "", digits)
    elif digits.startswith("0") and len(digits) == 10:
        candidate = settings.DEFAULT_COUNTRY_CODE + digits[1:]
    elif digits.startswith(settings.DEFAULT_COUNTRY_CODE.lstrip("+")) and len(digits) >= 11:
        candidate = "+" + digits
    else:
        return None
    return candidate if 11 <= len(candidate) <= 16 else None


def send_sms(to: Optional[str], message: str) -> bool:
    phone = normalize_phone(to)
    if not phone:
        logger.warning(f"SMS skipped: not a valid phone number ({to!r})")
        return False
    text = message.strip()
    if len(text) > SMS_MAX_LENGTH:
        text = text[:SMS_MAX_LENGTH - 3].rstrip() + "..."
    if not sms_configured():
        logger.info(f"[SMS not configured] to {phone}: {text}")
        return False

    data = {"username": settings.AT_USERNAME, "to": phone, "message": text}
    if settings.AT_SENDER_ID:
        data["from"] = settings.AT_SENDER_ID
    try:
        response = requests.post(
            AT_SANDBOX_URL if settings.AT_SANDBOX else AT_LIVE_URL,
            data=data,
            headers={"apiKey": settings.AT_API_KEY, "Accept": "application/json"},
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code not in (200, 201):
            logger.error(f"Africa's Talking rejected SMS to {phone}: HTTP {response.status_code} {response.text[:200]}")
            return False
        recipients = (response.json().get("SMSMessageData") or {}).get("Recipients") or []
        # statusCode 100-102 = processed / sent / queued. Anything else is a failure
        # (e.g. 403 invalid number, 405 insufficient balance, 406 opted out).
        delivered = any(int(r.get("statusCode", 0)) in (100, 101, 102) for r in recipients)
        if not delivered:
            logger.error(f"Africa's Talking did not send SMS to {phone}: {response.text[:200]}")
        return delivered
    except (requests.RequestException, ValueError) as exc:
        logger.error(f"SMS to {phone} failed: {exc}")
        return False


def render_email(title: str, message: str, button_label: Optional[str] = None, button_url: Optional[str] = None) -> str:
    """Small branded HTML email. All text is escaped."""
    paragraphs = "".join(
        f'<p style="margin:0 0 14px;color:#403a35;font-size:16px;line-height:1.5">{html.escape(line)}</p>'
        for line in message.split("\n") if line.strip()
    )
    button = ""
    if button_label and button_url:
        button = (
            f'<p style="margin:24px 0 8px"><a href="{html.escape(button_url, quote=True)}" '
            f'style="background:#d94a0b;color:#ffffff;text-decoration:none;font-weight:bold;'
            f'padding:12px 22px;border-radius:10px;display:inline-block">{html.escape(button_label)}</a></p>'
        )
    return (
        '<div style="background:#f3f0ec;padding:32px 16px;font-family:Arial,Helvetica,sans-serif">'
        '<div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:16px;padding:32px">'
        f'<p style="margin:0 0 20px;color:#d94a0b;font-weight:bold;font-size:14px;letter-spacing:1px;text-transform:uppercase">{html.escape(settings.APP_NAME)}</p>'
        f'<h1 style="margin:0 0 16px;color:#1b1816;font-size:22px">{html.escape(title)}</h1>'
        f'{paragraphs}{button}'
        '</div></div>'
    )


def send_email(to: Optional[str], subject: str, message: str,
               button_label: Optional[str] = None, button_url: Optional[str] = None) -> bool:
    if not to or "@" not in to:
        return False
    if not email_configured():
        logger.info(f"[Email not configured] to {to}: {subject}")
        return False
    text = message + (f"\n\n{button_label}: {button_url}" if button_url else "")
    try:
        response = requests.post(
            RESEND_URL,
            json={
                "from": settings.EMAIL_FROM,
                "to": [to],
                "subject": subject,
                "html": render_email(subject, message, button_label, button_url),
                "text": text,
            },
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code not in (200, 201):
            logger.error(f"Resend rejected email to {to}: HTTP {response.status_code} {response.text[:200]}")
            return False
        return True
    except requests.RequestException as exc:
        logger.error(f"Email to {to} failed: {exc}")
        return False
