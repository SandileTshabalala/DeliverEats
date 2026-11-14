"""
Live tracking over WebSockets: the driver's phone sends its position and only
the customer of the order that driver is carrying receives it.
"""
import json
import threading

import pytest
from starlette.websockets import WebSocketDisconnect

world = {}


def token_of(api):
    return api.headers["Authorization"].split(" ", 1)[1]


def receive(ws, seconds=10):
    """receive_text() with a time limit, so a broken relay fails instead of hanging."""
    box = {}

    def run():
        try:
            box["text"] = ws.receive_text()
        except Exception as exc:  # noqa: BLE001
            box["error"] = exc

    reader = threading.Thread(target=run, daemon=True)
    reader.start()
    reader.join(seconds)
    if "error" in box:
        raise box["error"]
    assert "text" in box, "nothing received in time"
    return json.loads(box["text"])


@pytest.fixture(scope="module", autouse=True)
def setup(client, admin, login):
    restaurant_id = admin.post("/admin/restaurants", json={
        "name": "Track Kitchen", "address": "1 Track Rd", "admin_email": "track.owner@example.com",
        "admin_password": "password123", "admin_name": "T", "admin_sur_name": "O", "admin_contact_number": "0871110001",
    }).json()["id"]
    plan_id = admin.post("/admin/billing/plans", json={"name": "Track plan", "price": "100.00"}).json()["id"]
    admin.post(f"/admin/billing/restaurants/{restaurant_id}/payments", json={"plan_id": plan_id})
    owner = login("track.owner@example.com")
    item = owner.post(f"/menus/restaurant/{restaurant_id}/items", json={"name": "Chips", "price": "25.00"}).json()["id"]
    owner.post("/manage/drivers", json={"email": "track.driver@example.com", "password": "password123", "name": "Lwazi",
                                        "sur_name": "D", "contact_number": "0871110002", "vehicle_type": "Motorbike"})
    for email in ("track.customer@example.com", "track.stranger@example.com"):
        client.post("/api/v1/auth/register", json={"email": email, "password": "password123",
                                                   "name": "C", "sur_name": "T", "contact_number": "0871110003"})
    customer, driver = login("track.customer@example.com"), login("track.driver@example.com")

    order = customer.post("/orders/", json={"restaurant_id": restaurant_id, "items": [{"menu_item_id": item, "quantity": 1}]}).json()
    customer.post("/payments/", json={"order_id": order["id"], "provider_name": "cash_delivery"})
    assert owner.post(f"/orders/{order['id']}/accept").json()["driver_id"] == driver.user["id"]
    owner.post(f"/orders/{order['id']}/status", params={"status": "ready"})
    driver.post(f"/drivers/orders/{order['id']}/status", params={"status": "picked_up"})
    world.update(order=order["id"], customer=customer, driver=driver, stranger=login("track.stranger@example.com"))


def test_customer_follows_their_driver(client):
    driver_id = world["driver"].user["id"]
    with client.websocket_connect(f"/api/v1/ws/orders/order/{world['order']}?token={token_of(world['customer'])}") as follow:
        with client.websocket_connect(f"/api/v1/ws/orders/driver/{driver_id}?token={token_of(world['driver'])}") as share:
            share.send_text(json.dumps({"lat": -26.24, "lng": 27.85, "ts": 1763100000000}))
            first = receive(follow)
            assert (first["driver_id"], first["lat"], first["lng"]) == (driver_id, -26.24, 27.85)

            share.send_text("not json at all")                              # ignored, connection stays open
            share.send_text(json.dumps({"lat": 999, "lng": 0, "ts": 1}))     # impossible position: ignored
            share.send_text(json.dumps({"lat": -26.25, "lng": 27.86, "ts": 1763100010000}))
            # The first fix can arrive twice (as "last known" and live) when both
            # sockets open at the same moment: skip repeats, never the order of fixes
            second = receive(follow)
            while second["lat"] == -26.24:
                second = receive(follow)
            assert (second["lat"], second["lng"]) == (-26.25, 27.86)


def test_last_known_position_is_sent_on_connect(client):
    with client.websocket_connect(f"/api/v1/ws/orders/order/{world['order']}?token={token_of(world['customer'])}") as follow:
        assert receive(follow)["lat"] == -26.25


def test_others_cannot_track_or_pretend_to_be_the_driver(client):
    # someone else's order
    with client.websocket_connect(f"/api/v1/ws/orders/order/{world['order']}?token={token_of(world['stranger'])}") as follow:
        assert receive(follow) == {"type": "tracking_unavailable"}

    # no token
    with client.websocket_connect(f"/api/v1/ws/orders/order/{world['order']}") as follow:
        assert receive(follow)["type"] == "auth_error"

    # a customer sending positions as if they were the driver
    driver_id = world["driver"].user["id"]
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/v1/ws/orders/driver/{driver_id}?token={token_of(world['customer'])}") as share:
            share.send_text(json.dumps({"lat": 0, "lng": 0, "ts": 0}))
            share.receive_text()


def test_tracking_stops_once_delivered(client):
    world["driver"].post(f"/drivers/orders/{world['order']}/status", params={"status": "delivered"})
    with client.websocket_connect(f"/api/v1/ws/orders/order/{world['order']}?token={token_of(world['customer'])}") as follow:
        assert receive(follow) == {"type": "tracking_unavailable"}


def test_driver_position_is_saved_for_nearest_driver_matching(db):
    from app.models.driver import Driver
    db.expire_all()
    driver = db.query(Driver).filter(Driver.id == world["driver"].user["id"]).first()
    assert (driver.latitude, driver.longitude) == (-26.24, 27.85)  # first fix saved (later ones within 15 s are not)
