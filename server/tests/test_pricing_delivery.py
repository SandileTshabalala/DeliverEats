"""
Delivery fees are set by each restaurant: base fee, optional per-km charge,
optional free delivery above an order amount, optional maximum distance.
"""
from decimal import Decimal

import pytest

SHOP = (-26.2485, 27.8540)  # Vilakazi St, Soweto
# 0.02 degrees of latitude north = 2.22 km in a straight line, ~2.9 km by road (x1.3)
CUSTOMER_NEAR = (SHOP[0] + 0.02, SHOP[1])
world = {}


@pytest.fixture(scope="module", autouse=True)
def setup(client, admin, login, db):
    from app.models.user_address import UserAddress

    restaurant_id = admin.post("/admin/restaurants", json={
        "name": "Fee Kitchen", "address": "Vilakazi St", "admin_email": "fee.owner@example.com",
        "admin_password": "password123", "admin_name": "Zanele", "admin_sur_name": "F", "admin_contact_number": "0831110001",
    }).json()["id"]
    plan_id = admin.post("/admin/billing/plans", json={"name": "Fee plan", "price": "100.00"}).json()["id"]
    admin.post(f"/admin/billing/restaurants/{restaurant_id}/payments", json={"plan_id": plan_id})

    owner = login("fee.owner@example.com")
    item_id = owner.post(f"/menus/restaurant/{restaurant_id}/items", json={"name": "Plate", "price": "50.00"}).json()["id"]

    client.post("/api/v1/auth/register", json={
        "email": "fee.customer@example.com", "password": "password123", "name": "Buhle", "sur_name": "C",
        "contact_number": "0831110002",
    })
    customer = login("fee.customer@example.com")
    address = UserAddress(user_id=customer.user["id"], latitude=CUSTOMER_NEAR[0], longitude=CUSTOMER_NEAR[1],
                          formatted_address="22 Near St, Soweto", is_default=True)
    db.add(address)
    db.commit()

    world.update(restaurant=restaurant_id, item=item_id, owner=owner, customer=customer, address=address.id)


def basket(quantity=2, with_address=True):
    body = {"restaurant_id": world["restaurant"], "items": [{"menu_item_id": world["item"], "quantity": quantity}]}
    if with_address:
        body["address_id"] = world["address"]
    return body


def quote(**kw):
    response = world["customer"].post("/orders/quote", json=basket(**kw))
    assert response.status_code == 200, response.text
    return response.json()


def save(**settings):
    return world["owner"].put("/manage/delivery-settings", json=settings)


def test_default_is_the_platform_fee():
    assert world["owner"].get("/manage/delivery-settings").json()["base_fee"] == "0"
    priced = quote()
    assert (priced["subtotal"], priced["delivery_fee"], priced["total"]) == ("100.00", "0.00", "100.00")


def test_flat_fee_is_added_to_the_order():
    assert save(base_fee="15.00").status_code == 200
    priced = quote()
    assert (priced["delivery_fee"], priced["total"]) == ("15.00", "115.00")
    assert priced["distance_km"] is None  # the shop has not set its location yet

    # the order is charged exactly what the quote said, whatever the client claims
    order = world["customer"].post("/orders/", json={**basket(), "total": "1.00"}).json()
    assert Decimal(order["delivery_fee"]) == Decimal("15.00")
    assert Decimal(order["total_amount"]) == Decimal("115.00")


def test_per_km_fee_needs_the_shop_location():
    refused = save(per_km_fee="5.00")
    assert refused.status_code == 400 and "location" in refused.json()["detail"]
    assert save(max_distance_km=5).status_code == 400
    assert save(latitude=SHOP[0]).status_code == 400  # half a location


def test_fee_grows_with_distance():
    assert save(latitude=SHOP[0], longitude=SHOP[1], per_km_fee="5.00").status_code == 200
    priced = quote()
    assert priced["distance_km"] == 2.9
    # 15 + 5 x 2.9 = 29.50, charged in whole rands
    assert (priced["delivery_fee"], priced["total"]) == ("30.00", "130.00")

    # without a delivery address the distance is unknown: base fee only
    assert quote(with_address=False)["delivery_fee"] == "15.00"


def test_free_delivery_over_an_amount():
    assert save(free_delivery_over="150.00").status_code == 200
    assert quote(quantity=2)["delivery_fee"] == "30.00"   # R100 of food
    big = quote(quantity=3)                               # R150 of food
    assert big["free_delivery"] is True
    assert (big["delivery_fee"], big["total"]) == ("0.00", "150.00")

    # sending null switches the offer off again; other settings are untouched
    cleared = save(free_delivery_over=None).json()
    assert cleared["free_delivery_over"] is None and cleared["per_km_fee"] == "5.00"
    assert quote(quantity=3)["delivery_fee"] == "30.00"


def test_orders_outside_the_delivery_area_are_refused():
    assert save(max_distance_km=2).status_code == 200
    too_far = world["customer"].post("/orders/quote", json=basket())
    assert too_far.status_code == 400 and "only delivers within 2 km" in too_far.json()["detail"]
    assert world["customer"].post("/orders/", json=basket()).status_code == 400

    assert save(max_distance_km=10).status_code == 200
    assert world["customer"].post("/orders/", json=basket()).status_code == 200


def test_only_the_owner_sets_the_fee_and_values_are_checked():
    assert world["customer"].put("/manage/delivery-settings", json={"base_fee": "0"}).status_code == 403
    assert save(base_fee="-5").status_code == 422
    assert save(latitude=123).status_code == 422
    assert save(surprise="x").status_code == 422
    assert world["owner"].get("/manage/delivery-settings").json()["base_fee"] == "15.00"


def test_restaurant_cards_show_the_delivery_fee(client):
    """Customers see what delivery costs on the restaurant list, before opening the menu."""
    save(base_fee="15.00", per_km_fee="5.00", free_delivery_over="150.00", latitude=SHOP[0], longitude=SHOP[1], max_distance_km=None)
    from app.core.redis import redis_client
    redis_client.delete("lvovo:restaurants:list")
    first = client.get("/api/v1/restaurant/").json()
    # the list is cached (it once failed to cache because prices are Decimals, so every visit hit the database)
    assert redis_client.get("lvovo:restaurants:list")
    assert client.get("/api/v1/restaurant/").json() == first
    card = next(r for r in first if r["id"] == world["restaurant"])
    assert (card["delivery_fee_from"], card["delivery_per_km"], card["free_delivery_over"]) == ("15.00", True, "150.00")
    single = client.get(f"/api/v1/restaurant/{world['restaurant']}").json()
    assert single["delivery_fee_from"] == "15.00"
