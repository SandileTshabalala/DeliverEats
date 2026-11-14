"""
Dashboards show real numbers, restaurants manage their own profile and logo,
and there is no built-in admin login.
"""
import os

import pytest

from app.core.config import settings

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
world = {}


@pytest.fixture(scope="module", autouse=True)
def setup(admin, login):
    restaurant_id = admin.post("/admin/restaurants", json={
        "name": "Profile Kitchen", "address": "5 Old Rd", "admin_email": "profile.owner@example.com",
        "admin_password": "password123", "admin_name": "Palesa", "admin_sur_name": "P", "admin_contact_number": "0841110001",
    }).json()["id"]
    plan_id = admin.post("/admin/billing/plans", json={"name": "Profile plan", "price": "250.00"}).json()["id"]
    admin.post(f"/admin/billing/restaurants/{restaurant_id}/payments", json={"plan_id": plan_id})
    owner = login("profile.owner@example.com")
    owner.post("/manage/staff", json={"email": "profile.staff@example.com", "password": "password123",
                                      "name": "S", "sur_name": "T", "contact_number": "0841110002"})
    world.update(restaurant=restaurant_id, owner=owner, staff=login("profile.staff@example.com"))


def public_names(client):
    client.get("/api/v1/restaurant/")
    return {r["name"] for r in client.get("/api/v1/restaurant/").json()}


# ---------------------------------------------------------------- restaurant profile + logo
def test_owner_updates_restaurant_details(client):
    owner = world["owner"]
    assert owner.get("/manage/restaurant").json()["name"] == "Profile Kitchen"
    updated = owner.patch("/manage/restaurant", json={"name": "Palesa's Kitchen", "description": "Home cooked"})
    assert updated.status_code == 200 and updated.json()["description"] == "Home cooked"
    assert "Palesa's Kitchen" in public_names(client)  # customers see it straight away

    assert world["staff"].patch("/manage/restaurant", json={"name": "Hijacked"}).status_code == 403
    assert owner.patch("/manage/restaurant", json={"is_active": False}).status_code == 422  # cannot change that here
    assert owner.patch("/manage/restaurant", json={"name": ""}).status_code == 422


def test_owner_uploads_and_replaces_the_logo(client):
    owner = world["owner"]
    first = owner.post("/manage/restaurant/logo", files={"file": ("logo.png", PNG, "image/png")})
    assert first.status_code == 200, first.text
    path = first.json()["logo_img_url"]
    assert path.startswith("/api/v1/uploads/logos/") and path.endswith(".png")
    assert world["restaurant"] in path and "logo.png" not in path  # our own file name, not the uploaded one

    served = client.get(path)
    assert served.status_code == 200 and served.content == PNG
    on_disk = os.path.join(settings.UPLOAD_DIR, "logos", os.path.basename(path))
    assert os.path.isfile(on_disk)

    # customers get the logo in the restaurant list
    listed = next(r for r in client.get("/api/v1/restaurant/").json() if r["id"] == world["restaurant"])
    assert listed["logo_img_url"] == path

    # a new logo replaces the old file instead of piling up
    second = owner.post("/manage/restaurant/logo", files={"file": ("x.jpeg", JPG, "image/jpeg")}).json()["logo_img_url"]
    assert second.endswith(".jpg") and not os.path.isfile(on_disk)
    assert client.get(path).status_code == 404

    assert owner.delete("/manage/restaurant/logo").json()["logo_img_url"] is None
    assert client.get(second).status_code == 404


def test_logo_upload_rejects_bad_files():
    owner = world["owner"]
    upload = lambda who, name, data, kind: who.post("/manage/restaurant/logo", files={"file": (name, data, kind)})
    # the type is read from the file itself, not from its name or declared type
    assert upload(owner, "logo.png", b"<script>alert(1)</script>", "image/png").status_code == 400
    assert upload(owner, "logo.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>", "image/svg+xml").status_code == 400
    assert upload(owner, "big.png", PNG + b"\x00" * (2 * 1024 * 1024), "image/png").status_code == 413
    assert upload(world["staff"], "logo.png", PNG, "image/png").status_code == 403
    assert owner.get("/manage/restaurant").json()["logo_img_url"] is None


