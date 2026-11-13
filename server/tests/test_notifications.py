"""
SMS (Africa's Talking), email (Resend), who gets told what, and password reset.
No real message is ever sent: the HTTP calls to the providers are replaced.
"""
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from app.core.config import settings
from app.services import messaging, notification_service


class FakeResponse:
    def __init__(self, status_code=201, body=None, text=""):
        self.status_code = status_code
        self._body = body or {}
        self.text = text or str(body)

    def json(self):
        return self._body


@pytest.fixture
def providers(monkeypatch):
    """Both providers configured, deliveries run inline, provider HTTP calls recorded."""
    monkeypatch.setattr(settings, "AT_USERNAME", "sandbox")
    monkeypatch.setattr(settings, "AT_API_KEY", "at-key")
    monkeypatch.setattr(settings, "AT_SANDBOX", True)
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_key")
    monkeypatch.setattr(settings, "EMAIL_FROM", "Lvovo <orders@example.test>")
    monkeypatch.setattr(notification_service, "_submit", lambda function, *args: function(*args))

    class Calls(list):
        def sms(self):
            return [c for c in self if "africastalking" in c["url"]]

        def emails(self):
            return [c for c in self if "resend" in c["url"]]

    calls = Calls()

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        if "africastalking" in url:
            return FakeResponse(201, {"SMSMessageData": {"Recipients": [{"statusCode": 101, "status": "Success"}]}})
        return FakeResponse(200, {"id": "email-1"})

    monkeypatch.setattr(messaging.requests, "post", fake_post)
    return calls


# ---------------------------------------------------------------- providers
@pytest.mark.parametrize("typed, expected", [
    ("0721234567", "+27721234567"),
    ("072 123 4567", "+27721234567"),
    ("(072) 123-4567", "+27721234567"),
    ("+27 72 123 4567", "+27721234567"),
    ("27721234567", "+27721234567"),
    ("0027721234567", "+27721234567"),
    ("+254711000000", "+254711000000"),  # other countries keep their own code
    ("12345", None),
    ("not a number", None),
    ("", None),
    (None, None),
])
def test_phone_numbers_are_normalised(typed, expected):
    assert messaging.normalize_phone(typed) == expected


def test_sms_request_matches_africas_talking_api(providers):
    assert messaging.send_sms("072 123 4567", "Your order is on its way") is True
    call = providers.sms()[0]
    assert call["url"] == "https://api.sandbox.africastalking.com/version1/messaging"
    assert call["headers"] == {"apiKey": "at-key", "Accept": "application/json"}
    assert call["data"] == {"username": "sandbox", "to": "+27721234567", "message": "Your order is on its way"}


def test_sms_uses_live_url_and_sender_id_when_set(providers, monkeypatch):
    monkeypatch.setattr(settings, "AT_SANDBOX", False)
    monkeypatch.setattr(settings, "AT_SENDER_ID", "LVOVO")
    messaging.send_sms("0721234567", "Hi")
    call = providers.sms()[0]
    assert call["url"] == "https://api.africastalking.com/version1/messaging"
    assert call["data"]["from"] == "LVOVO"


def test_long_sms_is_cut_to_one_message(providers):
    messaging.send_sms("0721234567", "x" * 400)
    assert len(providers.sms()[0]["data"]["message"]) == 160


def test_sms_failures_are_reported_not_raised(providers, monkeypatch):
    assert messaging.send_sms("12345", "Hi") is False and providers.sms() == []  # bad number: no paid attempt

    rejected = FakeResponse(201, {"SMSMessageData": {"Recipients": [{"statusCode": 405, "status": "InsufficientBalance"}]}})
    monkeypatch.setattr(messaging.requests, "post", lambda url, **kw: rejected)
    assert messaging.send_sms("0721234567", "Hi") is False

    def offline(url, **kw):
        raise messaging.requests.ConnectionError("no network")
    monkeypatch.setattr(messaging.requests, "post", offline)
    assert messaging.send_sms("0721234567", "Hi") is False
    assert messaging.send_email("a@example.com", "Hi", "Body") is False


