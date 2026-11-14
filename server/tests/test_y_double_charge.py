"""
Nobody is charged twice:
  * an order paid through two checkouts is flagged for a refund and both sides are told
  * an earlier successful checkout keeps the order paid while a newer attempt is open
  * a restaurant on a PayFast debit order cannot start a second one
  * one PayFast charge can only ever be recorded once
  * the same "place order" request sent twice creates one order
"""
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.redis import redis_client
from app.models.order import Order
from app.models.payment import Payment
from app.models.payment_provider import PaymentProvider
from app.models.subscription import RestaurantSubscription, SubscriptionPayment
from app.services import payment_service
from app.utils.PaymentStatus import PaymentStatus

world = {}


@pytest.fixture(scope="module", autouse=True)
def setup(client, admin, login):
    restaurant_id = admin.post("/admin/restaurants", json={
        "name": "Twice Kitchen", "address": "1 Twice Rd", "admin_email": "twice.owner@example.com",
        "admin_password": "password123", "admin_name": "Tumi", "admin_sur_name": "T", "admin_contact_number": "0891110001",
    }).json()["id"]
    plan_id = admin.post("/admin/billing/plans", json={"name": "Twice plan", "price": "150.00"}).json()["id"]
    admin.post(f"/admin/billing/restaurants/{restaurant_id}/payments", json={"plan_id": plan_id})
    owner = login("twice.owner@example.com")
    item = owner.post(f"/menus/restaurant/{restaurant_id}/items", json={"name": "Wings", "price": "80.00"}).json()["id"]
    client.post("/api/v1/auth/register", json={"email": "twice.customer@example.com", "password": "password123",
                                               "name": "Ayanda", "sur_name": "C", "contact_number": "0891110002"})
    world.update(restaurant=restaurant_id, plan=plan_id, item=item, owner=owner,
                 customer=login("twice.customer@example.com"))


def post_order(api, key=None, item=None):
    headers = {**api.headers, **({"Idempotency-Key": key} if key else {})}
    return api.client.post("/api/v1/orders/", headers=headers, json={
        "restaurant_id": world["restaurant"], "items": [{"menu_item_id": item or world["item"], "quantity": 1}]})


def place(key=None):
    return post_order(world["customer"], key)


def online_attempt(db, order_id):
    provider = db.query(PaymentProvider).filter(PaymentProvider.provider_name == "payfast").one()
    payment = Payment(order_id=order_id, provider_id=provider.id, amount=80, status=PaymentStatus.PENDING,
                      reference=f"payfast_{order_id}")
    db.add(payment)
    db.commit()
    return payment


@pytest.fixture
def messages(monkeypatch):
    sent = []
    monkeypatch.setattr(payment_service, "send_notification", lambda user_id, title, text, **kw: sent.append((user_id, title, text)))
    monkeypatch.setattr(payment_service, "notify_restaurant_of_new_order", lambda order: None)
    monkeypatch.setattr(payment_service, "broadcast_order", lambda order, *a: None)
    return sent


# ---------------------------------------------------------------- orders paid twice
def test_second_charge_for_one_order_is_flagged_for_refund(db, messages):
    order_id = place().json()["id"]
    first, second = online_attempt(db, order_id), online_attempt(db, order_id)

    payment_service.mark_payment_completed(db, first, reference="pf-1")
    assert [title for _, title, _ in messages] == ["Payment received"]

    payment_service.mark_payment_completed(db, second, reference="pf-2")
    db.refresh(second)
    assert second.status == PaymentStatus.COMPLETED                     # the money did arrive
    assert second.provider_metadata["needs_refund"] is True and second.provider_metadata["duplicate_of"] == first.id

    owner_id = world["owner"].user["id"]
    titles = {(user, title) for user, title, _ in messages[1:]}
    assert titles == {(owner_id, "Refund needed: order paid twice"), (world["customer"].user["id"], "You were charged twice")}
    refund_note = next(text for user, _, text in messages if user == owner_id)
    assert "R 80.00" in refund_note and "pf-2" in refund_note

    # a repeat of the same notification changes nothing and tells nobody again
    payment_service.mark_payment_completed(db, second, reference="pf-2")
    assert len(messages) == 3


