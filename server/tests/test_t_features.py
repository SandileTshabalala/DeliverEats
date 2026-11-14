"""
Categories, open/closed and opening hours, ratings, menu photos, the in-app
notification bell, and the public site details used by the legal pages.
"""
from datetime import datetime

import pytest

from app.core.config import settings
from app.services import restaurant_info

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
world = {}


@pytest.fixture(scope="module", autouse=True)
def setup(client, admin, login):
    restaurant_id = admin.post("/admin/restaurants", json={
        "name": "Feature Kitchen", "address": "3 Feature Rd", "admin_email": "feature.owner@example.com",
        "admin_password": "password123", "admin_name": "Fikile", "admin_sur_name": "F", "admin_contact_number": "0861110001",
    }).json()["id"]
    plan_id = admin.post("/admin/billing/plans", json={"name": "Feature plan", "price": "100.00"}).json()["id"]
    admin.post(f"/admin/billing/restaurants/{restaurant_id}/payments", json={"plan_id": plan_id})
    owner = login("feature.owner@example.com")
    item = owner.post(f"/menus/restaurant/{restaurant_id}/items", json={"name": "Mogodu", "price": "60.00"}).json()["id"]
    owner.post("/manage/staff", json={"email": "feature.staff@example.com", "password": "password123",
                                      "name": "S", "sur_name": "T", "contact_number": "0861110002"})
    owner.post("/manage/drivers", json={"email": "feature.driver@example.com", "password": "password123", "name": "D",
                                        "sur_name": "R", "contact_number": "0861110003", "vehicle_type": "Bicycle"})
    client.post("/api/v1/auth/register", json={"email": "feature.customer@example.com", "password": "password123",
                                               "name": "Thandi", "sur_name": "C", "contact_number": "0861110004"})
    world.update(restaurant=restaurant_id, item=item, owner=owner, staff=login("feature.staff@example.com"),
                 driver=login("feature.driver@example.com"), customer=login("feature.customer@example.com"))


def listed(client):
    client.get("/api/v1/restaurant/")
    return next((r for r in client.get("/api/v1/restaurant/").json() if r["id"] == world["restaurant"]), None)


def order_food():
    return world["customer"].post("/orders/", json={"restaurant_id": world["restaurant"],
                                                    "items": [{"menu_item_id": world["item"], "quantity": 1}]})


# ---------------------------------------------------------------- categories
def option(profile, name):
    return next(o["id"] for o in profile["category_options"] if o["name"] == name)


def test_owner_chooses_a_category_from_the_list(client):
    owner = world["owner"]
    profile = owner.get("/manage/restaurant").json()
    assert profile["category"] is None and profile["category_ids"] == []
    names = [o["name"] for o in profile["category_options"]]
    assert "Shisanyama" in names and profile["max_categories"] == 3
    assert client.get("/api/v1/site").json()["categories"] == names
    assert [c["name"] for c in client.get("/api/v1/categories").json()] == names

    # older screens send one name
    assert owner.patch("/manage/restaurant", json={"category": "Sushi Fusion"}).status_code == 400
    assert owner.patch("/manage/restaurant", json={"category": "Traditional"}).json()["category"] == "Traditional"
    assert listed(client)["category"] == "Traditional"


def test_owner_sells_several_kinds_of_food(client):
    owner = world["owner"]
    profile = owner.get("/manage/restaurant").json()
    chicken, burgers, traditional, pizza = (option(profile, n) for n in ("Chicken", "Burgers", "Traditional", "Pizza"))

    saved = owner.patch("/manage/restaurant", json={"category_ids": [chicken, burgers, traditional]}).json()
    assert saved["category_ids"] == [chicken, burgers, traditional] and saved["category"] == "Chicken"
    card = listed(client)
    assert card["category"] == "Chicken" and card["categories"] == ["Chicken", "Burgers", "Traditional"]

    too_many = owner.patch("/manage/restaurant", json={"category_ids": [chicken, burgers, traditional, pizza]})
    assert too_many.status_code == 400 and "up to 3" in too_many.json()["detail"]
    assert owner.patch("/manage/restaurant", json={"category_ids": ["nope"]}).status_code == 400
    # staff cannot change what the shop sells
    assert world["staff"].patch("/manage/restaurant", json={"category_ids": [pizza]}).status_code == 403


