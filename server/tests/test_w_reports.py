"""
Reports and invoices: right numbers, right people, valid files.
"""
import csv
import io
import re
import zlib
from datetime import date, timedelta

import pytest

from app.core.config import settings

world = {}


def pdf_text(content: bytes) -> str:
    """Text drawn in a PDF made by fpdf2 (its page streams are zlib-compressed)."""
    assert content.startswith(b"%PDF-"), content[:20]
    chunks = []
    for stream in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", content, re.S):
        try:
            chunks.append(zlib.decompress(stream))
        except zlib.error:
            chunks.append(stream)
    drawn = b"".join(re.findall(rb"\(((?:\\.|[^\\)])*)\)\s*Tj", b"\n".join(chunks), re.S))
    # PDF strings escape brackets and backslashes
    return re.sub(rb"\\([()\\])", rb"\1", drawn).decode("latin-1")


def csv_rows(content: bytes):
    assert content.startswith("﻿".encode("utf-8"))  # Excel-friendly
    return list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))


def get(api, path, **params):
    return api.client.get(f"/api/v1{path}", headers=api.headers, params=params)


@pytest.fixture(scope="module", autouse=True)
def setup(client, admin, login):
    ids = {}
    for key, name, email, phone in (("A", "Report Kitchen", "report.owner@example.com", "0891110001"),
                                    ("B", "Other Report Spot", "report.other@example.com", "0891110002")):
        ids[key] = admin.post("/admin/restaurants", json={
            "name": name, "address": "4 Ledger Rd, Soweto", "admin_email": email, "admin_password": "password123",
            "admin_name": "Rea", "admin_sur_name": "P", "admin_contact_number": phone,
        }).json()["id"]
    plan_id = admin.post("/admin/billing/plans", json={"name": "Report plan", "price": "299.00"}).json()["id"]
    first = admin.post(f"/admin/billing/restaurants/{ids['A']}/payments", json={"plan_id": plan_id, "note": "EFT ref 77"})
    second = admin.post(f"/admin/billing/restaurants/{ids['B']}/payments", json={"plan_id": plan_id})
    assert first.status_code == 200 and second.status_code == 200

    owner, other = login("report.owner@example.com"), login("report.other@example.com")
    item = owner.post(f"/menus/restaurant/{ids['A']}/items", json={"name": "Kota special", "price": "55.00"}).json()["id"]
    other_item = other.post(f"/menus/restaurant/{ids['B']}/items", json={"name": "Pap", "price": "20.00"}).json()["id"]
    owner.post("/manage/drivers", json={"email": "report.driver@example.com", "password": "password123", "name": "D",
                                        "sur_name": "R", "contact_number": "0891110003", "vehicle_type": "Bicycle"})
    owner.post("/manage/staff", json={"email": "report.staff@example.com", "password": "password123", "name": "S",
                                      "sur_name": "T", "contact_number": "0891110004"})
    client.post("/api/v1/auth/register", json={"email": "report.customer@example.com", "password": "password123",
                                               "name": "Zodwa", "sur_name": "Mthembu", "contact_number": "0891110005"})
    client.post("/api/v1/auth/register", json={"email": "report.nosy@example.com", "password": "password123",
                                               "name": "N", "sur_name": "Y", "contact_number": "0891110006"})
    customer, driver = login("report.customer@example.com"), login("report.driver@example.com")

    def order(restaurant, menu_item, quantity, deliver=True):
        placed = customer.post("/orders/", json={"restaurant_id": ids[restaurant], "items": [{"menu_item_id": menu_item, "quantity": quantity}]}).json()
        customer.post("/payments/", json={"order_id": placed["id"], "provider_name": "cash_delivery"})
        if deliver:
            owner.post(f"/orders/{placed['id']}/accept")
            owner.post(f"/orders/{placed['id']}/status", params={"status": "ready"})
            driver.post(f"/drivers/orders/{placed['id']}/status", params={"status": "picked_up"})
            assert driver.post(f"/drivers/orders/{placed['id']}/status", params={"status": "delivered"}).status_code == 200
        return placed["id"]

    world.update(
        ids=ids, owner=owner, other=other, customer=customer, staff=login("report.staff@example.com"),
        nosy=login("report.nosy@example.com"),
        delivered=[order("A", item, 2), order("A", item, 1)],
        open_order=order("A", item, 3, deliver=False),
        other_order=customer.post("/orders/", json={"restaurant_id": ids["B"], "items": [{"menu_item_id": other_item, "quantity": 1}]}).json()["id"],
    )