def test_earlier_success_keeps_the_order_paid_while_a_new_attempt_is_open(db, messages):
    order_id = place().json()["id"]
    first = online_attempt(db, order_id)
    payment_service.mark_payment_completed(db, first, reference="pf-3")
    online_attempt(db, order_id)                                         # customer started another checkout

    order = db.query(Order).filter(Order.id == order_id).one()
    db.refresh(order)
    assert order.latest_payment.status == PaymentStatus.PENDING
    assert order.payment_status == "completed" and order.is_payment_cleared
    # the customer's order list agrees
    listed = next(o for o in world["customer"].get("/orders/my").json() if o["id"] == order_id)
    assert listed["payment_status"] == "completed"


def test_failed_notification_does_not_undo_a_payment(db, messages):
    order_id = place().json()["id"]
    payment = online_attempt(db, order_id)
    payment_service.mark_payment_completed(db, payment, reference="pf-4")
    payment_service.mark_payment_failed(db, payment)                     # late "failed" for the same payment
    db.refresh(payment)
    assert payment.status == PaymentStatus.COMPLETED


# ---------------------------------------------------------------- subscriptions
def test_no_second_debit_order_while_one_is_running(db, admin):
    subscription = db.query(RestaurantSubscription).filter(RestaurantSubscription.restaurant_id == world["restaurant"]).one()
    subscription.payfast_token = "token-abc"
    db.commit()

    billing = world["owner"].get("/manage/billing").json()
    assert billing["subscription"]["recurring_active"] is True
    refused = world["owner"].post("/manage/billing/subscribe", json={"plan_id": world["plan"]})
    assert refused.status_code == 409 and "charged twice" in refused.json()["detail"]

    # after cancelling the debit order on PayFast, the admin marks it stopped
    stopped = admin.put(f"/admin/billing/restaurants/{world['restaurant']}/subscription", json={"stop_recurring": True})
    assert stopped.status_code == 200, stopped.text
    db.refresh(subscription)
    assert subscription.payfast_token is None
    assert world["owner"].get("/manage/billing").json()["subscription"]["recurring_active"] is False
    assert world["owner"].post("/manage/billing/subscribe", json={"plan_id": world["plan"]}).status_code == 200


def test_one_payfast_charge_is_recorded_once(db):
    def charge(reference):
        return SubscriptionPayment(restaurant_id=world["restaurant"], plan_id=world["plan"], amount=150,
                                   status="completed", method="payfast", reference=reference)
    db.add(charge("pf-sub-1"))
    db.commit()
    db.add(charge("pf-sub-1"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    # manual payments may share a note, and pending rows are not charges yet
    for _ in range(2):
        db.add(SubscriptionPayment(restaurant_id=world["restaurant"], plan_id=world["plan"], amount=150,
                                   status="completed", method="manual", reference="Recorded by admin"))
    db.commit()


# ---------------------------------------------------------------- placing an order
def test_same_order_request_twice_creates_one_order(db):
    key = str(uuid.uuid4())
    before = db.query(Order).filter(Order.restaurant_id == world["restaurant"]).count()
    first, again = place(key), place(key)
    assert first.status_code == again.status_code == 200
    assert first.json()["id"] == again.json()["id"]
    assert db.query(Order).filter(Order.restaurant_id == world["restaurant"]).count() == before + 1

    # a new checkout (new key) is a new order
    assert place(str(uuid.uuid4())).json()["id"] != first.json()["id"]
    # no key at all still works
    assert place().status_code == 200


def test_request_still_running_is_not_repeated(db):
    key = str(uuid.uuid4())
    redis_client.set(f"lvovo:idem:order:{world['customer'].user['id']}:{key}", "__in_progress__", ex=60)
    busy = place(key)
    assert busy.status_code == 409 and "already being placed" in busy.json()["detail"]


def test_failed_order_can_be_retried_with_the_same_key():
    key = str(uuid.uuid4())
    bad = post_order(world["customer"], key, item="does-not-exist")
    assert bad.status_code >= 400
    assert place(key).status_code == 200


def test_keys_belong_to_one_customer(client, login):
    key = str(uuid.uuid4())
    mine = place(key).json()["id"]
    client.post("/api/v1/auth/register", json={"email": "twice.other@example.com", "password": "password123",
                                               "name": "Other", "sur_name": "C", "contact_number": "0891110003"})
    other = login("twice.other@example.com")
    theirs = post_order(other, key)
    assert theirs.status_code == 200 and theirs.json()["id"] != mine
