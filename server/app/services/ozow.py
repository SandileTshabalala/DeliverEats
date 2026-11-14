"""
Ozow (instant EFT) through Ozow's One API: https://hub.ozow.com

Flow
----
1. Get an OAuth access token with the restaurant's client id and secret.
2. Create a payment request; Ozow answers with a `redirectUrl` for the customer.
3. The customer pays from their own bank on Ozow's page and is sent back.
4. Neither the return nor Ozow's notification is trusted on its own. The server
   always asks Ozow for the payment's transactions and only counts the order
   as paid when one of them is `Successful`, for the right amount, with our
   reference. That pull check is what makes a forged notification harmless.
"""
import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import requests

LIVE_BASE = "https://one.ozow.com/v1"
STAGING_BASE = "https://stagingone.ozow.com/v1"
TIMEOUT_SECONDS = 20


class OzowError(Exception):
    pass


@dataclass
class OzowCredentials:
    site_code: str
    client_id: str
    client_secret: str
    sandbox: bool = False

    @property
    def base(self) -> str:
        return STAGING_BASE if self.sandbox else LIVE_BASE


def _token_cache_key(creds: OzowCredentials) -> str:
    fingerprint = hashlib.sha256(f"{creds.client_id}:{creds.client_secret}:{creds.sandbox}".encode()).hexdigest()[:24]
    return f"lvovo:ozow_token:{fingerprint}"


def access_token(creds: OzowCredentials, use_cache: bool = True) -> str:
    """OAuth client-credentials token, cached in Redis until shortly before it expires."""
    from app.core import redis as redis_module

    key = _token_cache_key(creds)
    if use_cache:
        try:
            cached = redis_module.redis_client.get(key)
            if cached:
                return cached.decode() if isinstance(cached, bytes) else cached
        except Exception:
            pass

    try:
        response = requests.post(
            f"{creds.base}/token",
            data={
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scope": "payments",
                "grant_type": "client_credentials",
            },
            headers={"Accept": "application/json"},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise OzowError(f"could not reach Ozow: {exc}") from exc
    if response.status_code in (400, 401, 403):
        raise OzowError("Ozow rejected the client id or secret")
    if response.status_code != 200:
        raise OzowError(f"Ozow token request failed with HTTP {response.status_code}")

    body = response.json()
    token = body.get("access_token")
    if not token:
        raise OzowError("Ozow did not return an access token")
    try:
        lifetime = int(body.get("expires_in") or 3600)
        redis_module.redis_client.setex(key, max(60, lifetime - 120), token)
    except Exception:
        pass
    return token


def _bank_reference(text: str) -> str:
    """Shown on the customer's bank statement: letters and digits only, 20 at most."""
    return (re.sub(r"[^A-Za-z0-9]", "", text) or "ORDER")[:20]


def create_payment(
    creds: OzowCredentials,
    *,
    amount,
    merchant_reference: str,
    bank_reference: str,
    return_url: str,
    notify_url: str,
    expires_in_minutes: int = 30,
) -> dict:
    """Returns {"id": <Ozow payment id>, "redirectUrl": <page to send the customer to>}."""
    expire_at = (datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)).replace(microsecond=0)
    payload = {
        "siteCode": creds.site_code,
        "amount": {"currency": "ZAR", "value": float(Decimal(str(amount)).quantize(Decimal("0.01")))},
        "merchantReference": merchant_reference[:50],
        "beneficiaryReference": _bank_reference(bank_reference),
        "expireAt": expire_at.isoformat().replace("+00:00", "Z"),
        "returnUrl": return_url,
        "notifyUrl": notify_url,
    }
    try:
        response = requests.post(
            f"{creds.base}/payments",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token(creds)}",
                "Accept": "application/json",
                # Ozow ignores a repeated request with the same key
                "Idempotency-Key": merchant_reference,
            },
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise OzowError(f"could not reach Ozow: {exc}") from exc
    if response.status_code not in (200, 201):
        raise OzowError(f"Ozow refused the payment request (HTTP {response.status_code}): {response.text[:300]}")
    body = response.json()
    if not body.get("redirectUrl") or not body.get("id"):
        raise OzowError("Ozow did not return a payment page")
    return body


def is_paid(creds: OzowCredentials, ozow_payment_id: str, merchant_reference: str, expected_amount, created: date) -> Optional[bool]:
    """
    Ask Ozow whether this payment succeeded.
    True  = a Successful transaction for the full amount with our reference
    False = it definitely failed (only Error transactions)
    None  = not finished yet / nothing to decide
    """
    params = {
        "fromDate": (created - timedelta(days=1)).isoformat(),
        "toDate": (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat(),
    }
    try:
        response = requests.get(
            f"{creds.base}/payments/{ozow_payment_id}/transactions",
            params=params,
            headers={"Authorization": f"Bearer {access_token(creds)}", "Accept": "application/json"},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise OzowError(f"could not reach Ozow: {exc}") from exc
    if response.status_code != 200:
        raise OzowError(f"Ozow status check failed with HTTP {response.status_code}")

    transactions = response.json().get("results") or []
    expected = Decimal(str(expected_amount)).quantize(Decimal("0.01"))
    for transaction in transactions:
        if transaction.get("merchantReference") not in (None, merchant_reference):
            continue
        if transaction.get("siteCode") not in (None, creds.site_code):
            continue
        value = (transaction.get("amount") or {}).get("value")
        right_amount = value is not None and abs(Decimal(str(value)) - expected) <= Decimal("0.01")
        if transaction.get("status") == "Successful" and right_amount:
            return True
    if transactions and all(t.get("status") == "Error" for t in transactions):
        return False
    return None
