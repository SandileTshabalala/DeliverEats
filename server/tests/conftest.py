"""
Test setup: the whole API runs against a throw-away SQLite database and an
in-memory fake Redis, so the tests need no Postgres, Redis or internet.

Run from the `server` folder:  python -m pytest
(needs: pip install pytest fakeredis httpx)
"""
import os
import tempfile

_db_file = os.path.join(tempfile.mkdtemp(prefix="lvovo-test-"), "test.db")

# Must be set before anything from `app` is imported
os.environ.update({
    "ENV": "development",
    "DEBUG": "development",
    "DATABASE_URL": "sqlite:///" + _db_file.replace("\\", "/"),
    "JWT_SECRET_KEY": "test-secret-key-not-used-anywhere-real",
    "CELERY_BROKER_URL": "redis://localhost:6379/1",
    "CELERY_RESULT_BACKEND": "redis://localhost:6379/2",
    "REDIS_URL": "redis://localhost:6379/0",
    "CORS_ORIGINS": "http://localhost:5173",
    "FRONTEND_URL": "http://localhost:5173",
    "PUBLIC_API_URL": "https://api.example.test",
    "PAYFAST_MERCHANT_ID": "10000100",
    "PAYFAST_MERCHANT_KEY": "46f0cd694581a",
    "PAYFAST_PASSPHRASE": "platform-passphrase",
    "PAYFAST_SANDBOX": "true",
    "SUBSCRIPTIONS_ENFORCED": "true",
    "SUBSCRIPTION_GRACE_DAYS": "5",
    "UPLOAD_DIR": os.path.join(tempfile.mkdtemp(prefix="lvovo-uploads-"), "uploads"),
    "RATE_LIMIT_DEFAULT": "100000",
    "RATE_LIMIT_AUTH": "100000",
    "RATE_LIMIT_AUTHENTICATED": "100000",
})

import fakeredis  # noqa: E402
import fakeredis.aioredis  # noqa: E402
import pytest  # noqa: E402
import redis  # noqa: E402
import redis.asyncio  # noqa: E402

_server = fakeredis.FakeServer()


def _fake_sync(*args, **kwargs):
    return fakeredis.FakeRedis(server=_server, decode_responses=True)


def _fake_async(*args, **kwargs):
    return fakeredis.aioredis.FakeRedis(server=_server, decode_responses=True)


# Patch the Redis classes before app.core.redis builds its clients
redis.Redis = _fake_sync
redis.asyncio.Redis = _fake_async

import app.core.redis as app_redis  # noqa: E402

app_redis.Redis = _fake_async
app_redis.redis_client = _fake_sync()
app_redis.get_sync_redis = _fake_sync


async def _get_async_redis():
    return _fake_async()


app_redis.get_async_redis = _get_async_redis

from fastapi.testclient import TestClient  # noqa: E402

from app.core.roles import Role  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def db():
    session = SessionLocal()
    yield session
    session.close()


class Api:
    """A logged-in user of the API."""

    def __init__(self, client, email, password):
        response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
        assert response.status_code == 200, response.text
        self.client = client
        self.user = response.json()["user"]
        self.headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    def get(self, path, **kw):
        return self.client.get(f"/api/v1{path}", headers=self.headers, **kw)

    def post(self, path, **kw):
        return self.client.post(f"/api/v1{path}", headers=self.headers, **kw)

    def put(self, path, **kw):
        return self.client.put(f"/api/v1{path}", headers=self.headers, **kw)

    def patch(self, path, **kw):
        return self.client.patch(f"/api/v1{path}", headers=self.headers, **kw)

    def delete(self, path, **kw):
        return self.client.delete(f"/api/v1{path}", headers=self.headers, **kw)


@pytest.fixture(scope="session")
def login(client):
    return lambda email, password="password123": Api(client, email, password)


@pytest.fixture(scope="session")
def admin(client, db, login):
    if not db.query(User).filter(User.email == "boss@example.com").first():
        db.add(User(
            name="Platform", sur_name="Owner", email="boss@example.com", contact_number="0110000000",
            password_hash=hash_password("password123"), role=Role.SUPER_ADMIN, is_active=True,
        ))
        db.commit()
    return login("boss@example.com")


@pytest.fixture(autouse=True)
def _no_real_address_lookups(monkeypatch):
    """Tests never call the real OpenStreetMap service: it would look like it is down."""
    import requests
    from app.services import geocoding_service

    def offline(*args, **kwargs):
        raise requests.ConnectionError("address lookups are offline in tests")

    monkeypatch.setattr(geocoding_service, "_http_get", offline)
