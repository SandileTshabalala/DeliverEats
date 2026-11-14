"""
Ozow and Peach Payments, paid into the RESTAURANT's own account.
No real gateway is called: Ozow's API and Peach's webhooks are simulated.
"""
import hashlib
import hmac
from urllib.parse import urlencode

import pytest

from app.services import ozow, peach

world = {}
OZOW_CREDS = {"ozow_site_code": "SITE-001", "ozow_client_id": "client-123", "ozow_client_secret": "ozow-secret-xyz", "ozow_sandbox": True}
PEACH_CREDS = {"peach_entity_id": "8ac7a4ca68c22c4d0168c2caab2e0025", "peach_secret_token": "peach-secret-abc", "peach_sandbox": True}


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {}
        self.text = str(body)

    def json(self):
        return self._body


class FakeOzow:
    """Stands in for Ozow's One API."""

    def __init__(self):
        self.calls = []
        self.payments = {}       # ozow payment id -> merchantReference
        self.transactions = {}   # ozow payment id -> list of transactions
        self.accept_credentials = True

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if url.endswith("/token"):
            if not self.accept_credentials:
                return FakeResponse(401, {"error": "invalid_client"})
            return FakeResponse(200, {"access_token": "tok-1", "token_type": "Bearer", "expires_in": "14400"})
        if url.endswith("/payments"):
            ozow_id = f"oz-{len(self.payments) + 1:04d}-0000-0000-0000-000000000000"
            self.payments[ozow_id] = kwargs["json"]["merchantReference"]
            return FakeResponse(201, {"id": ozow_id, "status": "Created", "redirectUrl": f"https://pay.ozow.test/{ozow_id}"})
        raise AssertionError(url)

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        ozow_id = url.rstrip("/").split("/")[-2]
        return FakeResponse(200, {"results": self.transactions.get(ozow_id, [])})

    def pay(self, ozow_id, status="Successful", amount=None, reference=None):
        self.transactions[ozow_id] = [{
            "id": "tx-1", "siteCode": "SITE-001", "status": status, "institution": "Capitec",
            "merchantReference": reference or self.payments[ozow_id],
            "amount": {"currency": "ZAR", "value": amount}, "createdDate": "2026-11-14T10:00:00Z",
        }]


@pytest.fixture
def fake_ozow(monkeypatch):
    fake = FakeOzow()
    monkeypatch.setattr(ozow.requests, "post", fake.post)
    monkeypatch.setattr(ozow.requests, "get", fake.get)
    from app.core import redis as redis_module
    for key in redis_module.redis_client.keys("lvovo:ozow_token:*"):
        redis_module.redis_client.delete(key)
    return fake


@pytest.fixture(scope="module", autouse=True)
def setup(client, admin, login):
    restaurant_id = admin.post("/admin/restaurants", json={
        "name": "Gateway Grill", "address": "8 Pay Rd", "admin_email": "gateway.owner@example.com",
        "admin_password": "password123", "admin_name": "G", "admin_sur_name": "O", "admin_contact_number": "0881110001",
    }).json()["id"]
    plan_id = admin.post("/admin/billing/plans", json={"name": "Gateway plan", "price": "100.00"}).json()["id"]
    admin.post(f"/admin/billing/restaurants/{restaurant_id}/payments", json={"plan_id": plan_id})
    owner = login("gateway.owner@example.com")
    item = owner.post(f"/menus/restaurant/{restaurant_id}/items", json={"name": "Wors roll", "price": "35.00"}).json()["id"]
    client.post("/api/v1/auth/register", json={"email": "gateway.customer@example.com", "password": "password123",
                                               "name": "P", "sur_name": "C", "contact_number": "0881110002"})
    world.update(restaurant=restaurant_id, item=item, owner=owner, customer=login("gateway.customer@example.com"))


def methods(client):
    return [m["provider_name"] for m in client.get(f"/api/v1/payments/config?restaurant_id={world['restaurant']}").json()]