def test_platform_owner_manages_categories(client, admin):
    owner = world["owner"]
    assert owner.get("/admin/categories").status_code == 403
    assert owner.post("/admin/categories", json={"name": "Seafood"}).status_code == 403

    rows = admin.get("/admin/categories").json()
    chicken = next(r for r in rows if r["name"] == "Chicken")
    assert chicken["restaurant_count"] >= 1 and chicken["is_active"] is True

    # add, with no duplicates (case does not matter)
    seafood = admin.post("/admin/categories", json={"name": "  Seafood  "}).json()
    assert seafood["name"] == "Seafood" and seafood["sort_order"] == max(r["sort_order"] for r in rows) + 1
    assert admin.post("/admin/categories", json={"name": "seafood"}).status_code == 400

    # a picture
    with_image = admin.post(f"/admin/categories/{seafood['id']}/image", files={"file": ("x.png", PNG, "image/png")}).json()
    assert with_image["image_url"].startswith("/api/v1/uploads/categories/")
    assert client.get(with_image["image_url"]).status_code == 200
    assert admin.post(f"/admin/categories/{seafood['id']}/image", files={"file": ("x.txt", b"hello", "text/plain")}).status_code == 400
    assert next(c for c in client.get("/api/v1/categories").json() if c["id"] == seafood["id"])["image_url"] == with_image["image_url"]

    # rename: restaurant cards follow
    assert admin.patch(f"/admin/categories/{chicken['id']}", json={"name": "Chicken & Chips"}).json()["name"] == "Chicken & Chips"
    assert listed(client)["categories"][0] == "Chicken & Chips"
    assert owner.get("/manage/restaurant").json()["category"] == "Chicken & Chips"
    assert admin.patch(f"/admin/categories/{chicken['id']}", json={"name": "Burgers"}).status_code == 400

    # hide: gone for customers, main category moves to the next one
    admin.patch(f"/admin/categories/{chicken['id']}", json={"is_active": False})
    assert all(c["id"] != chicken["id"] for c in client.get("/api/v1/categories").json())
    assert listed(client)["category"] == "Burgers"
    admin.patch(f"/admin/categories/{chicken['id']}", json={"is_active": True})
    assert listed(client)["category"] == "Chicken & Chips"

    # reorder
    ids = [r["id"] for r in admin.get("/admin/categories").json()]
    reordered = admin.put("/admin/categories/order", json={"ids": ids[::-1]}).json()
    assert [r["id"] for r in reordered] == ids[::-1]
    assert admin.put("/admin/categories/order", json={"ids": ids[:2]}).status_code == 400
    admin.put("/admin/categories/order", json={"ids": ids})

    # delete: the restaurant keeps its other categories
    assert admin.delete(f"/admin/categories/{chicken['id']}").status_code == 204
    assert listed(client)["categories"] == ["Burgers", "Traditional"]
    assert admin.delete(f"/admin/categories/{seafood['id']}").status_code == 204
    assert admin.patch(f"/admin/categories/{seafood['id']}", json={"name": "x"}).status_code == 404


# ---------------------------------------------------------------- open / closed
def test_opening_hours_logic():
    class Shop:
        accepting_orders, opens_at, closes_at = True, None, None

    at = lambda clock: datetime(2026, 11, 14, *map(int, clock.split(":")))
    shop = Shop()
    assert restaurant_info.is_open_now(shop, at("03:00"))               # no hours: open whenever switched on
    shop.opens_at, shop.closes_at = "09:00", "17:30"
    assert [restaurant_info.is_open_now(shop, at(t)) for t in ("08:59", "09:00", "17:29", "17:30")] == [False, True, True, False]
    shop.opens_at, shop.closes_at = "18:00", "02:00"                    # past midnight
    assert [restaurant_info.is_open_now(shop, at(t)) for t in ("17:00", "18:00", "23:59", "01:30", "02:00")] == [False, True, True, True, False]
    shop.accepting_orders = False
    assert not restaurant_info.is_open_now(shop, at("19:00"))           # the switch wins over the hours


