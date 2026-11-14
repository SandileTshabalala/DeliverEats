"""
Address lookups through OpenStreetMap's Nominatim: its usage policy (1 request
a second for the whole app, real contact details, cache results) and what
happens when it is busy or down (addresses still save; orders never depend on it).
"""
import pytest
import requests

from app.core.config import settings
from app.core.redis import redis_client
from app.services import geocoding_service as geo

SOWETO = (-26.24851, 27.85402)
PLACE = {"display_name": "Vilakazi St, Orlando West, Soweto", "address": {"suburb": "Orlando West", "city": "Johannesburg"}}


class FakeNominatim:
    def __init__(self, answer=PLACE, fail=False):
        self.answer, self.fail, self.calls = answer, fail, []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.fail:
            raise requests.Timeout("too slow")
        answer = self.answer

        class Response:
            def raise_for_status(self):
                pass

            def json(self):
                return answer
        return Response()


@pytest.fixture(autouse=True)
def clean():
    for key in list(redis_client.scan_iter("lvovo:geo*")):
        redis_client.delete(key)
    yield


@pytest.fixture
def nominatim(monkeypatch):
    fake = FakeNominatim()
    monkeypatch.setattr(geo, "_http_get", fake)
    return fake


@pytest.fixture(scope="module")
def customer(client, login):
    client.post("/api/v1/auth/register", json={"email": "geo.customer@example.com", "password": "password123",
                                               "name": "Lerato", "sur_name": "G", "contact_number": "0871110001"})
    return login("geo.customer@example.com")


def test_requests_identify_the_app_with_contact_details(nominatim, monkeypatch):
    monkeypatch.setattr(settings, "GEOCODER_CONTACT_EMAIL", "maps@example.com")
    geo.reverse_geocode(*SOWETO)
    url, kwargs = nominatim.calls[0]
    assert url == "https://nominatim.openstreetmap.org/reverse"
    assert kwargs["headers"]["User-Agent"] == "DeliverEats/1.0 (maps@example.com)"
    assert kwargs["timeout"] <= 5


def test_contact_falls_back_to_the_support_email(monkeypatch):
    from app.services import business
    monkeypatch.setattr(settings, "GEOCODER_CONTACT_EMAIL", None)
    monkeypatch.setattr(business, "current", lambda db=None: {"support_email": "help@example.com"})
    assert geo._user_agent() == "DeliverEats/1.0 (help@example.com)"


def test_street_names_are_kept_and_shared_by_nearby_points(nominatim):
    assert geo.reverse_geocode(*SOWETO)["display_name"] == PLACE["display_name"]
    geo.reverse_geocode(SOWETO[0] + 0.00002, SOWETO[1] - 0.00002)   # 2-3 m away
    assert len(nominatim.calls) == 1
    geo.reverse_geocode(SOWETO[0] + 0.001, SOWETO[1])                # ~110 m away: asked again
    assert len(nominatim.calls) == 2
    assert redis_client.ttl(geo.reverse_key(*SOWETO)) > 29 * 24 * 3600


def test_search_is_cached_limited_to_the_country_and_ignores_tiny_queries(nominatim):
    nominatim.answer = [{"display_name": "Orlando West"}]
    assert geo.forward_geocode("  Orlando   WEST ") == [{"display_name": "Orlando West"}]
    assert geo.forward_geocode("orlando west") == [{"display_name": "Orlando West"}]
    assert len(nominatim.calls) == 1
    assert nominatim.calls[0][1]["params"]["countrycodes"] == "za"
    assert geo.forward_geocode("ab") == [] and len(nominatim.calls) == 1


def test_at_most_one_request_a_second_for_the_whole_app(nominatim, monkeypatch):
    monkeypatch.setattr(geo, "MAX_WAIT_SECONDS", 0.3)
    geo.reverse_geocode(*SOWETO)
    # the slot is held (by this or another worker) for just over a second: the next one waits, then gives up
    with pytest.raises(geo.GeocodingUnavailable):
        geo.reverse_geocode(SOWETO[0] + 0.01, SOWETO[1])
    assert len(nominatim.calls) == 1
    redis_client.delete(geo._SLOT_KEY)        # a second later
    geo.reverse_geocode(SOWETO[0] + 0.01, SOWETO[1])
    assert len(nominatim.calls) == 2


def test_busy_search_tells_the_customer_what_to_do(customer, nominatim):
    redis_client.set(geo._SLOT_KEY, "1", px=5000)
    response = customer.get("/addresses/geocode", params={"q": "Orlando West"})
    assert response.status_code == 503 and "current location" in response.json()["detail"]


def test_address_saves_even_when_openstreetmap_is_down(customer, monkeypatch):
    monkeypatch.setattr(geo, "_http_get", FakeNominatim(fail=True))
    saved = customer.post("/addresses", json={"latitude": SOWETO[0], "longitude": SOWETO[1], "is_default": True})
    assert saved.status_code == 201, saved.text
    body = saved.json()
    assert body["formatted_address"] == "Pinned location (-26.24851, 27.85402)"
    assert body["suburb"] is None and (body["latitude"], body["longitude"]) == SOWETO

    # the "use my location" lookup answers too
    point = customer.get("/addresses/reverse-geocode", params={"lat": SOWETO[0], "lng": SOWETO[1]})
    assert point.status_code == 200 and point.json()["display_name"].startswith("Pinned location")


def test_address_gets_its_street_name_when_available(customer, nominatim):
    saved = customer.post("/addresses", json={"latitude": SOWETO[0], "longitude": SOWETO[1]}).json()
    assert (saved["formatted_address"], saved["suburb"], saved["city"]) == (PLACE["display_name"], "Orlando West", "Johannesburg")


def test_township_style_answers_fill_in_the_suburb(nominatim):
    nominatim.answer = {"display_name": "Zone 3, Meadowlands", "address": {"township": "Meadowlands", "town": "Soweto"}}
    place = geo.describe(*SOWETO)
    assert (place["suburb"], place["city"]) == ("Meadowlands", "Soweto")


def test_bad_coordinates_are_refused(customer):
    assert customer.get("/addresses/reverse-geocode", params={"lat": 123, "lng": 0}).status_code == 422