def test_email_request_matches_resend_api(providers):
    assert messaging.send_email("thembi@example.com", "New order", "2 x Kota\nTotal: R 91.00",
                                button_label="Open orders", button_url="https://app.test/restaurant/orders") is True
    call = providers.emails()[0]
    assert call["url"] == "https://api.resend.com/emails"
    assert call["headers"] == {"Authorization": "Bearer re_key"}
    body = call["json"]
    assert body["from"] == "Lvovo <orders@example.test>" and body["to"] == ["thembi@example.com"]
    assert body["subject"] == "New order"
    assert "2 x Kota" in body["html"] and 'href="https://app.test/restaurant/orders"' in body["html"]
    assert body["text"].endswith("Open orders: https://app.test/restaurant/orders")


def test_email_text_is_escaped():
    rendered = messaging.render_email("<script>alert(1)</script>", "Tom & Jerry <b>")
    assert "<script>" not in rendered and "&lt;script&gt;" in rendered and "Tom &amp; Jerry &lt;b&gt;" in rendered


def test_nothing_is_sent_without_provider_keys(monkeypatch):
    sent = []
    monkeypatch.setattr(messaging.requests, "post", lambda url, **kw: sent.append(url))
    monkeypatch.setattr(notification_service, "_submit", lambda function, *args: function(*args))
    assert messaging.send_sms("0721234567", "Hi") is False
    assert messaging.send_email("a@example.com", "Hi", "Body") is False
    notification_service.send_notification("anyone", "Hi", "Body", sms=True, email=True)
    assert sent == []


# ---------------------------------------------------------------- who is told what
def test_order_events_reach_the_right_people(providers, client, admin, login):
    restaurant_id = admin.post("/admin/restaurants", json={
        "name": "Notify Kitchen", "address": "1 Test Rd", "admin_email": "notify.owner@example.com",
        "admin_password": "password123", "admin_name": "Nomsa", "admin_sur_name": "Z", "admin_contact_number": "0821110001",
    }).json()["id"]
    plan_id = admin.post("/admin/billing/plans", json={"name": "Notify plan", "price": "100.00"}).json()["id"]
    providers.clear()
    admin.post(f"/admin/billing/restaurants/{restaurant_id}/payments", json={"plan_id": plan_id})
    # paying the subscription emails the owner a receipt
    receipt = providers.emails()[-1]["json"]
    assert receipt["to"] == ["notify.owner@example.com"] and "Notify plan" in receipt["text"]

    owner = login("notify.owner@example.com")
    item = owner.post(f"/menus/restaurant/{restaurant_id}/items", json={"name": "Bunny Chow", "price": "55.00"}).json()["id"]
    owner.post("/manage/drivers", json={
        "email": "notify.driver@example.com", "password": "password123", "name": "Vusi", "sur_name": "M",
        "contact_number": "0821110002", "vehicle_type": "bike",
    })
    driver = login("notify.driver@example.com")
    client.post("/api/v1/auth/register", json={
        "email": "notify.customer@example.com", "password": "password123", "name": "Lerato", "sur_name": "K",
        "contact_number": "0821110003",
    })
    customer = login("notify.customer@example.com")

    sms_to = lambda: [(c["data"]["to"], c["data"]["message"]) for c in providers.sms()]
    OWNER, DRIVER, CUSTOMER = "+27821110001", "+27821110002", "+27821110003"

    # 1. customer orders and chooses cash: the OWNER is told by SMS and email
    providers.clear()
    order = customer.post("/orders/", json={"restaurant_id": restaurant_id, "items": [{"menu_item_id": item, "quantity": 2}]}).json()
    assert providers == []  # nothing until a payment method is chosen
    customer.post("/payments/", json={"order_id": order["id"], "provider_name": "cash_delivery"})
    ref = order["id"][:8].upper()
    assert sms_to() == [(OWNER, f"New order: #{ref} R 110.00: 2 x Bunny Chow")]
    assert providers.emails()[0]["json"]["to"] == ["notify.owner@example.com"]

    # 2. owner accepts: the DRIVER gets the job, the CUSTOMER hears it is being prepared
    providers.clear()
    assert owner.post(f"/orders/{order['id']}/accept").status_code == 200
    told = dict(sms_to())
    assert set(told) == {DRIVER, CUSTOMER}
    assert f"#{ref}" in told[DRIVER] and "Notify Kitchen" in told[DRIVER]
    assert "accepted" in told[CUSTOMER]

    # 3. ready: nobody is messaged (no SMS spent on a step the customer cannot act on)
    providers.clear()
    owner.post(f"/orders/{order['id']}/status", params={"status": "ready"})
    assert providers == []

    # 4. picked up: customer SMS.  5. delivered: customer email receipt, no SMS
    driver.post(f"/drivers/orders/{order['id']}/status", params={"status": "picked_up"})
    assert sms_to() == [(CUSTOMER, f"Notify Kitchen: Your order #{ref} is on its way to you.")]
    providers.clear()
    driver.post(f"/drivers/orders/{order['id']}/status", params={"status": "delivered"})
    assert providers.sms() == []
    assert providers.emails()[0]["json"]["to"] == ["notify.customer@example.com"]
    assert "R 110.00" in providers.emails()[0]["json"]["text"]


