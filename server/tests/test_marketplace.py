"""
End-to-end test of the marketplace rules, through the real HTTP API:

- restaurants are isolated tenants (orders, menus, drivers, payment settings)
- order money goes to the restaurant's own payment methods / PayFast account
- restaurants pay the platform through subscription plans the admin creates

The tests run in order and build on each other, like a day in the life of the platform.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlencode

import pytest

from app.services import payfast

state = {}

A_PAYFAST = {"merchant_id": "20000001", "merchant_key": "akeyakeyakey1", "passphrase": "mama-thembi-secret"}


def signed_itn(fields: dict, passphrase: str) -> bytes:
    pairs = list(fields.items())
    param_string = "&".join(f"{k}={payfast._encode(v)}" for k, v in pairs) + f"&passphrase={payfast._encode(passphrase)}"
    pairs.append(("signature", hashlib.md5(param_string.encode()).hexdigest()))
    return urlencode(pairs).encode()


@pytest.fixture(autouse=True)
def payfast_confirms(monkeypatch):
    """Stand in for the confirmation call to PayFast's servers."""
    monkeypatch.setattr(payfast, "itn_confirmed_by_payfast", lambda creds, pairs: True)


def new_restaurant(admin, name, email):
    response = admin.post("/admin/restaurants", json={
        "name": name, "address": "12 Vilakazi St, Soweto", "description": "Kasi food",
        "admin_email": email, "admin_password": "password123", "admin_name": "Owner",
        "admin_sur_name": name.split()[0], "admin_contact_number": "0721234567",
    })
    assert response.status_code == 200, response.text
    return response.json()["id"]


def public_restaurant_ids(client):
    return {r["id"] for r in client.get("/api/v1/restaurant/").json()}


# ---------------------------------------------------------------- sign-up
def test_signup_cannot_choose_a_role(client, login):
    response = client.post("/api/v1/auth/register", json={
        "email": "sipho@example.com", "password": "password123", "name": "Sipho", "sur_name": "Nkosi",
        "contact_number": "0731112222", "role": "super_admin", "is_active": True,
    })
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "customer"
    state["customer"] = login("sipho@example.com")
    assert state["customer"].get("/admin/users").status_code == 403


# ---------------------------------------------------------------- plans + subscriptions
def test_restaurants_are_hidden_until_they_have_a_subscription(client, admin, login):
    state["A"] = new_restaurant(admin, "Mama Thembi Kitchen", "thembi@example.com")
    state["B"] = new_restaurant(admin, "Bra Joe Shisanyama", "joe@example.com")
    state["owner_a"] = login("thembi@example.com")
    state["owner_b"] = login("joe@example.com")
    assert public_restaurant_ids(client).isdisjoint({state["A"], state["B"]})


def test_admin_creates_plans_dynamically(admin):
    starter = admin.post("/admin/billing/plans", json={
        "name": "Starter", "price": "199.00", "interval_months": 1, "trial_days": 14, "max_orders_per_month": 3,
    })
    pro = admin.post("/admin/billing/plans", json={"name": "Pro", "price": "399.00", "interval_months": 1})
    assert starter.status_code == 200 and pro.status_code == 200, starter.text + pro.text
    state["starter"], state["pro"] = starter.json()["id"], pro.json()["id"]

    assert admin.post("/admin/billing/plans", json={"name": "Starter", "price": "1"}).status_code == 400
    edited = admin.patch(f"/admin/billing/plans/{state['pro']}", json={"price": "449.00"})
    assert edited.json()["price"] == "449.00"
    # only the platform owner manages plans
    assert state["owner_a"].post("/admin/billing/plans", json={"name": "Free", "price": "0"}).status_code == 403


def test_restaurant_starts_a_trial_and_goes_live(client):
    owner_a = state["owner_a"]
    overview = owner_a.get("/manage/billing").json()
    assert overview["subscription"]["status"] == "none"
    assert {p["name"] for p in overview["plans"]} == {"Starter", "Pro"}

    started = owner_a.post("/manage/billing/subscribe", json={"plan_id": state["starter"]})
    assert started.json()["action"] == "trial_started", started.text
    subscription = owner_a.get("/manage/billing").json()["subscription"]
    assert subscription["status"] == "trialing" and subscription["is_live"]
    assert public_restaurant_ids(client) == {state["A"]}


