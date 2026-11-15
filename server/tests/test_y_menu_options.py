"""
Menu sections and dish options:
  * a dish can have choices (spice level: pick one; extras: pick any) with prices
  * the server checks every pick and prices it; the browser never sets a price
  * each order line keeps what was picked, as it was then
  * the restaurant puts its sections in order
"""
from decimal import Decimal

import pytest

world = {}

KOTA = {
    "name": "Kota", "price": "35.00", "section": "  Kotas ",
    "options": [
        {"name": "Spice level", "min_select": 1, "max_select": 1,
         "choices": [{"name": "Mild"}, {"name": "Hot"}]},
        {"name": "Extras", "min_select": 0, "max_select": 3,
         "choices": [{"name": "Extra chips", "price": "10.00"}, {"name": "Cheese", "price": "6.50"},
                     {"name": "Russian", "price": "12.00", "available": False}]},
    ],
}


@pytest.fixture(scope="module", autouse=True)
def setup(client, admin, login):
    restaurant_id = admin.post("/admin/restaurants", json={
        "name": "Options Kitchen", "address": "1 Choice Rd", "admin_email": "options.owner@example.com",
        "admin_password": "password123", "admin_name": "Kagiso", "admin_sur_name": "O", "admin_contact_number": "0894440001",
    }).json()["id"]
    plan_id = admin.post("/admin/billing/plans", json={"name": "Options plan", "price": "150.00"}).json()["id"]
    admin.post(f"/admin/billing/restaurants/{restaurant_id}/payments", json={"plan_id": plan_id})
    owner = login("options.owner@example.com")
    kota = owner.post(f"/menus/restaurant/{restaurant_id}/items", json=KOTA)
    assert kota.status_code == 200, kota.text
    coke = owner.post(f"/menus/restaurant/{restaurant_id}/items", json={"name": "Coke", "price": "15.00", "section": "Drinks"}).json()
    client.post("/api/v1/auth/register", json={"email": "options.customer@example.com", "password": "password123",
                                               "name": "Lindi", "sur_name": "C", "contact_number": "0894440002"})
    world.update(restaurant=restaurant_id, owner=owner, kota=kota.json(), coke=coke,
                 customer=login("options.customer@example.com"))


def choice(group_name, choice_name):
    group = next(g for g in world["kota"]["options"] if g["name"] == group_name)
    return next(c["id"] for c in group["choices"] if c["name"] == choice_name)


def quote(*lines):
    return world["customer"].post("/orders/quote", json={"restaurant_id": world["restaurant"], "items": list(lines)})


def kota(*picks, quantity=1):
    return {"menu_item_id": world["kota"]["id"], "quantity": quantity, "options": list(picks)}


def test_options_are_saved_with_ids_and_shown_on_the_menu():
    kota_item = world["kota"]
    assert kota_item["section"] == "Kotas"                                  # tidied
    assert [g["name"] for g in kota_item["options"]] == ["Spice level", "Extras"]
    assert all(c["id"] for g in kota_item["options"] for c in g["choices"])
    menu = {i["name"]: i for i in world["customer"].get(f"/menus/restaurant/{world['restaurant']}").json()}
    assert menu["Kota"]["options"][1]["choices"][0]["price"] in ("10.00", 10.0, "10")
    assert menu["Coke"]["options"] == [] and menu["Coke"]["section"] == "Drinks"


def test_extras_are_priced_by_the_server():
    response = quote(kota(choice("Spice level", "Hot"), choice("Extras", "Extra chips"), choice("Extras", "Cheese"), quantity=2))
    assert response.status_code == 200, response.text
    assert Decimal(str(response.json()["subtotal"])) == Decimal("103.00")    # (35 + 10 + 6.50) x 2


def test_required_choice_must_be_made():
    response = quote(kota(choice("Extras", "Cheese")))
    assert response.status_code == 400 and "spice level" in response.json()["detail"]


def test_too_many_choices_in_a_pick_one_group():
    response = quote(kota(choice("Spice level", "Hot"), choice("Spice level", "Mild")))
    assert response.status_code == 400


def test_unknown_or_unavailable_choices_are_refused():
    assert quote(kota(choice("Spice level", "Hot"), "c-made-up")).status_code == 400
    sold_out = quote(kota(choice("Spice level", "Hot"), choice("Extras", "Russian")))
    assert sold_out.status_code == 400 and "Russian" in sold_out.json()["detail"]


def test_order_lines_keep_the_picks_and_split_by_choice():
    customer = world["customer"]
    hot, mild, chips = choice("Spice level", "Hot"), choice("Spice level", "Mild"), choice("Extras", "Extra chips")
    response = customer.post("/orders/", json={"restaurant_id": world["restaurant"], "items": [
        kota(hot, chips), kota(chips, hot), kota(mild), {"menu_item_id": world["coke"]["id"], "quantity": 1},
    ]})
    assert response.status_code == 200, response.text
    lines = response.json()["items"]
    assert len(lines) == 3                                                  # same picks merged, different picks apart
    hot_line = next(l for l in lines if l["options"] and any(o["name"] == "Hot" for o in l["options"]))
    assert hot_line["quantity"] == 2 and Decimal(str(hot_line["price"])) == Decimal("45.00")
    assert {(o["group"], o["name"]) for o in hot_line["options"]} == {("Spice level", "Hot"), ("Extras", "Extra chips")}
    coke = next(l for l in lines if l["name"] == "Coke")
    assert coke["options"] is None
    assert Decimal(str(response.json()["total_amount"])) >= Decimal("105.00")  # 90 + 35 + 15 (+ delivery)


def test_editing_options_keeps_existing_ids():
    owner, kota_item = world["owner"], world["kota"]
    groups = kota_item["options"]
    groups[0]["choices"].append({"name": "Extra hot"})
    updated = owner.patch(f"/menus/{kota_item['id']}", json={"options": groups})
    assert updated.status_code == 200, updated.text
    spice = updated.json()["options"][0]["choices"]
    assert [c["id"] for c in spice[:2]] == [c["id"] for c in kota_item["options"][0]["choices"][:2]]
    assert spice[2]["name"] == "Extra hot" and spice[2]["id"]


def test_option_rules_are_checked():
    owner = world["owner"]
    bad = {"name": "Bad", "price": "10.00", "options": [
        {"name": "Sauce", "min_select": 3, "max_select": 1, "choices": [{"name": "Tomato"}]}]}
    assert owner.post(f"/menus/restaurant/{world['restaurant']}/items", json=bad).status_code == 422
    no_choices = {"name": "Bad", "price": "10.00", "options": [{"name": "Sauce", "choices": []}]}
    assert owner.post(f"/menus/restaurant/{world['restaurant']}/items", json=no_choices).status_code == 422


def test_restaurant_orders_its_sections():
    owner = world["owner"]
    saved = owner.put("/manage/menu-sections", json={"sections": ["Drinks", " kotas", "Kotas", "", "Sides"]})
    assert saved.status_code == 200, saved.text
    assert saved.json()["menu_sections"] == ["Drinks", "kotas", "Sides"]   # tidied, no repeats
    assert owner.get("/manage/restaurant").json()["menu_sections"] == ["Drinks", "kotas", "Sides"]
    public = world["customer"].get(f"/restaurant/{world['restaurant']}").json()
    assert public["menu_sections"] == ["Drinks", "kotas", "Sides"]