# ---------------------------------------------------------------- real numbers
def test_restaurant_dashboard_numbers_are_real(client, login):
    owner = world["owner"]
    assert owner.get("/manage/stats").json() == {
        "orders_today": 0, "orders_this_month": 0, "sales_today": 0, "sales_this_month": 0,
        "open_orders": 0, "menu_items_available": 0,
    }
    item = owner.post(f"/menus/restaurant/{world['restaurant']}/items", json={"name": "Pap and wors", "price": "40.00"}).json()["id"]
    owner.post("/manage/drivers", json={"email": "profile.driver@example.com", "password": "password123", "name": "D",
                                        "sur_name": "R", "contact_number": "0841110003", "vehicle_type": "bike"})
    client.post("/api/v1/auth/register", json={"email": "profile.customer@example.com", "password": "password123",
                                               "name": "C", "sur_name": "U", "contact_number": "0841110004"})
    customer, driver = login("profile.customer@example.com"), login("profile.driver@example.com")

    order = customer.post("/orders/", json={"restaurant_id": world["restaurant"], "items": [{"menu_item_id": item, "quantity": 3}]}).json()
    customer.post("/payments/", json={"order_id": order["id"], "provider_name": "cash_delivery"})
    stats = owner.get("/manage/stats").json()
    assert (stats["orders_today"], stats["open_orders"], stats["menu_items_available"]) == (1, 1, 1)
    assert float(stats["sales_today"]) == 0  # not earned until it is delivered

    owner.post(f"/orders/{order['id']}/accept")
    owner.post(f"/orders/{order['id']}/status", params={"status": "ready"})
    driver.post(f"/drivers/orders/{order['id']}/status", params={"status": "picked_up"})
    driver.post(f"/drivers/orders/{order['id']}/status", params={"status": "delivered"})
    stats = owner.get("/manage/stats").json()
    assert (float(stats["sales_today"]), float(stats["sales_this_month"]), stats["open_orders"]) == (120.0, 120.0, 0)

    driver_stats = driver.get("/drivers/stats").json()
    assert (driver_stats["completed_deliveries"], driver_stats["reliability_score"]) == (1, 100)


def test_admin_dashboard_numbers_are_real(admin, db):
    from app.models.order import Order
    from app.models.restaurant import Restaurant
    from app.models.subscription import SubscriptionPayment
    from app.utils.OrderStatus import OrderStatus

    stats = admin.get("/admin/stats").json()
    assert stats["restaurants"]["total"] == db.query(Restaurant).count()
    assert 0 < stats["restaurants"]["live"] <= stats["restaurants"]["total"]
    assert stats["orders"]["all_time"] == db.query(Order).filter(Order.status != OrderStatus.CANCELLED).count()
    assert sum(day["orders"] for day in stats["orders"]["last_7_days"]) == stats["orders"]["all_time"]  # all test orders are from today
    assert len(stats["orders"]["last_7_days"]) == 7 and stats["orders"]["last_7_days"][-1]["orders"] == stats["orders"]["today"]

    paid = sum(float(p.amount) for p in db.query(SubscriptionPayment).filter_by(status="completed").all())
    assert float(stats["subscription_income"]["all_time"]) == paid
    assert float(stats["subscription_income"]["this_month"]) == paid
    assert float(stats["subscription_income"]["monthly_recurring"]) > 0
    assert sum(stats["subscriptions"].values()) == stats["restaurants"]["total"]
    assert stats["customers"] > 0 and stats["drivers"] > 0

    assert world["owner"].get("/admin/stats").status_code == 403


def test_admin_manages_restaurants(client, admin):
    rows = admin.get("/admin/restaurants").json()
    mine = next(r for r in rows if r["id"] == world["restaurant"])
    assert mine["owner_email"] == "profile.owner@example.com" and mine["plan_name"] == "Profile plan"
    assert mine["subscription_status"] == "active" and mine["is_live"] and mine["orders_this_month"] == 1

    closed = admin.patch(f"/admin/restaurants/{world['restaurant']}", json={"is_active": False}).json()
    assert closed["is_active"] is False and closed["is_live"] is False
    assert "Palesa's Kitchen" not in public_names(client)
    admin.patch(f"/admin/restaurants/{world['restaurant']}", json={"is_active": True, "address": "7 New Rd"})
    assert "Palesa's Kitchen" in public_names(client)
    assert world["owner"].get("/manage/restaurant").json()["address"] == "7 New Rd"

    assert world["owner"].get("/admin/restaurants").status_code == 403
    assert admin.patch("/admin/restaurants/nope", json={"name": "x"}).status_code == 404


