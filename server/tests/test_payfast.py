"""
Unit tests for the PayFast signing / ITN validation helpers.

Run from the `server` folder:  python -m pytest tests/test_payfast.py
(they only need `requests`, no database or Redis).
"""
import hashlib
from urllib.parse import urlencode

from app.services import payfast

CREDS = payfast.PayFastCredentials(
    merchant_id="10000100",
    merchant_key="46f0cd694581a",
    passphrase="jt7NOE43FZPn",
    sandbox=True,
)


def make_checkout(**overrides):
    args = dict(
        payment_id="pay-123",
        amount="149.5",
        item_name="Mama Thembi's Kitchen order #abc12345",
        item_description="2 x Kota, 1 x Chips & Russian",
        return_url="https://example.com/customer/orders?payment=success&order=o1",
        cancel_url="https://example.com/customer/orders?payment=cancelled&order=o1",
        notify_url="https://api.example.com/api/v1/payments/payfast/notify",
        name_first="Sipho",
        name_last="Nkosi",
        email_address="sipho@example.com",
        order_id="o1",
    )
    args.update(overrides)
    return payfast.build_checkout(CREDS, **args)


def test_checkout_targets_sandbox_or_live():
    url, _ = make_checkout()
    assert url == "https://sandbox.payfast.co.za/eng/process"
    live = payfast.PayFastCredentials("1", "2", sandbox=False)
    assert live.process_url == "https://www.payfast.co.za/eng/process"


def test_checkout_fields_and_amount_format():
    _, fields = make_checkout()
    assert fields["amount"] == "149.50"
    assert fields["m_payment_id"] == "pay-123"
    assert fields["custom_str1"] == "o1"
    # signature is last and empty fields are left out entirely
    assert list(fields)[-1] == "signature"
    assert "cell_number" not in fields


def test_checkout_signature_matches_manual_calculation():
    """Signature = md5 of the fields in PayFast's order, PHP-urlencoded, + passphrase."""
    _, fields = make_checkout()
    expected_string = (
        "merchant_id=10000100"
        "&merchant_key=46f0cd694581a"
        "&return_url=https%3A%2F%2Fexample.com%2Fcustomer%2Forders%3Fpayment%3Dsuccess%26order%3Do1"
        "&cancel_url=https%3A%2F%2Fexample.com%2Fcustomer%2Forders%3Fpayment%3Dcancelled%26order%3Do1"
        "&notify_url=https%3A%2F%2Fapi.example.com%2Fapi%2Fv1%2Fpayments%2Fpayfast%2Fnotify"
        "&name_first=Sipho"
        "&name_last=Nkosi"
        "&email_address=sipho%40example.com"
        "&m_payment_id=pay-123"
        "&amount=149.50"
        "&item_name=Mama+Thembi%27s+Kitchen+order+%23abc12345"
        "&item_description=2+x+Kota%2C+1+x+Chips+%26+Russian"
        "&custom_str1=o1"
        "&passphrase=jt7NOE43FZPn"
    )
    assert fields["signature"] == hashlib.md5(expected_string.encode()).hexdigest()


def test_signature_changes_when_amount_is_tampered_with():
    _, fields = make_checkout()
    tampered = dict(fields, amount="1.00")
    assert payfast.sign_checkout(tampered, CREDS.passphrase) != fields["signature"]


def _itn_pairs(passphrase=CREDS.passphrase, **overrides):
    data = [
        ("m_payment_id", "pay-123"),
        ("pf_payment_id", "1089250"),
        ("payment_status", "COMPLETE"),
        ("item_name", "Mama Thembi's Kitchen order #abc12345"),
        ("item_description", ""),  # ITNs include empty fields and they ARE signed
        ("amount_gross", "149.50"),
        ("amount_fee", "-3.44"),
        ("amount_net", "146.06"),
        ("custom_str1", "o1"),
        ("name_first", "Sipho"),
        ("email_address", "sipho@example.com"),
        ("merchant_id", "10000100"),
    ]
    data = [(k, overrides.get(k, v)) for k, v in data]
    param_string = "&".join(f"{k}={payfast._encode(v)}" for k, v in data)
    if passphrase:
        param_string += f"&passphrase={payfast._encode(passphrase)}"
    return data + [("signature", hashlib.md5(param_string.encode()).hexdigest())]


def test_itn_body_roundtrip_and_signature():
    pairs = _itn_pairs()
    parsed = payfast.parse_itn_body(urlencode(pairs).encode())
    assert parsed == pairs  # order and empty values preserved
    assert payfast.itn_signature_valid(parsed, CREDS.passphrase)


def test_itn_signature_rejects_tampering_and_wrong_passphrase():
    pairs = _itn_pairs()
    tampered = [(k, "999.00" if k == "amount_gross" else v) for k, v in pairs]
    assert not payfast.itn_signature_valid(tampered, CREDS.passphrase)
    assert not payfast.itn_signature_valid(pairs, "wrong-passphrase")
    assert not payfast.itn_signature_valid([p for p in pairs if p[0] != "signature"], CREDS.passphrase)


def test_amounts_match():
    assert payfast.amounts_match("149.50", "149.50")
    assert payfast.amounts_match(149.5, "149.50")
    assert not payfast.amounts_match("149.50", "14.95")
    assert not payfast.amounts_match("149.50", None)
    assert not payfast.amounts_match("149.50", "abc")


def test_validate_itn_runs_every_check(monkeypatch):
    pairs = _itn_pairs()
    monkeypatch.setattr(payfast, "itn_confirmed_by_payfast", lambda creds, p: True)
    monkeypatch.setattr(payfast, "payfast_ip_addresses", lambda: {"197.97.145.144"})

    ok = dict(expected_amount="149.50", remote_ip="197.97.145.144")
    assert payfast.validate_itn(CREDS, pairs, **ok) == (True, "")

    # wrong amount on our side (someone paid less than the order total)
    assert payfast.validate_itn(CREDS, pairs, expected_amount="500.00", remote_ip="197.97.145.144")[1] == "amount mismatch"
    # not sent from a PayFast address
    assert "did not come from PayFast" in payfast.validate_itn(CREDS, pairs, expected_amount="149.50", remote_ip="10.0.0.9")[1]
    # ...unless the source check is switched off (sandbox behind a tunnel)
    assert payfast.validate_itn(CREDS, pairs, expected_amount="149.50", remote_ip="10.0.0.9", check_source_ip=False)[0]
    # someone else's merchant account
    other = _itn_pairs(merchant_id="99999999")
    assert payfast.validate_itn(CREDS, other, **ok)[1] == "merchant_id mismatch"
    # PayFast does not recognise the notification
    monkeypatch.setattr(payfast, "itn_confirmed_by_payfast", lambda creds, p: False)
    assert payfast.validate_itn(CREDS, pairs, **ok)[1] == "PayFast did not confirm the notification"
