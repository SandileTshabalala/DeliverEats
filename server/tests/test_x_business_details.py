"""The platform owner sets the business details (incl. VAT number) in the app."""
import re
import zlib

import pytest

from app.core.config import settings


def pdf_text(content: bytes) -> str:
    chunks = []
    for stream in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", content, re.S):
        try:
            chunks.append(zlib.decompress(stream))
        except zlib.error:
            chunks.append(stream)
    drawn = b"".join(re.findall(rb"\(((?:\\.|[^\\)])*)\)\s*Tj", b"\n".join(chunks), re.S))
    return re.sub(rb"\\([()\\])", rb"\1", drawn).decode("latin-1")


@pytest.fixture(autouse=True)
def clean(admin):
    yield
    admin.put("/admin/business", json={k: "" for k in ("business_name", "business_address", "support_email", "support_phone", "vat_number")})


def test_owner_sets_details_and_they_appear_everywhere(client, admin, db):
    from app.models.subscription import SubscriptionPayment
    saved = admin.put("/admin/business", json={
        "business_name": "Kasi Eats (Pty) Ltd", "business_address": "12 Vilakazi St, Soweto",
        "support_email": "Help@KasiEats.co.za", "support_phone": "011 555 0123", "vat_number": "4123456789",
    })
    assert saved.status_code == 200, saved.text
    assert saved.json()["support_email"] == "Help@kasieats.co.za"  # domain normalised
    assert admin.get("/admin/business").json()["vat_number"] == "4123456789"

    site = client.get("/api/v1/site").json()
    assert site["business_name"] == "Kasi Eats (Pty) Ltd" and site["support_phone"] == "011 555 0123"
    assert "vat_number" not in site  # not needed publicly
    assert admin.get("/admin/system").json()["legal_contact_set"] is True

    payment = db.query(SubscriptionPayment).filter(SubscriptionPayment.status == "completed").first()
    text = pdf_text(admin.client.get(f"/api/v1/admin/invoices/{payment.id}.pdf", headers=admin.headers).content)
    assert "Tax Invoice" in text and "VAT no. 4123456789" in text and "Kasi Eats (Pty) Ltd" in text

    # clearing the VAT number turns them back into plain invoices
    admin.put("/admin/business", json={"vat_number": ""})
    text = pdf_text(admin.client.get(f"/api/v1/admin/invoices/{payment.id}.pdf", headers=admin.headers).content)
    assert "Tax Invoice" not in text and "VAT no." not in text and "Kasi Eats (Pty) Ltd" in text


def test_values_are_checked(admin):
    assert admin.put("/admin/business", json={"vat_number": "12345"}).status_code == 422
    assert admin.put("/admin/business", json={"support_email": "not-an-email"}).status_code == 422
    assert admin.put("/admin/business", json={"surprise": "x"}).status_code == 422


def test_env_file_still_applies_to_empty_fields(admin, monkeypatch):
    monkeypatch.setattr(settings, "BUSINESS_NAME", "From The Env File")
    assert admin.get("/admin/business").json()["business_name"] == "From The Env File"
    admin.put("/admin/business", json={"business_name": "Saved In The App"})
    assert admin.get("/admin/business").json()["business_name"] == "Saved In The App"  # the app wins


def test_only_the_platform_owner(client, login):
    client.post("/api/v1/auth/register", json={"email": "biz.customer@example.com", "password": "password123",
                                               "name": "C", "sur_name": "U", "contact_number": "0801110001"})
    customer = login("biz.customer@example.com")
    assert customer.get("/admin/business").status_code == 403
    assert customer.put("/admin/business", json={"vat_number": "4123456789"}).status_code == 403
