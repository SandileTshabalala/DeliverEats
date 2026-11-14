"""
Peach Payments Hosted Checkout: https://developer.peachpayments.com/docs/checkout-hosted

Flow
----
1. The server signs the checkout fields (HMAC-SHA256 with the restaurant's
   secret token) and the browser POSTs them to Peach's checkout page.
   Peach only accepts that POST from a domain the restaurant allowlisted in
   its Peach Dashboard (it checks the Referer).
2. The customer pays (card, Apple Pay, ...) and Peach POSTs the browser back to
   our `shopperResultUrl`. That return proves nothing.
3. Peach sends a webhook to `notificationUrl`. Its signature is checked with the
   same secret token, and the amount and our transaction id must match, before
   the order counts as paid.

Pure helpers, no database access.
"""
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

LIVE_CHECKOUT = "https://secure.peachpayments.com/checkout"
SANDBOX_CHECKOUT = "https://testsecure.peachpayments.com/checkout"

# Peach / OPPWA result codes for a successfully processed payment
SUCCESS_CODE = re.compile(r"^(000\.000\.|000\.100\.1|000\.[36])")
CANCELLED_CODES = {"100.396.101"}


@dataclass
class PeachCredentials:
    entity_id: str
    secret_token: str
    sandbox: bool = False

    @property
    def checkout_url(self) -> str:
        return SANDBOX_CHECKOUT if self.sandbox else LIVE_CHECKOUT


def sign(fields: Dict[str, str], secret_token: str) -> str:
    """All fields (empty ones too) sorted by name, name+value concatenated, HMAC-SHA256, hex."""
    message = "".join(f"{name}{fields[name]}" for name in sorted(fields) if name != "signature")
    return hmac.new(secret_token.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def new_transaction_id() -> str:
    """merchantTransactionId must be 8 to 16 characters and unique."""
    return secrets.token_hex(8)


def build_checkout(
    creds: PeachCredentials,
    *,
    amount,
    merchant_transaction_id: str,
    shopper_result_url: str,
    notification_url: str,
) -> Tuple[str, Dict[str, str]]:
    """Return (url to POST to, signed form fields)."""
    fields = {
        "authentication.entityId": creds.entity_id,
        "amount": f"{Decimal(str(amount)):.2f}",
        "currency": "ZAR",
        "paymentType": "DB",  # debit: take the money now
        "merchantTransactionId": merchant_transaction_id,
        "nonce": secrets.token_hex(16),
        "shopperResultUrl": shopper_result_url,
        "notificationUrl": notification_url,
    }
    fields["signature"] = sign(fields, creds.secret_token)
    return creds.checkout_url, fields


def field(data: Dict[str, str], dotted: str) -> Optional[str]:
    """Peach documents `result.code` but some payloads use `result_code`."""
    return data.get(dotted) or data.get(dotted.replace(".", "_"))


def webhook_signature_valid(
    pairs: List[Tuple[str, str]],
    raw_body: bytes,
    headers: Dict[str, str],
    url: str,
    secret_token: str,
) -> bool:
    """Accept either Peach signing scheme: the `signature` field, or the x-webhook-* headers."""
    data = dict(pairs)
    received = (data.get("signature") or "").lower()
    if received and hmac.compare_digest(sign(data, secret_token), received):
        return True

    header_signature = (headers.get("x-webhook-signature") or "").lower()
    timestamp = headers.get("x-webhook-timestamp")
    webhook_id = headers.get("x-webhook-id")
    if header_signature and timestamp and webhook_id:
        message = f"{timestamp}.{webhook_id}.{url}.{raw_body.decode('utf-8', errors='replace')}"
        expected = hmac.new(secret_token.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, header_signature)
    return False


def outcome(result_code: Optional[str]) -> Optional[str]:
    """'completed', 'failed', or None (still in progress / nothing to do)."""
    code = (result_code or "").strip()
    if SUCCESS_CODE.match(code):
        return "completed"
    if code in CANCELLED_CODES:
        return "failed"
    return None
