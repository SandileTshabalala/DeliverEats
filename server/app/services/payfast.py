"""
PayFast (https://developers.payfast.co.za) custom-integration helpers.

Flow
----
1. `build_checkout()` produces the signed form fields. The browser POSTs them to
   PayFast's hosted payment page, so card details never touch this server.
2. The customer pays and is sent back to `return_url` (or `cancel_url`).
   Being redirected back proves NOTHING and must never mark an order as paid.
3. PayFast calls `notify_url` server-to-server (the "ITN"). `validate_itn()`
   runs the four checks PayFast requires before the payment is trusted:
   signature, source address, amount, and a confirmation call back to PayFast.

This module is pure helpers: no database access, so it is easy to unit test.
"""
import hashlib
import hmac
import ipaddress
import socket
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, quote_plus

import requests

LIVE_HOST = "www.payfast.co.za"
SANDBOX_HOST = "sandbox.payfast.co.za"

# Hosts PayFast sends ITNs from
ITN_SOURCE_HOSTS = (
    "www.payfast.co.za",
    "sandbox.payfast.co.za",
    "w1w.payfast.co.za",
    "w2w.payfast.co.za",
)

# The signature depends on field ORDER. This is the order from PayFast's docs.
CHECKOUT_FIELD_ORDER = (
    "merchant_id", "merchant_key", "return_url", "cancel_url", "notify_url",
    "name_first", "name_last", "email_address", "cell_number",
    "m_payment_id", "amount", "item_name", "item_description",
    "custom_int1", "custom_int2", "custom_int3", "custom_int4", "custom_int5",
    "custom_str1", "custom_str2", "custom_str3", "custom_str4", "custom_str5",
    "email_confirmation", "confirmation_address", "payment_method",
    # recurring billing (subscriptions)
    "subscription_type", "billing_date", "recurring_amount", "frequency", "cycles",
)


@dataclass
class PayFastCredentials:
    merchant_id: str
    merchant_key: str
    passphrase: Optional[str] = None
    sandbox: bool = True

    @property
    def host(self) -> str:
        return SANDBOX_HOST if self.sandbox else LIVE_HOST

    @property
    def process_url(self) -> str:
        return f"https://{self.host}/eng/process"

    @property
    def validate_url(self) -> str:
        return f"https://{self.host}/eng/query/validate"


def _encode(value) -> str:
    """URL-encode exactly like PHP's urlencode(), which PayFast signs with."""
    return quote_plus(str(value).strip()).replace("~", "%7E")


def _param_string(pairs: List[Tuple[str, str]], passphrase: Optional[str] = None) -> str:
    param_string = "&".join(f"{key}={_encode(value)}" for key, value in pairs)
    if passphrase:
        param_string += f"&passphrase={_encode(passphrase)}"
    return param_string


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def format_amount(amount) -> str:
    return f"{Decimal(str(amount)):.2f}"


# --------------------------------------------------------------------------
# Checkout
# --------------------------------------------------------------------------
def sign_checkout(fields: Dict[str, str], passphrase: Optional[str] = None) -> str:
    """Signature for the payment form: non-empty fields, in PayFast's documented order."""
    pairs = [
        (name, fields[name])
        for name in CHECKOUT_FIELD_ORDER
        if fields.get(name) not in (None, "")
    ]
    return _md5(_param_string(pairs, passphrase))


def build_checkout(
    creds: PayFastCredentials,
    *,
    payment_id: str,
    amount,
    item_name: str,
    return_url: str,
    cancel_url: str,
    notify_url: str,
    item_description: str = "",
    name_first: str = "",
    name_last: str = "",
    email_address: str = "",
    order_id: str = "",
    extra_fields: Optional[Dict[str, str]] = None,
) -> Tuple[str, Dict[str, str]]:
    """Return (url_to_post_to, ordered_form_fields_including_signature)."""
    raw = {
        "merchant_id": creds.merchant_id,
        "merchant_key": creds.merchant_key,
        "return_url": return_url,
        "cancel_url": cancel_url,
        "notify_url": notify_url,
        "name_first": (name_first or "")[:100],
        "name_last": (name_last or "")[:100],
        "email_address": (email_address or "")[:100],
        "m_payment_id": payment_id,
        "amount": format_amount(amount),
        "item_name": (item_name or "Order")[:100],
        "item_description": (item_description or "")[:255],
        "custom_str1": order_id,
    }
    raw.update(extra_fields or {})
    fields = {
        name: str(raw[name]).strip()
        for name in CHECKOUT_FIELD_ORDER
        if raw.get(name) not in (None, "")
    }
    fields["signature"] = sign_checkout(fields, creds.passphrase)
    return creds.process_url, fields


# --------------------------------------------------------------------------
# ITN (Instant Transaction Notification)
# --------------------------------------------------------------------------
def parse_itn_body(body: bytes) -> List[Tuple[str, str]]:
    """Parse the raw POST body, keeping the field order and empty values."""
    return parse_qsl(body.decode("utf-8", errors="replace"), keep_blank_values=True)


def itn_signature_valid(pairs: List[Tuple[str, str]], passphrase: Optional[str]) -> bool:
    """Every posted field except `signature`, in the order PayFast sent them."""
    received = dict(pairs).get("signature", "")
    data = [(key, value) for key, value in pairs if key != "signature"]
    expected = _md5(_param_string(data, passphrase))
    return hmac.compare_digest(expected, received.lower())


def payfast_ip_addresses() -> set:
    addresses = set()
    for host in ITN_SOURCE_HOSTS:
        try:
            for info in socket.getaddrinfo(host, None):
                addresses.add(info[4][0])
        except socket.gaierror:
            continue
    return addresses


def itn_source_valid(remote_ip: Optional[str]) -> bool:
    if not remote_ip:
        return False
    try:
        ip = str(ipaddress.ip_address(remote_ip.strip()))
    except ValueError:
        return False
    return ip in payfast_ip_addresses()


def amounts_match(expected, received) -> bool:
    try:
        return abs(Decimal(str(expected)) - Decimal(str(received))) <= Decimal("0.01")
    except (InvalidOperation, TypeError):
        return False


def itn_confirmed_by_payfast(creds: PayFastCredentials, pairs: List[Tuple[str, str]]) -> bool:
    """Ask PayFast itself whether it really sent this notification."""
    data = [(key, value) for key, value in pairs if key != "signature"]
    try:
        response = requests.post(
            creds.validate_url,
            data=_param_string(data),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
    except requests.RequestException:
        return False
    return response.status_code == 200 and response.text.strip().upper().startswith("VALID")


def validate_itn(
    creds: PayFastCredentials,
    pairs: List[Tuple[str, str]],
    *,
    expected_amount,
    remote_ip: Optional[str],
    check_source_ip: bool = True,
) -> Tuple[bool, str]:
    """Run all PayFast security checks. Returns (ok, reason_if_not_ok)."""
    data = dict(pairs)

    if data.get("merchant_id") != creds.merchant_id:
        return False, "merchant_id mismatch"
    if not itn_signature_valid(pairs, creds.passphrase):
        return False, "invalid signature"
    if check_source_ip and not itn_source_valid(remote_ip):
        return False, f"notification did not come from PayFast ({remote_ip})"
    if not amounts_match(expected_amount, data.get("amount_gross")):
        return False, "amount mismatch"
    if not itn_confirmed_by_payfast(creds, pairs):
        return False, "PayFast did not confirm the notification"
    return True, ""