def new_order(quantity=2):
    return world["customer"].post("/orders/", json={
        "restaurant_id": world["restaurant"], "items": [{"menu_item_id": world["item"], "quantity": quantity}],
    }).json()


def payment_status(order_id):
    return next(o for o in world["customer"].get("/orders/my").json() if o["id"] == order_id)["payment_status"]


# ---------------------------------------------------------------- defaults
def test_card_machine_is_off_until_the_owner_switches_it_on(client):
    assert methods(client) == ["cash_delivery"]
    settings_now = world["owner"].get("/manage/payment-settings").json()
    assert settings_now["accepts_card_machine"] is False and settings_now["ozow_enabled"] is False
    world["owner"].put("/manage/payment-settings", json={"accepts_card_machine": True})
    assert methods(client) == ["cash_delivery", "card_delivery"]


# ---------------------------------------------------------------- Ozow
def test_ozow_credentials_are_checked_when_saved(client, fake_ozow):
    owner = world["owner"]
    assert owner.put("/manage/payment-settings", json={"ozow_enabled": True}).status_code == 400  # details missing

    fake_ozow.accept_credentials = False
    refused = owner.put("/manage/payment-settings", json={"ozow_enabled": True, **OZOW_CREDS})
    assert refused.status_code == 400 and "Could not connect to Ozow" in refused.json()["detail"]
    assert "ozow" not in methods(client)

    fake_ozow.accept_credentials = True
    saved = owner.put("/manage/payment-settings", json={"ozow_enabled": True, **OZOW_CREDS})
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["ozow_client_secret"] == "********" and "ozow-secret-xyz" not in saved.text
    assert body["ozow_site_code"] == "SITE-001" and body["ozow_sandbox"] is True
    token_call = next(c for c in fake_ozow.calls if c[1].endswith("/token"))
    assert token_call[1] == "https://stagingone.ozow.com/v1/token"
    assert token_call[2]["data"] == {"client_id": "client-123", "client_secret": "ozow-secret-xyz",
                                     "scope": "payments", "grant_type": "client_credentials"}
    assert methods(client) == ["cash_delivery", "card_delivery", "ozow"]