def test_system_status_shows_no_secrets(admin):
    status = admin.get("/admin/system")
    assert status.status_code == 200
    body = status.json()
    assert body["payfast"] == {"configured": True, "sandbox": True}
    assert body["subscriptions"] == {"enforced": True, "grace_days": 5}
    for secret in (settings.JWT_SECRET_KEY, settings.PAYFAST_MERCHANT_KEY, settings.PAYFAST_PASSPHRASE):
        assert secret not in status.text
    assert world["owner"].get("/admin/system").status_code == 403



def test_public_counters_are_real(client, db):
    from app.models.order import Order
    from app.utils.OrderStatus import OrderStatus

    counters = client.get("/api/v1/stats/public").json()
    assert counters["orders_delivered"] <= db.query(Order).filter(Order.status == OrderStatus.DELIVERED).count()
    assert counters["restaurants"] > 0 and set(counters) == {"restaurants", "orders_delivered"}


# ---------------------------------------------------------------- accounts
def test_change_own_password(client, login):
    staff = world["staff"]
    change = lambda current, new: staff.post("/auth/change-password", json={"current_password": current, "new_password": new})
    assert change("wrong-password", "brand-new-pass-1").status_code == 400
    assert change("password123", "short").status_code == 422
    assert change("password123", "password123").status_code == 400
    assert change("password123", "brand-new-pass-1").status_code == 200
    assert client.post("/api/v1/auth/login", data={"username": "profile.staff@example.com", "password": "password123"}).status_code == 401
    assert login("profile.staff@example.com", "brand-new-pass-1").user["email"] == "profile.staff@example.com"


def test_there_is_no_built_in_admin_account(db, monkeypatch, capsys):
    from app.core.roles import Role
    from app.db import init_db as setup_script
    from app.models.user import User

    assert db.query(User).filter(User.email == "admin@lvovo.com").first() is None

    # with an owner already present the script changes nothing
    assert setup_script.init_db() == 0
    assert "already exists" in capsys.readouterr().out

    # with no owner and no ADMIN_* settings it refuses instead of inventing a login
    owners = db.query(User).filter(User.role == Role.SUPER_ADMIN).all()
    for owner in owners:
        owner.role = Role.CUSTOMER
    db.commit()
    try:
        assert setup_script.init_db() == 1
        assert "ADMIN_EMAIL" in capsys.readouterr().out

        monkeypatch.setattr(settings, "ADMIN_EMAIL", "Real.Owner@Example.com")
        monkeypatch.setattr(settings, "ADMIN_CONTACT_NUMBER", "0820000000")
        monkeypatch.setattr(settings, "ADMIN_PASSWORD", "tooshort")
        assert setup_script.init_db() == 1  # weak password refused

        monkeypatch.setattr(settings, "ADMIN_PASSWORD", "a-long-real-password")
        assert setup_script.init_db() == 0
        created = db.query(User).filter(User.email == "real.owner@example.com").first()
        assert created is not None and created.role == Role.SUPER_ADMIN
    finally:
        for owner in owners:
            owner.role = Role.SUPER_ADMIN
        db.commit()


def test_orders_show_who_the_driver_and_customer_are(login):
    """The restaurant, customer and driver see names and numbers, never raw ids."""
    order = world["owner"].get("/restaurant/orders").json()[0]
    assert (order["driver"]["name"], order["driver"]["sur_name"]) == ("D", "R")
    assert order["driver"]["contact_number"] == "0841110003" and order["driver"]["vehicle_type"] == "bike"
    assert (order["customer"]["name"], order["customer"]["contact_number"]) == ("C", "0841110004")
    assert "email" not in order["customer"] and "email" not in order["driver"]

    mine = login("profile.customer@example.com").get("/orders/my").json()[0]
    assert mine["driver"]["contact_number"] == "0841110003" and mine["restaurant_name"]

    job = login("profile.driver@example.com").get("/orders/driver/history").json()[0]
    assert job["customer"]["contact_number"] == "0841110004"