def test_closing_the_kitchen_stops_orders(client):
    owner, staff = world["owner"], world["staff"]
    assert listed(client)["is_open"] is True and order_food().status_code == 200

    # staff can close for the day, but cannot change anything else
    assert staff.patch("/manage/restaurant", json={"accepting_orders": False}).json()["is_open"] is False
    assert staff.patch("/manage/restaurant", json={"name": "Nope"}).status_code == 403
    shop = listed(client)
    assert shop is not None and shop["is_open"] is False  # still listed, shown as closed
    refused = order_food()
    assert refused.status_code == 409 and "closed right now" in refused.json()["detail"]
    assert world["customer"].post("/orders/quote", json={"restaurant_id": world["restaurant"],
                                                         "items": [{"menu_item_id": world["item"], "quantity": 1}]}).status_code == 409
    owner.patch("/manage/restaurant", json={"accepting_orders": True})
    assert listed(client)["is_open"] is True


def test_hours_must_be_valid_and_come_as_a_pair(client, monkeypatch):
    owner = world["owner"]
    assert owner.patch("/manage/restaurant", json={"opens_at": "9am"}).status_code == 422
    assert owner.patch("/manage/restaurant", json={"opens_at": "25:00", "closes_at": "26:00"}).status_code == 422
    assert owner.patch("/manage/restaurant", json={"opens_at": "09:00"}).status_code == 400  # needs a closing time too

    saved = owner.patch("/manage/restaurant", json={"opens_at": "09:00", "closes_at": "17:00"})
    assert saved.status_code == 200 and (saved.json()["opens_at"], saved.json()["closes_at"]) == ("09:00", "17:00")

    monkeypatch.setattr(restaurant_info, "local_now", lambda: datetime(2026, 11, 14, 20, 0))
    late = order_food()
    assert late.status_code == 409 and "It opens at 9:00 AM" in late.json()["detail"]
    monkeypatch.setattr(restaurant_info, "local_now", lambda: datetime(2026, 11, 14, 12, 0))
    assert order_food().status_code == 200

    cleared = owner.patch("/manage/restaurant", json={"opens_at": None, "closes_at": None}).json()
    assert cleared["opens_at"] is None and cleared["is_open"] is True


# ---------------------------------------------------------------- ratings
def deliver_new_order():
    customer, owner, driver = world["customer"], world["owner"], world["driver"]
    order = order_food().json()
    customer.post("/payments/", json={"order_id": order["id"], "provider_name": "cash_delivery"})
    assert owner.post(f"/orders/{order['id']}/accept").status_code == 200
    owner.post(f"/orders/{order['id']}/status", params={"status": "ready"})
    driver.post(f"/drivers/orders/{order['id']}/status", params={"status": "picked_up"})
    assert driver.post(f"/drivers/orders/{order['id']}/status", params={"status": "delivered"}).status_code == 200
    return order["id"]


def test_customer_rates_a_delivered_order(client, login):
    customer = world["customer"]
    # the earlier orders in this file were never delivered: cancel them so the driver is free
    for pending in customer.get("/orders/my").json():
        if pending["status"] == "pending":
            customer.post(f"/orders/{pending['id']}/cancel")

    undelivered = order_food().json()["id"]
    assert customer.post(f"/orders/{undelivered}/review", json={"rating": 5}).status_code == 409
    customer.post(f"/orders/{undelivered}/cancel")

    first, second = deliver_new_order(), deliver_new_order()
    assert customer.post(f"/orders/{first}/review", json={"rating": 6}).status_code == 422
    assert world["owner"].post(f"/orders/{first}/review", json={"rating": 5}).status_code == 403  # not a customer

    rated = customer.post(f"/orders/{first}/review", json={"rating": 5, "comment": "  Best mogodu in the kasi  "})
    assert rated.status_code == 200 and rated.json()["my_rating"] == 5
    assert customer.post(f"/orders/{first}/review", json={"rating": 1}).status_code == 409  # once only
    customer.post(f"/orders/{second}/review", json={"rating": 4})

    mine = {o["id"]: o["my_rating"] for o in customer.get("/orders/my").json()}
    assert (mine[first], mine[second]) == (5, 4)

    shop = listed(client)
    assert (shop["rating"], shop["review_count"]) == (4.5, 2)

    seen = world["owner"].get("/manage/reviews").json()
    assert (seen["rating"], seen["review_count"]) == (4.5, 2)
    best = next(r for r in seen["reviews"] if r["rating"] == 5)
    assert best["comment"] == "Best mogodu in the kasi" and best["customer_name"] == "Thandi"
    assert "email" not in best and "customer_id" not in best

    # someone else's order cannot be rated
    client.post("/api/v1/auth/register", json={"email": "feature.other@example.com", "password": "password123",
                                               "name": "O", "sur_name": "X", "contact_number": "0861110005"})
    assert login("feature.other@example.com").post(f"/orders/{second}/review", json={"rating": 1}).status_code == 404