def test_admin_can_put_a_restaurant_on_a_plan(client, admin):
    response = admin.put(f"/admin/billing/restaurants/{state['B']}/subscription",
                         json={"plan_id": state["pro"], "status": "active"})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "active"
    assert public_restaurant_ids(client) == {state["A"], state["B"]}
    listed = {s["restaurant_name"]: s["status"] for s in admin.get("/admin/billing/subscriptions").json()}
    assert listed == {"Mama Thembi Kitchen": "trialing", "Bra Joe Shisanyama": "active"}


# ---------------------------------------------------------------- tenant isolation: menus
def test_a_restaurant_can_only_edit_its_own_menu():
    owner_a, owner_b = state["owner_a"], state["owner_b"]
    assert owner_a.get("/restaurant/mine").json()["id"] == state["A"]
    assert owner_b.get("/restaurant/mine").json()["id"] == state["B"]

    kota = owner_a.post(f"/menus/restaurant/{state['A']}/items", json={"name": "Kota", "description": "Full house", "price": "45.50"})
    assert kota.status_code == 200, kota.text
    state["kota"] = kota.json()["id"]
    wings = owner_b.post(f"/menus/restaurant/{state['B']}/items", json={"name": "Wings", "price": "60.00"})
    state["wings"] = wings.json()["id"]

    assert owner_b.post(f"/menus/restaurant/{state['A']}/items", json={"name": "Hack", "price": "1"}).status_code == 403
    assert owner_b.patch(f"/menus/{state['kota']}", json={"price": "0.01"}).status_code == 403
    assert owner_b.delete(f"/menus/{state['kota']}").status_code == 403
    assert owner_b.get(f"/menus/restaurant/{state['A']}/manage").status_code == 403
    # the old endpoint accepted any column
    assert owner_a.patch(f"/menus/{state['kota']}", json={"menu_id": "x"}).status_code == 422


# ---------------------------------------------------------------- per-restaurant payments
def test_each_restaurant_sets_its_own_payment_methods(client):
    owner_a, owner_b = state["owner_a"], state["owner_b"]
    config = lambda rid: [m["provider_name"] for m in client.get(f"/api/v1/payments/config?restaurant_id={rid}").json()]

    # default: cash and the shop's card machine
    assert config(state["A"]) == ["cash_delivery", "card_delivery"]

    # online payments need the restaurant's own PayFast details
    assert owner_a.put("/manage/payment-settings", json={"payfast_enabled": True}).status_code == 400
    saved = owner_a.put("/manage/payment-settings", json={
        "payfast_enabled": True, "payfast_sandbox": True, "payfast_merchant_id": A_PAYFAST["merchant_id"],
        "payfast_merchant_key": A_PAYFAST["merchant_key"], "payfast_passphrase": A_PAYFAST["passphrase"],
    })
    assert saved.status_code == 200, saved.text
    assert saved.json()["payfast_merchant_key"] == "********"  # never sent back
    assert A_PAYFAST["merchant_key"] not in saved.text and A_PAYFAST["passphrase"] not in saved.text

    # saving again with the mask keeps the stored key
    owner_a.put("/manage/payment-settings", json={"accepts_cash": True, "payfast_merchant_key": "********"})
    assert config(state["A"]) == ["cash_delivery", "card_delivery", "payfast"]

    # B is card machine only, and A's settings did not leak into B
    owner_b.put("/manage/payment-settings", json={"accepts_cash": False})
    assert config(state["B"]) == ["card_delivery"]
    assert owner_b.get("/manage/payment-settings").json()["payfast_merchant_id"] is None
    assert owner_b.put("/manage/payment-settings", json={"accepts_card_machine": False}).status_code == 400


def test_secrets_are_encrypted_in_the_database(db):
    from app.models.restaurant_payment_settings import RestaurantPaymentSettings
    row = db.query(RestaurantPaymentSettings).filter_by(restaurant_id=state["A"]).first()
    assert row.payfast_merchant_key_enc and A_PAYFAST["merchant_key"] not in row.payfast_merchant_key_enc
    assert A_PAYFAST["passphrase"] not in row.payfast_passphrase_enc