def test_test_message_endpoint_is_admin_only(providers, admin, login):
    assert login("notify.customer@example.com").post("/notifications/test").status_code == 403
    providers.clear()
    assert admin.post("/notifications/test").json() == {"sms": True, "email": True}
    assert len(providers.sms()) == 1 and len(providers.emails()) == 1


# ---------------------------------------------------------------- subscription reminders
def test_subscription_reminders_are_sent_once_per_stage(providers, db):
    from app.models.restaurant import Restaurant
    from app.models.subscription import RestaurantSubscription, utcnow
    from app.services.subscription_service import send_subscription_reminders

    restaurant = db.query(Restaurant).filter(Restaurant.name == "Notify Kitchen").first()
    subscription = db.query(RestaurantSubscription).filter_by(restaurant_id=restaurant.id).first()
    send_subscription_reminders(db)  # flush reminders that belong to other tests' restaurants

    def reminders_after(period_end):
        subscription.current_period_end = period_end
        subscription.payfast_token = None
        db.commit()
        providers.clear()
        send_subscription_reminders(db)
        return [c["data"]["message"] for c in providers.sms() if c["data"]["to"] == "+27821110001"]

    assert reminders_after(utcnow() + timedelta(days=20)) == []          # not due yet
    ending = reminders_after(utcnow() + timedelta(days=2))
    assert len(ending) == 1 and "ends on" in ending[0]
    providers.clear()
    send_subscription_reminders(db)
    assert providers == []                                               # not repeated every run
    overdue = reminders_after(utcnow() - timedelta(days=1))
    assert len(overdue) == 1 and "overdue" in overdue[0]
    closed = reminders_after(utcnow() - timedelta(days=30))
    assert len(closed) == 1 and "hidden from customers" in closed[0]

    # automatic PayFast renewal: no "ending soon" nagging
    subscription.current_period_end = utcnow() + timedelta(days=1, hours=1)
    subscription.payfast_token = "tok"
    db.commit()
    providers.clear()
    send_subscription_reminders(db)
    assert [c for c in providers.sms() if c["data"]["to"] == "+27821110001"] == []


# ---------------------------------------------------------------- password reset
def test_password_reset_by_email(providers, client, login):
    forgot = lambda email: client.post("/api/v1/auth/forgot-password", json={"email": email})

    # unknown address: same answer, nothing sent
    providers.clear()
    unknown = forgot("nobody@example.com")
    assert unknown.status_code == 200 and providers == []

    known = forgot("notify.customer@example.com")
    assert known.json() == unknown.json()
    email = providers.emails()[0]["json"]
    assert email["to"] == ["notify.customer@example.com"] and providers.sms() == []
    link = email["text"].rsplit(" ", 1)[-1]
    assert link.startswith("http://localhost:5173/reset-password?token=")
    token = parse_qs(urlparse(link).query)["token"][0]

    reset = lambda t, password: client.post("/api/v1/auth/reset-password", json={"token": t, "password": password})
    assert reset("x" * 40, "new-password-1").status_code == 400            # made-up token
    assert reset(token, "short").status_code == 422                        # password rules still apply
    assert reset(token, "new-password-1").status_code == 200
    assert reset(token, "another-password").status_code == 400             # link works once

    old = client.post("/api/v1/auth/login", data={"username": "notify.customer@example.com", "password": "password123"})
    assert old.status_code == 401
    assert login("notify.customer@example.com", "new-password-1").user["email"] == "notify.customer@example.com"