# ---------------------------------------------------------------- restaurant sales
def test_sales_csv_lists_only_this_restaurants_orders():
    response = get(world["owner"], "/manage/reports/sales.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"].startswith('attachment; filename="orders-report-kitchen-')
    rows = csv_rows(response.content)
    assert rows[0][:3] == ["Date", "Time", "Order no."]
    refs = {row[2] for row in rows[1:]}
    assert refs == {o[:8].upper() for o in world["delivered"] + [world["open_order"]]}
    assert world["other_order"][:8].upper() not in refs  # another restaurant's order never appears
    by_ref = {row[2]: row for row in rows[1:]}
    first = by_ref[world["delivered"][0][:8].upper()]
    assert first[3] == "delivered" and first[4] == "Zodwa Mthembu" and first[5] == "2 x Kota special"
    assert (first[6], first[8], first[9]) == ("110.00", "110.00", "Cash on Delivery")


def test_sales_pdf_counts_delivered_orders():
    response = get(world["owner"], "/manage/reports/sales.pdf")
    assert response.status_code == 200 and response.headers["content-type"] == "application/pdf"
    text = pdf_text(response.content)
    assert "Sales report" in text and "Report Kitchen" in text
    assert "R 165.00" in text          # 110 + 55 delivered; the open order is not a sale
    assert "Kota special" in text and "Cash on Delivery" in text


def test_staff_cannot_download_sales_or_plan_invoices():
    assert get(world["staff"], "/manage/reports/sales.csv").status_code == 403
    assert get(world["staff"], "/manage/reports/sales.pdf").status_code == 403


def test_period_is_checked():
    today = date.today()
    assert get(world["owner"], "/manage/reports/sales.csv", **{"from": today, "to": today - timedelta(days=1)}).status_code == 400
    assert get(world["owner"], "/manage/reports/sales.csv", **{"from": today - timedelta(days=400), "to": today}).status_code == 400
    old = get(world["owner"], "/manage/reports/sales.csv", **{"from": today - timedelta(days=60), "to": today - timedelta(days=40)})
    assert old.status_code == 200 and len(csv_rows(old.content)) == 1  # headings only: nothing in that period


# ---------------------------------------------------------------- invoices
def test_order_invoice_for_restaurant_and_customer():
    order_id = world["delivered"][0]
    for who in ("owner", "staff"):
        response = get(world[who], f"/manage/orders/{order_id}/invoice.pdf")
        assert response.status_code == 200
        text = pdf_text(response.content)
        assert "Invoice" in text and "Tax Invoice" not in text
        assert "Report Kitchen" in text and "Zodwa Mthembu" in text and order_id[:8].upper() in text
        assert "R 110.00" in text

    assert get(world["other"], f"/manage/orders/{order_id}/invoice.pdf").status_code == 404   # another restaurant
    mine = get(world["customer"], f"/orders/{order_id}/invoice.pdf")
    assert mine.status_code == 200 and mine.headers["content-disposition"].endswith(f'invoice-{order_id[:8].upper()}.pdf"')
    assert get(world["nosy"], f"/orders/{order_id}/invoice.pdf").status_code == 404           # someone else's order
    assert get(world["customer"], f"/orders/{world['open_order']}/invoice.pdf").status_code == 409  # not paid or delivered yet


def test_vat_registered_restaurant_issues_tax_invoices():
    owner = world["owner"]
    assert owner.patch("/manage/restaurant", json={"vat_number": "12345"}).status_code == 422
    assert owner.patch("/manage/restaurant", json={"vat_number": "4123456789"}).json()["vat_number"] == "4123456789"
    text = pdf_text(get(owner, f"/manage/orders/{world['delivered'][0]}/invoice.pdf").content)
    assert "Tax Invoice" in text and "VAT no. 4123456789" in text
    assert "R 14.35" in text  # 15/115 of R 110.00
    owner.patch("/manage/restaurant", json={"vat_number": None})