# ---------------------------------------------------------------- team: drivers + staff
def test_drivers_and_staff_belong_to_one_restaurant(login):
    owner_a, owner_b = state["owner_a"], state["owner_b"]
    person = lambda email: {"email": email, "password": "password123", "name": "T", "sur_name": "M", "contact_number": "0700000000"}

    # B's driver exists first and is free: it must never get A's orders
    assert owner_b.post("/manage/drivers", json={**person("driver.b@example.com"), "vehicle_type": "bike"}).status_code == 200
    state["driver_b"] = login("driver.b@example.com")

    staff = owner_a.post("/manage/staff", json=person("cashier.a@example.com"))
    assert staff.status_code == 200, staff.text
    cashier = login("cashier.a@example.com")
    state["cashier_a"] = cashier

    assert [d["email"] for d in owner_b.get("/manage/drivers").json()] == ["driver.b@example.com"]
    assert owner_a.get("/manage/drivers").json() == []
    assert {s["email"] for s in owner_a.get("/manage/staff").json()} == {"thembi@example.com", "cashier.a@example.com"}

    # staff work for the same restaurant but cannot touch money or the team
    assert cashier.get("/restaurant/mine").json()["id"] == state["A"]
    assert cashier.put("/manage/payment-settings", json={"accepts_cash": False}).status_code == 403
    assert cashier.post("/manage/billing/subscribe", json={"plan_id": state["pro"]}).status_code == 403
    assert cashier.post("/manage/staff", json=person("x@example.com")).status_code == 403


# ---------------------------------------------------------------- orders
def place_order(restaurant, item, quantity=2, **extra):
    return state["customer"].post("/orders/", json={
        "restaurant_id": state[restaurant], "items": [{"menu_item_id": state[item], "quantity": quantity}], **extra,
    })


def test_order_total_is_calculated_by_the_server():
    response = place_order("A", "kota", total="0.01", customer_id="someone-else")
    assert response.status_code == 200, response.text
    order = response.json()
    assert Decimal(order["total_amount"]) == Decimal("91.00")
    assert order["customer_id"] == state["customer"].user["id"]
    assert order["payment_status"] == "unpaid"
    assert "email" not in order["customer"]  # no personal details beyond name and phone
    state["order1"] = order["id"]

    # items from another restaurant cannot be slipped into the order
    assert place_order("A", "wings").status_code == 400


def test_payment_method_must_be_one_the_restaurant_accepts():
    customer = state["customer"]
    order_b = place_order("B", "wings").json()["id"]
    refused = customer.post("/payments/", json={"order_id": order_b, "provider_name": "cash_delivery"})
    assert refused.status_code == 400  # B switched cash off
    assert customer.post("/payments/", json={"order_id": order_b, "provider_name": "card_delivery"}).status_code == 200
    state["order_b"] = order_b

    paid = customer.post("/payments/", json={"order_id": state["order1"], "provider_name": "cash_delivery", "amount": "0.01"})
    assert paid.status_code == 200, paid.text
    assert Decimal(paid.json()["amount"]) == Decimal("91.00")


def test_restaurants_cannot_see_or_touch_each_others_orders():
    owner_a, owner_b = state["owner_a"], state["owner_b"]
    assert [o["id"] for o in owner_a.get("/restaurant/orders").json()] == [state["order1"]]
    assert [o["id"] for o in owner_b.get("/restaurant/orders").json()] == [state["order_b"]]
    assert owner_b.post(f"/orders/{state['order1']}/accept").status_code == 404
    assert owner_b.post(f"/orders/{state['order1']}/status", params={"status": "cancelled"}).status_code == 404
    # staff see their own restaurant's orders
    assert [o["id"] for o in state["cashier_a"].get("/restaurant/orders").json()] == [state["order1"]]


def test_only_the_restaurants_own_driver_gets_the_delivery(login):
    owner_a = state["owner_a"]
    accepted = owner_a.post(f"/orders/{state['order1']}/accept")
    assert accepted.status_code == 200, accepted.text
    # B's driver is free, but A has no driver yet
    assert accepted.json()["status"] == "waiting_for_driver"
    assert accepted.json()["driver_id"] is None
    assert state["driver_b"].get("/orders/driver/jobs").json() == []

    added = owner_a.post("/manage/drivers", json={
        "email": "driver.a@example.com", "password": "password123", "name": "Lucky", "sur_name": "D",
        "contact_number": "0711111111", "vehicle_type": "bicycle",
    })
    assert added.status_code == 200, added.text
    driver_a = login("driver.a@example.com")
    state["driver_a"] = driver_a
    assert driver_a.post("/drivers/availability", params={"available": True}).status_code == 200

    jobs = driver_a.get("/orders/driver/jobs").json()
    assert [j["id"] for j in jobs] == [state["order1"]]
    assert jobs[0]["status"] == "preparing"


