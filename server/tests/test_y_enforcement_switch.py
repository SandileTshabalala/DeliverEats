"""
The subscription switch lives in Admin > Subscriptions, not only in the server settings:
  * the admin sees whether it is on and which restaurants would be hidden
  * switching it off opens unpaid restaurants at once; switching it on hides them again
  * only the platform admin may change it
"""
import pytest


world = {}


@pytest.fixture(scope="module", autouse=True)
def setup(client, admin, login):
    unpaid = admin.post("/admin/restaurants", json={
        "name": "Unpaid Kitchen", "address": "1 Owing Rd", "admin_email": "unpaid.owner@example.com",
        "admin_password": "password123", "admin_name": "Sizwe", "admin_sur_name": "U", "admin_contact_number": "0895550001",
    }).json()["id"]
    item = login("unpaid.owner@example.com").post(f"/menus/restaurant/{unpaid}/items", json={"name": "Vetkoek", "price": "12.00"}).json()["id"]
    client.post("/api/v1/auth/register", json={"email": "switch.customer@example.com", "password": "password123",
                                               "name": "Ayanda", "sur_name": "S", "contact_number": "0895550002"})
    world.update(unpaid=unpaid, item=item, owner=login("unpaid.owner@example.com"), customer=login("switch.customer@example.com"))
    yield
    admin.put("/admin/billing/enforcement", json={"enforced": True})   # leave it as the other tests expect


def listed(client):
    return {r["id"] for r in client.get("/api/v1/restaurant/").json()}


def order(api):
    return api.post("/orders/", json={"restaurant_id": world["unpaid"], "items": [{"menu_item_id": world["item"], "quantity": 1}]})


def test_admin_sees_the_switch_and_who_would_close(admin):
    state = admin.get("/admin/billing/enforcement").json()
    assert state["enforced"] is True
    assert "Unpaid Kitchen" in state["would_close"]


def test_switching_off_opens_unpaid_restaurants_at_once(admin, client):
    assert world["unpaid"] not in listed(client)
    assert order(world["customer"]).status_code == 409

    off = admin.put("/admin/billing/enforcement", json={"enforced": False})
    assert off.status_code == 200 and off.json()["enforced"] is False
    assert world["unpaid"] in listed(client)                      # the cached list was refreshed
    assert order(world["customer"]).status_code == 200
    assert admin.get("/admin/stats").json()["subscriptions_enforced"] is False
    assert admin.get("/admin/system").json()["subscriptions"]["enforced"] is False
    assert world["owner"].get("/manage/billing").json()["subscription"]["enforced"] is False

    assert admin.put("/admin/billing/enforcement", json={"enforced": True}).json()["enforced"] is True
    assert world["unpaid"] not in listed(client)
    assert order(world["customer"]).status_code == 409


def test_only_the_platform_admin_may_flip_it(admin):
    assert world["owner"].put("/admin/billing/enforcement", json={"enforced": False}).status_code == 403
    assert world["customer"].get("/admin/billing/enforcement").status_code == 403
    assert admin.get("/admin/billing/enforcement").json()["enforced"] is True