def test_ozow_payment_is_only_paid_when_ozow_confirms_it(client, fake_ozow):
    customer, owner = world["customer"], world["owner"]
    order = new_order()
    session = customer.post("/payments/", json={"order_id": order["id"], "provider_name": "ozow"})
    assert session.status_code == 200, session.text
    session = session.json()
    ozow_id = session["checkout_url"].rsplit("/", 1)[-1]
    assert session["checkout_url"] == f"https://pay.ozow.test/{ozow_id}" and session["checkout_fields"] is None

    created = next(c for c in fake_ozow.calls if c[1].endswith("/payments"))[2]
    assert created["headers"]["Authorization"] == "Bearer tok-1"
    request = created["json"]
    assert request["siteCode"] == "SITE-001"
    assert request["amount"] == {"currency": "ZAR", "value": 70.0}
    assert request["merchantReference"] == session["id"]
    assert request["beneficiaryReference"].isalnum() and len(request["beneficiaryReference"]) <= 20
    assert request["notifyUrl"] == "https://api.example.test/api/v1/payments/ozow/notify"
    assert request["returnUrl"] == f"http://localhost:5173/customer/payment?status=returned&order={order['id']}"
    assert request["expireAt"].endswith("Z")

    # unpaid: the kitchen cannot start, and an early notification changes nothing
    assert owner.post(f"/orders/{order['id']}/accept").status_code == 409
    notify = lambda body: client.post("/api/v1/payments/ozow/notify", content=urlencode(body),
                                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert notify({"TransactionReference": session["id"], "Status": "Complete", "Amount": "70.00"}).status_code == 200
    assert payment_status(order["id"]) == "pending"  # Ozow itself has no successful transaction

    # a "successful" transaction for less than the order total is not enough
    fake_ozow.pay(ozow_id, amount=1.00)
    notify({"TransactionReference": session["id"]})
    assert payment_status(order["id"]) == "pending"

    fake_ozow.pay(ozow_id, amount=70.00)
    notify({"TransactionReference": session["id"]})
    assert payment_status(order["id"]) == "completed"
    assert owner.post(f"/orders/{order['id']}/accept").status_code == 200
    world["ozow_order"] = order["id"]


def test_returning_customer_triggers_a_check(fake_ozow):
    customer = world["customer"]
    order = new_order(quantity=1)
    session = customer.post("/payments/", json={"order_id": order["id"], "provider_name": "ozow"}).json()
    ozow_id = session["checkout_url"].rsplit("/", 1)[-1]
    assert customer.post(f"/payments/order/{order['id']}/check").json()["payment_status"] == "pending"
    fake_ozow.pay(ozow_id, amount=35.00)
    assert customer.post(f"/payments/order/{order['id']}/check").json()["payment_status"] == "completed"


def test_background_check_and_failed_payments(db, fake_ozow):
    from app.services.payment_service import check_pending_ozow_payments
    customer = world["customer"]
    paid_later, failed = new_order(quantity=1), new_order(quantity=1)
    first = customer.post("/payments/", json={"order_id": paid_later["id"], "provider_name": "ozow"}).json()
    second = customer.post("/payments/", json={"order_id": failed["id"], "provider_name": "ozow"}).json()
    fake_ozow.pay(first["checkout_url"].rsplit("/", 1)[-1], amount=35.00)
    fake_ozow.pay(second["checkout_url"].rsplit("/", 1)[-1], status="Error", amount=35.00)

    assert check_pending_ozow_payments(db) >= 2
    assert payment_status(paid_later["id"]) == "completed"
    assert payment_status(failed["id"]) == "failed"


def test_ozow_notification_for_unknown_payment_is_ignored(client, fake_ozow):
    before = len(fake_ozow.calls)
    response = client.post("/api/v1/payments/ozow/notify", json={"type": "transaction.complete", "data": {"id": "nope"}})
    assert response.status_code == 200 and len(fake_ozow.calls) == before  # nothing asked of Ozow


# ---------------------------------------------------------------- Peach Payments
def signed_peach(fields, secret=PEACH_CREDS["peach_secret_token"]):
    message = "".join(f"{k}{fields[k]}" for k in sorted(fields))
    return {**fields, "signature": hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()}


def peach_notify(client, body: dict, headers=None):
    return client.post("/api/v1/payments/peach/notify", content=urlencode(body),
                       headers={"Content-Type": "application/x-www-form-urlencoded", **(headers or {})})


def test_peach_setup_and_checkout_fields(client):
    owner = world["owner"]
    assert owner.put("/manage/payment-settings", json={"peach_enabled": True}).status_code == 400
    saved = owner.put("/manage/payment-settings", json={"peach_enabled": True, **PEACH_CREDS})
    assert saved.status_code == 200 and saved.json()["peach_secret_token"] == "********"
    assert "peach-secret-abc" not in saved.text
    assert methods(client)[-1] == "peach"

    order = new_order()
    session = world["customer"].post("/payments/", json={"order_id": order["id"], "provider_name": "peach"}).json()
    fields = session["checkout_fields"]
    assert session["checkout_url"] == "https://testsecure.peachpayments.com/checkout"
    assert fields["authentication.entityId"] == PEACH_CREDS["peach_entity_id"]
    assert (fields["amount"], fields["currency"], fields["paymentType"]) == ("70.00", "ZAR", "DB")
    assert 8 <= len(fields["merchantTransactionId"]) <= 16 and fields["nonce"]
    assert fields["notificationUrl"] == "https://api.example.test/api/v1/payments/peach/notify"
    assert fields["shopperResultUrl"] == f"https://api.example.test/api/v1/payments/peach/return?order={order['id']}"
    unsigned = {k: v for k, v in fields.items() if k != "signature"}
    assert fields["signature"] == signed_peach(unsigned)["signature"]
    world.update(peach_order=order["id"], peach_txn=fields["merchantTransactionId"])


def test_peach_webhook_must_be_genuine(client):
    base = {"merchantTransactionId": world["peach_txn"], "amount": "70.00", "currency": "ZAR",
            "paymentType": "DB", "result.code": "000.100.110", "result.description": "Request successfully processed",
            "id": "8ac7a4a1", "checkoutId": "chk-1", "timestamp": "2026-11-14T10:00:00Z"}

    # forged: wrong secret, then right secret but a smaller amount, then no signature at all
    assert peach_notify(client, signed_peach(base, secret="guess")).status_code == 200
    assert peach_notify(client, signed_peach({**base, "amount": "1.00"})).status_code == 200
    assert peach_notify(client, base).status_code == 200
    assert payment_status(world["peach_order"]) == "pending"

    # still in progress: nothing changes
    peach_notify(client, signed_peach({**base, "result.code": "000.200.000"}))
    assert payment_status(world["peach_order"]) == "pending"

    assert peach_notify(client, signed_peach(base)).status_code == 200
    assert payment_status(world["peach_order"]) == "completed"


def test_peach_header_signature_and_cancellation(client):
    order = new_order(quantity=1)
    fields = world["customer"].post("/payments/", json={"order_id": order["id"], "provider_name": "peach"}).json()["checkout_fields"]
    body = urlencode({"merchantTransactionId": fields["merchantTransactionId"], "amount": "35.00", "currency": "ZAR",
                      "result.code": "100.396.101", "result.description": "Cancelled by user"})
    url = "https://api.example.test/api/v1/payments/peach/notify"
    message = f"1763100000.wh-1.{url}.{body}"
    signature = hmac.new(PEACH_CREDS["peach_secret_token"].encode(), message.encode(), hashlib.sha256).hexdigest()
    response = client.post("/api/v1/payments/peach/notify", content=body, headers={
        "Content-Type": "application/x-www-form-urlencoded", "x-webhook-timestamp": "1763100000",
        "x-webhook-id": "wh-1", "x-webhook-signature": signature, "x-webhook-signature-algorithm": "HmacSHA256",
    })
    assert response.status_code == 200
    assert payment_status(order["id"]) == "failed"


def test_peach_return_bounces_the_browser_to_the_orders_page(client):
    order_id = world["peach_order"]
    back = client.post(f"/api/v1/payments/peach/return?order={order_id}", content=urlencode({"result.code": "000.100.110"}),
                       headers={"Content-Type": "application/x-www-form-urlencoded"}, follow_redirects=False)
    assert back.status_code == 303
    assert back.headers["location"] == f"http://localhost:5173/customer/payment?status=returned&order={order_id}"
    cancelled = client.post("/api/v1/payments/peach/return?order=<script>", content=urlencode({"result.code": "100.396.101"}),
                            headers={"Content-Type": "application/x-www-form-urlencoded"}, follow_redirects=False)
    assert cancelled.headers["location"].endswith("?status=cancelled&order=script")  # nothing unsafe passed through


def test_peach_result_codes():
    assert peach.outcome("000.000.000") == "completed"
    assert peach.outcome("000.100.110") == "completed"
    assert peach.outcome("000.200.100") is None       # created / pending
    assert peach.outcome("100.396.104") is None       # uncertain: wait for the next webhook
    assert peach.outcome("100.396.101") == "failed"
    assert peach.outcome("") is None


def test_gateway_secrets_are_encrypted(db):
    from app.models.restaurant_payment_settings import RestaurantPaymentSettings
    row = db.query(RestaurantPaymentSettings).filter_by(restaurant_id=world["restaurant"]).first()
    assert row.ozow_client_secret_enc and "ozow-secret-xyz" not in row.ozow_client_secret_enc
    assert row.peach_secret_token_enc and "peach-secret-abc" not in row.peach_secret_token_enc