# ---------------------------------------------------------------- menu photos
def test_menu_item_photo_upload(client):
    owner = world["owner"]
    uploaded = owner.post(f"/menus/{world['item']}/image", files={"file": ("photo.png", PNG, "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    path = uploaded.json()["image_url"]
    assert path.startswith("/api/v1/uploads/menu/") and client.get(path).content == PNG
    menu = client.get(f"/api/v1/menus/restaurant/{world['restaurant']}").json()
    assert menu[0]["image_url"] == path  # customers see it at once (cache was refreshed)

    replaced = owner.post(f"/menus/{world['item']}/image", files={"file": ("p.png", PNG, "image/png")}).json()["image_url"]
    assert replaced != path and client.get(path).status_code == 404

    assert owner.post(f"/menus/{world['item']}/image", files={"file": ("x.png", b"not an image", "image/png")}).status_code == 400
    assert world["customer"].post(f"/menus/{world['item']}/image", files={"file": ("p.png", PNG, "image/png")}).status_code == 403
    assert world["staff"].post(f"/menus/{world['item']}/image", files={"file": ("p.png", PNG, "image/png")}).status_code == 200


# ---------------------------------------------------------------- the bell
def test_in_app_notifications(client, login):
    client.post("/api/v1/auth/register", json={"email": "feature.bell@example.com", "password": "password123",
                                               "name": "B", "sur_name": "L", "contact_number": "0861110006"})
    customer = login("feature.bell@example.com")
    assert customer.get("/notifications").json() == {"unread": 0, "items": []}
    assert client.get("/api/v1/notifications").status_code == 401

    owner_before = world["owner"].get("/notifications").json()["unread"]
    order = customer.post("/orders/", json={"restaurant_id": world["restaurant"], "items": [{"menu_item_id": world["item"], "quantity": 1}]}).json()
    customer.post("/payments/", json={"order_id": order["id"], "provider_name": "cash_delivery"})

    # the owner's bell rings for the new order even though no SMS / email provider is configured
    owner_inbox = world["owner"].get("/notifications").json()
    assert owner_inbox["unread"] > owner_before
    newest = owner_inbox["items"][0]
    assert "New order" in newest["title"] and order["id"][:8].upper() in newest["title"] + newest["message"]
    assert newest["link"] == "/restaurant/orders"

    world["owner"].post(f"/orders/{order['id']}/accept")
    mine = customer.get("/notifications").json()
    assert mine["unread"] == 1 and "accepted" in mine["items"][0]["message"]

    assert customer.post("/notifications/read").json() == {"unread": 0}
    after = customer.get("/notifications").json()
    assert after["unread"] == 0 and len(after["items"]) == 1  # marked read, still listed

    # a password reset link is never kept in the inbox
    client.post("/api/v1/auth/forgot-password", json={"email": "feature.bell@example.com"})
    assert all("reset" not in (item["link"] or "") for item in customer.get("/notifications").json()["items"])


# ---------------------------------------------------------------- legal pages data
def test_site_details_for_legal_pages(client, admin, monkeypatch):
    assert client.get("/api/v1/site").json()["business_name"] is None
    assert admin.get("/admin/system").json()["legal_contact_set"] is False

    monkeypatch.setattr(settings, "BUSINESS_NAME", "Kasi Eats (Pty) Ltd")
    monkeypatch.setattr(settings, "SUPPORT_EMAIL", "help@example.co.za")
    site = client.get("/api/v1/site").json()
    assert (site["business_name"], site["support_email"]) == ("Kasi Eats (Pty) Ltd", "help@example.co.za")
    assert admin.get("/admin/system").json()["legal_contact_set"] is True


def test_hours_read_as_people_say_them():
    clock = restaurant_info.clock
    assert [clock(t) for t in ("08:00", "12:00", "00:30", "22:00", "23:59")] == ["8:00 AM", "12:00 PM", "12:30 AM", "10:00 PM", "11:59 PM"]
    assert clock(None) == "" and clock("nonsense") == "nonsense"
