"""
A driver's online/offline switch is their own choice. Being on a delivery makes
them busy, but never flips the switch, and the switch never refuses to work.
"""
import pytest

world = {}


@pytest.fixture(scope="module", autouse=True)
def setup(client, admin, login):
    restaurant_id = admin.post("/admin/restaurants", json={
        "name": "Shift Kitchen", "address": "9 Shift Rd", "admin_email": "shift.owner@example.com",
        "admin_password": "password123", "admin_name": "O", "admin_sur_name": "W", "admin_contact_number": "0851110001",
    }).json()["id"]
    plan_id = admin.post("/admin/billing/plans", json={"name": "Shift plan", "price": "100.00"}).json()["id"]
    admin.post(f"/admin/billing/restaurants/{restaurant_id}/payments", json={"plan_id": plan_id})
    owner = login("shift.owner@example.com")
    item = owner.post(f"/menus/restaurant/{restaurant_id}/items", json={"name": "Vetkoek", "price": "20.00"}).json()["id"]
    owner.post("/manage/drivers", json={"email": "shift.driver@example.com", "password": "password123", "name": "Dumi",
                                        "sur_name": "S", "contact_number": "0851110002", "vehicle_type": "bike"})
    client.post("/api/v1/auth/register", json={"email": "shift.customer@example.com", "password": "password123",
                                               "name": "C", "sur_name": "S", "contact_number": "0851110003"})
    world.update(restaurant=restaurant_id, item=item, owner=owner,
                 driver=login("shift.driver@example.com"), customer=login("shift.customer@example.com"))


def new_accepted_order():
    customer, owner = world["customer"], world["owner"]
    order = customer.post("/orders/", json={"restaurant_id": world["restaurant"], "items": [{"menu_item_id": world["item"], "quantity": 1}]}).json()
    customer.post("/payments/", json={"order_id": order["id"], "provider_name": "cash_delivery"})
    accepted = owner.post(f"/orders/{order['id']}/accept")
    assert accepted.status_code == 200, accepted.text
    return accepted.json()


def switch(online: bool):
    return world["driver"].post("/drivers/availability", params={"available": online})


def is_online():
    return world["driver"].get("/drivers/profile").json()["is_available"]


def my_jobs():
    return [job["id"] for job in world["driver"].get("/orders/driver/jobs").json()]


def deliver(order_id):
    owner, driver = world["owner"], world["driver"]
    owner.post(f"/orders/{order_id}/status", params={"status": "ready"})
    assert driver.post(f"/drivers/orders/{order_id}/status", params={"status": "picked_up"}).status_code == 200
    assert driver.post(f"/drivers/orders/{order_id}/status", params={"status": "delivered"}).status_code == 200


def status_of(order_id):
    return next(o for o in world["owner"].get("/restaurant/orders").json() if o["id"] == order_id)


def test_getting_a_delivery_keeps_the_driver_online():
    assert is_online() is True  # new drivers start online
    first = new_accepted_order()
    assert first["driver_id"] == world["driver"].user["id"] and first["status"] == "preparing"
    assert is_online() is True  # used to flip to "offline" here
    world["first"] = first["id"]


def test_a_busy_driver_is_not_given_a_second_delivery():
    second = new_accepted_order()
    assert second["driver_id"] is None and second["status"] == "waiting_for_driver"
    assert my_jobs() == [world["first"]]
    world["second"] = second["id"]


def test_the_switch_always_works_even_during_a_delivery():
    off = switch(False)
    assert off.status_code == 200 and off.json() == {"user_id": world["driver"].user["id"], "is_available": False, "on_delivery": True}
    on = switch(True)  # used to answer 409 "Finish your current delivery..."
    assert on.status_code == 200 and on.json()["is_available"] is True and on.json()["on_delivery"] is True
    # going online while busy does not grab the waiting order: one delivery at a time
    assert my_jobs() == [world["first"]]


def test_finishing_a_delivery_hands_over_the_waiting_order():
    deliver(world["first"])
    assert my_jobs() == [world["second"]]
    assert status_of(world["second"])["driver_id"] == world["driver"].user["id"]
    assert is_online() is True


def test_an_offline_driver_gets_no_new_work_until_they_go_online():
    assert switch(False).status_code == 200  # mid-delivery: finish this one, then stop
    deliver(world["second"])
    assert my_jobs() == [] and is_online() is False

    third = new_accepted_order()
    assert third["status"] == "waiting_for_driver" and my_jobs() == []

    assert switch(True).json() == {"user_id": world["driver"].user["id"], "is_available": True, "on_delivery": True}
    assert my_jobs() == [third["id"]]  # going online picked up the waiting order
    deliver(third["id"])


def test_a_removed_driver_is_never_assigned(login):
    owner = world["owner"]
    owner.delete(f"/manage/drivers/{world['driver'].user['id']}")
    orphan = new_accepted_order()
    assert orphan["driver_id"] is None and orphan["status"] == "waiting_for_driver"