def test_order_moves_through_its_steps_in_order():
    owner_a, driver_a, driver_b = state["owner_a"], state["driver_a"], state["driver_b"]
    order = state["order1"]
    step = lambda who, path, status: who.post(path, params={"status": status})

    assert step(driver_a, f"/drivers/orders/{order}/status", "delivered").status_code == 409  # not picked up yet
    assert step(driver_b, f"/drivers/orders/{order}/status", "picked_up").status_code == 404  # not their order
    assert step(owner_a, f"/orders/{order}/status", "ready").status_code == 200
    assert step(driver_a, f"/drivers/orders/{order}/status", "picked_up").status_code == 200
    assert step(owner_a, f"/orders/{order}/status", "cancelled").status_code == 409  # already on the road
    assert step(driver_a, f"/drivers/orders/{order}/status", "delivered").status_code == 200

    done = state["customer"].get("/orders/my").json()
    delivered = next(o for o in done if o["id"] == order)
    assert delivered["status"] == "delivered"
    assert delivered["payment_status"] == "completed"  # cash was collected at the door


# ---------------------------------------------------------------- PayFast: money goes to the restaurant
def test_online_payment_uses_the_restaurants_own_payfast_account(client):
    customer, owner_a = state["customer"], state["owner_a"]
    order = place_order("A", "kota", quantity=1).json()
    session = customer.post("/payments/", json={"order_id": order["id"], "provider_name": "payfast"})
    assert session.status_code == 200, session.text
    session = session.json()
    fields = session["checkout_fields"]

    assert session["checkout_url"] == "https://sandbox.payfast.co.za/eng/process"
    assert fields["merchant_id"] == A_PAYFAST["merchant_id"]  # the shop's account, not the platform's
    assert fields["amount"] == "45.50"
    assert fields["notify_url"] == "https://api.example.test/api/v1/payments/payfast/notify"
    assert fields["signature"] == payfast.sign_checkout(fields, A_PAYFAST["passphrase"])

    # coming back from PayFast proves nothing: the kitchen cannot start yet
    assert owner_a.post(f"/orders/{order['id']}/accept").status_code == 409

    itn = {
        "m_payment_id": fields["m_payment_id"], "pf_payment_id": "555001", "payment_status": "COMPLETE",
        "item_name": fields["item_name"], "amount_gross": "45.50", "amount_fee": "-1.50", "amount_net": "44.00",
        "merchant_id": A_PAYFAST["merchant_id"],
    }
    notify = lambda body: client.post("/api/v1/payments/payfast/notify", content=body,
                                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    paid_status = lambda: next(o for o in customer.get("/orders/my").json() if o["id"] == order["id"])["payment_status"]

    # forged: signed with a different passphrase, or claiming a smaller amount
    assert notify(signed_itn(itn, "platform-passphrase")).status_code == 200
    assert paid_status() == "pending"
    assert notify(signed_itn({**itn, "amount_gross": "1.00"}, A_PAYFAST["passphrase"])).status_code == 200
    assert paid_status() == "pending"

    # genuine
    assert notify(signed_itn(itn, A_PAYFAST["passphrase"])).status_code == 200
    assert paid_status() == "completed"
    assert owner_a.post(f"/orders/{order['id']}/accept").status_code == 200


def test_plan_order_limit_is_enforced():
    # Starter allows 3 orders a month: A has had 2, the third still goes through
    assert place_order("A", "kota", quantity=1).status_code == 200
    blocked = place_order("A", "kota", quantity=1)
    assert blocked.status_code == 409, blocked.text
    billing = state["owner_a"].get("/manage/billing").json()["subscription"]
    assert billing["limit_reached"] and billing["orders_this_month"] == 3 and billing["orders_limit"] == 3
    # B is on Pro (unlimited)
    assert place_order("B", "wings").status_code == 200


# ---------------------------------------------------------------- subscriptions: restaurants pay the platform
def test_restaurant_pays_subscription_into_the_platform_account(client):
    owner_a = state["owner_a"]
    checkout = owner_a.post("/manage/billing/subscribe", json={"plan_id": state["pro"]})
    assert checkout.status_code == 200, checkout.text
    body = checkout.json()
    fields = body["checkout_fields"]

    assert body["action"] == "checkout"
    assert fields["merchant_id"] == "10000100"  # the platform's account
    assert fields["amount"] == "449.00" and fields["recurring_amount"] == "449.00"
    assert fields["subscription_type"] == "1" and fields["frequency"] == "3" and fields["cycles"] == "0"
    assert fields["signature"] == payfast.sign_checkout(fields, "platform-passphrase")

    before = owner_a.get("/manage/billing").json()["subscription"]
    assert before["plan"]["name"] == "Starter"  # nothing changes until PayFast confirms

    itn = {
        "m_payment_id": fields["m_payment_id"], "pf_payment_id": "777001", "payment_status": "COMPLETE",
        "item_name": fields["item_name"], "amount_gross": "449.00", "amount_fee": "-10.00", "amount_net": "439.00",
        "merchant_id": "10000100", "token": "tok-abc",
    }
    notify = lambda fields_: client.post("/api/v1/billing/payfast/notify", content=signed_itn(fields_, "platform-passphrase"),
                                         headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert notify(itn).status_code == 200

    after = owner_a.get("/manage/billing").json()["subscription"]
    assert after["status"] == "active" and after["plan"]["name"] == "Pro" and after["auto_renews"]
    assert after["limit_reached"] is False  # Pro has no order limit
    first_end = datetime.fromisoformat(after["current_period_end"])
    assert first_end > datetime.fromisoformat(before["current_period_end"])  # remaining trial days were kept

    # the same notification again must not add a second month
    notify(itn)
    assert owner_a.get("/manage/billing").json()["subscription"]["current_period_end"] == after["current_period_end"]

    # next month's automatic charge does
    notify({**itn, "pf_payment_id": "777002"})
    renewed = datetime.fromisoformat(owner_a.get("/manage/billing").json()["subscription"]["current_period_end"])
    assert renewed > first_end
    assert len(owner_a.get("/manage/billing/payments").json()) == 2
    assert place_order("A", "kota", quantity=1).status_code == 200


def test_unpaid_restaurants_get_grace_days_then_close(client, admin):
    now = datetime.now(timezone.utc)
    set_end = lambda days_ago: admin.put(f"/admin/billing/restaurants/{state['B']}/subscription",
                                         json={"current_period_end": (now - timedelta(days=days_ago)).isoformat()}).json()

    assert set_end(2)["status"] == "past_due"  # inside the 5 grace days: still open
    assert state["B"] in public_restaurant_ids(client)

    closed = set_end(6)
    assert closed["status"] == "expired" and closed["is_live"] is False
    assert state["B"] not in public_restaurant_ids(client)
    assert place_order("B", "wings").status_code == 409
    # the owner can still log in and see why
    assert state["owner_b"].get("/manage/billing").json()["subscription"]["status"] == "expired"

    # paid by EFT: the admin records it and the shop reopens
    paid = admin.post(f"/admin/billing/restaurants/{state['B']}/payments",
                      json={"plan_id": state["pro"], "note": "EFT ref 1234"})
    assert paid.status_code == 200 and paid.json()["status"] == "active", paid.text
    assert state["B"] in public_restaurant_ids(client)
    history = admin.get(f"/admin/billing/restaurants/{state['B']}/payments").json()
    assert history[0]["method"] == "manual" and history[0]["reference"] == "EFT ref 1234"


def test_admin_can_suspend_and_plans_in_use_are_retired_not_deleted(client, admin):
    suspended = admin.put(f"/admin/billing/restaurants/{state['A']}/subscription", json={"status": "suspended"})
    assert suspended.json()["is_live"] is False
    assert state["A"] not in public_restaurant_ids(client)
    admin.put(f"/admin/billing/restaurants/{state['A']}/subscription", json={"status": "active"})
    assert state["A"] in public_restaurant_ids(client)

    # Nobody is on Starter any more and nobody ever paid for it: really deleted
    assert admin.delete(f"/admin/billing/plans/{state['starter']}").json()["message"] == "Plan deleted"
    # Pro has subscribers and payment history: kept, but no longer offered
    assert "retired" in admin.delete(f"/admin/billing/plans/{state['pro']}").json()["message"]
    assert state["owner_a"].get("/manage/billing").json()["plans"] == []
    assert state["owner_a"].get("/manage/billing").json()["subscription"]["plan"]["name"] == "Pro"
