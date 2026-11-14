"""
Money and session fixes:
  * a paid online order that gets cancelled is flagged for a refund, and both sides are told
  * a payment that arrives after the order was cancelled never reaches the kitchen: it is refunded
  * cancelling a cash order asks for no refund
  * changing the password signs out other devices, not this one
  * the per-route rate limit works, and never runs the route twice
  * CORS wraps the rate limiter, so the browser can read a 429
"""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.models.order import Order
from app.models.payment import Payment
from app.models.payment_provider import PaymentProvider
from app.models.refresh_tokens import RefreshToken
from app.services import order_service, payment_service
from app.utils.OrderStatus import OrderStatus
from app.utils.PaymentStatus import PaymentStatus

world = {}


@pytest.fixture(scope="module", autouse=True)
def setup(client, admin, login):
    restaurant_id = admin.post("/admin/restaurants", json={
        "name": "Refund Kitchen", "address": "1 Refund Rd", "admin_email": "refund.owner@example.com",
        "admin_password": "password123", "admin_name": "Lebo", "admin_sur_name": "R", "admin_contact_number": "0892220001",
    }).json()["id"]
    plan_id = admin.post("/admin/billing/plans", json={"name": "Refund plan", "price": "150.00"}).json()["id"]
    admin.post(f"/admin/billing/restaurants/{restaurant_id}/payments", json={"plan_id": plan_id})
    owner = login("refund.owner@example.com")
    item = owner.post(f"/menus/restaurant/{restaurant_id}/items", json={"name": "Ribs", "price": "90.00"}).json()["id"]
    client.post("/api/v1/auth/register", json={"email": "refund.customer@example.com", "password": "password123",
                                               "name": "Zola", "sur_name": "C", "contact_number": "0892220002"})
    world.update(restaurant=restaurant_id, item=item, owner=owner, customer=login("refund.customer@example.com"))


def place():
    response = world["customer"].post("/orders/", json={
        "restaurant_id": world["restaurant"], "items": [{"menu_item_id": world["item"], "quantity": 1}]})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def attempt(db, order_id, provider_name="payfast"):
    provider = db.query(PaymentProvider).filter(PaymentProvider.provider_name == provider_name).first()
    if provider is None:
        provider = PaymentProvider(provider_name=provider_name, display_name=provider_name.title())
        db.add(provider)
        db.commit()
    payment = Payment(order_id=order_id, provider_id=provider.id, amount=90, status=PaymentStatus.PENDING,
                      reference=f"{provider_name}_{uuid.uuid4().hex[:8]}")
    db.add(payment)
    db.commit()
    return payment


@pytest.fixture
def messages(monkeypatch):
    sent = []
    record = lambda user_id, title, text, **kw: sent.append((user_id, title, text))
    for module in (payment_service, order_service):
        monkeypatch.setattr(module, "send_notification", record)
    monkeypatch.setattr(payment_service, "notify_restaurant_of_new_order", lambda order: None)
    monkeypatch.setattr(payment_service, "broadcast_order", lambda order, *a: None)
    return sent


def cancel_as_restaurant(order_id):
    return world["owner"].post(f"/orders/{order_id}/status", params={"status": "cancelled"})


# ---------------------------------------------------------------- refunds
def test_restaurant_cancelling_a_paid_order_asks_for_a_refund(db, messages):
    order_id = place()
    payment = attempt(db, order_id)
    payment_service.mark_payment_completed(db, payment, reference="pf-r1")
    messages.clear()

    assert cancel_as_restaurant(order_id).status_code == 200
    db.refresh(payment)
    assert payment.provider_metadata["needs_refund"] is True
    assert payment.provider_metadata["refund_reason"] == "order_cancelled"

    owner_id, customer_id = world["owner"].user["id"], world["customer"].user["id"]
    by_user = {user: (title, text) for user, title, text in messages}
    assert by_user[owner_id][0] == "Refund needed: paid order cancelled"
    assert "R 90.00" in by_user[owner_id][1] and "pf-r1" in by_user[owner_id][1]
    assert "refund" in by_user[customer_id][1] and "R 90.00" in by_user[customer_id][1]