def test_subscription_invoices_are_numbered_and_private(db):
    from app.models.subscription import SubscriptionPayment
    payments = {p.restaurant_id: p for p in db.query(SubscriptionPayment).filter(
        SubscriptionPayment.restaurant_id.in_(world["ids"].values())).all()}
    a, b = payments[world["ids"]["A"]], payments[world["ids"]["B"]]
    assert a.invoice_number and b.invoice_number == a.invoice_number + 1  # one after the other, never reused

    history = world["owner"].get("/manage/billing/payments").json()
    assert history[0]["invoice_number"] == a.invoice_number

    response = get(world["owner"], f"/manage/invoices/{a.id}.pdf")
    assert response.status_code == 200
    assert response.headers["content-disposition"] == f'attachment; filename="INV-{a.invoice_number:05d}.pdf"'
    text = pdf_text(response.content)
    assert f"INV-{a.invoice_number:05d}" in text and "Report Kitchen" in text
    assert "Report plan plan, billed per month" in text and "R 299.00" in text and "EFT / cash" in text

    assert get(world["owner"], f"/manage/invoices/{b.id}.pdf").status_code == 404   # another restaurant's invoice
    assert get(world["staff"], f"/manage/invoices/{a.id}.pdf").status_code == 403   # staff: no billing
    assert get(world["owner"], f"/admin/invoices/{a.id}.pdf").status_code == 403    # admin route


def test_platform_vat_turns_subscription_invoices_into_tax_invoices(admin, db, monkeypatch):
    from app.models.subscription import SubscriptionPayment
    payment = db.query(SubscriptionPayment).filter(SubscriptionPayment.restaurant_id == world["ids"]["A"]).first()
    monkeypatch.setattr(settings, "BUSINESS_NAME", "Kasi Eats (Pty) Ltd")
    monkeypatch.setattr(settings, "BUSINESS_VAT_NUMBER", "4999999999")
    text = pdf_text(get(admin, f"/admin/invoices/{payment.id}.pdf").content)
    assert "Tax Invoice" in text and "Kasi Eats (Pty) Ltd" in text and "VAT no. 4999999999" in text
    assert "R 39.00" in text  # 15/115 of R 299.00


# ---------------------------------------------------------------- platform owner
def test_admin_income_reports(admin):
    listed = get(admin, "/admin/reports/subscription-payments").json()
    mine = [p for p in listed["payments"] if p["restaurant_name"] in ("Report Kitchen", "Other Report Spot")]
    assert len(mine) == 2 and all(p["invoice_number"].startswith("INV-") for p in mine)

    rows = csv_rows(get(admin, "/admin/reports/subscriptions.csv").content)
    assert rows[0] == ["Date", "Invoice no.", "Restaurant", "Plan", "Paid with", "Reference", "Amount (R)"]
    report_rows = [r for r in rows[1:] if r[2] == "Report Kitchen"]
    assert report_rows[0][3:] == ["Report plan", "EFT / cash", "EFT ref 77", "299.00"]
    assert sum(float(r[6]) for r in rows[1:]) == pytest.approx(float(listed["total"]))

    text = pdf_text(get(admin, "/admin/reports/income.pdf").content)
    assert "Subscription income" in text and "Report Kitchen" in text and "Other Report Spot" in text


def test_admin_restaurants_csv_has_activity_but_not_takings(admin):
    rows = csv_rows(get(admin, "/admin/reports/restaurants.csv").content)
    row = next(r for r in rows[1:] if r[0] == "Report Kitchen")
    heading = rows[0]
    assert row[heading.index("Owner phone")] == "0891110001"
    assert row[heading.index("Plan")] == "Report plan" and row[heading.index("Subscription")] == "active"
    assert row[heading.index("Delivered")] == "2"
    assert row[heading.index("Subscription paid (R)")] == "299.00"
    assert not any("Sales" in h for h in heading)  # the platform does not report restaurants' takings


def test_only_the_admin_gets_platform_reports():
    for path in ("/admin/reports/income.pdf", "/admin/reports/subscriptions.csv", "/admin/reports/restaurants.csv",
                 "/admin/reports/subscription-payments"):
        assert get(world["owner"], path).status_code == 403


def test_names_outside_latin1_do_not_break_a_pdf(client, login):
    owner = world["owner"]
    owner.patch("/manage/restaurant", json={"name": "Report Kitchen ★ 日本"})
    response = get(owner, "/manage/reports/sales.pdf")
    assert response.status_code == 200 and response.content.startswith(b"%PDF-")
    owner.patch("/manage/restaurant", json={"name": "Report Kitchen"})