def test_payment_after_the_order_was_cancelled_is_refunded_not_cooked(db, messages, monkeypatch):
    kitchen = []
    monkeypatch.setattr(payment_service, "notify_restaurant_of_new_order", lambda order: kitchen.append(order.id))
    order_id = place()
    payment = attempt(db, order_id)
    assert cancel_as_restaurant(order_id).status_code == 200            # e.g. the unpaid-order clean-up ran first
    messages.clear()

    payment_service.mark_payment_completed(db, payment, reference="pf-late")
    db.refresh(payment)
    assert payment.status == PaymentStatus.COMPLETED                     # the money did arrive
    assert payment.provider_metadata["needs_refund"] is True
    assert payment.provider_metadata["refund_reason"] == "paid_after_cancel"
    assert kitchen == []                                                 # never sent to the kitchen
    titles = [title for _, title, _ in messages]
    assert "Payment received" not in titles and "Refund needed: paid order cancelled" in titles
    assert db.query(Order).filter(Order.id == order_id).one().status == OrderStatus.CANCELLED


def test_no_driver_in_time_refunds_a_paid_order(db, messages):
    order_id = place()
    payment = attempt(db, order_id)
    payment_service.mark_payment_completed(db, payment, reference="pf-wait")
    order = db.query(Order).filter(Order.id == order_id).one()
    order.status = OrderStatus.WAITING_FOR_DRIVER
    order.driver_wait_started_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=3)
    db.commit()
    messages.clear()

    order_service.cancel_stale_orders(db)
    db.refresh(payment)
    assert payment.provider_metadata["refund_reason"] == "no_driver"
    assert any(title == "Refund needed: paid order cancelled" for _, title, _ in messages)


def test_cancelling_a_cash_order_asks_for_no_refund(db, messages):
    order_id = place()
    attempt(db, order_id, provider_name="cash")
    messages.clear()

    assert cancel_as_restaurant(order_id).status_code == 200
    titles = [title for _, title, _ in messages]
    assert not any(title.startswith("Refund needed") for title in titles), messages
    assert any("was cancelled" in text for _, _, text in messages)


# ---------------------------------------------------------------- password change
def test_changing_password_signs_out_other_devices_only(client, db):
    client.post("/api/v1/auth/register", json={"email": "pw.change@example.com", "password": "password123",
                                               "name": "Nandi", "sur_name": "P", "contact_number": "0892220003"})
    response = client.post("/api/v1/auth/login", data={"username": "pw.change@example.com", "password": "password123"})
    user_id, token = response.json()["user"]["id"], response.json()["access_token"]
    this_device = response.cookies.get("refresh_token") or client.cookies.get("refresh_token")
    other = RefreshToken(token_hash=hashlib.sha256(b"other-phone").hexdigest(), user_id=user_id,
                         expires_at=datetime.now(timezone.utc) + timedelta(days=1), user_agent="phone", ip_address="1.2.3.4")
    db.add(other)
    db.commit()

    changed = client.post("/api/v1/auth/change-password", headers={"Authorization": f"Bearer {token}"},
                          cookies={"refresh_token": this_device},
                          json={"current_password": "password123", "new_password": "a-new-password"})
    assert changed.status_code == 200, changed.text

    db.expire_all()
    assert db.query(RefreshToken).filter(RefreshToken.id == other.id).one().is_revoked is True
    mine = db.query(RefreshToken).filter(RefreshToken.token_hash == hashlib.sha256(this_device.encode()).hexdigest()).one()
    assert mine.is_revoked is False


# ---------------------------------------------------------------- rate limiting
def test_route_rate_limit_blocks_and_runs_the_route_once():
    from app.core.rate_limit import rate_limit

    calls = []
    mini = FastAPI()

    @mini.post("/thing")
    @rate_limit(f"test-{uuid.uuid4().hex}", limit=2, window=60)
    def thing(request: Request):
        calls.append(1)
        raise HTTPException(status_code=400, detail="saved, then failed")

    with TestClient(mini) as c:
        assert c.post("/thing").status_code == 400
        assert len(calls) == 1                                           # not run a second time after the error
        assert c.post("/thing").status_code == 400
        blocked = c.post("/thing")
        assert blocked.status_code == 429 and blocked.headers.get("retry-after")
        assert len(calls) == 2


def test_cors_wraps_the_rate_limiter():
    from app.core.rate_limit import RateLimitMiddleware
    from app.main import app

    order = [m.cls for m in app.user_middleware]                         # first = runs first
    assert order[0] is CORSMiddleware
    assert order.index(CORSMiddleware) < order.index(RateLimitMiddleware)
