"""
Sessions:
  * one account can be signed in on several devices at once (the restaurant's tablet and phone)
  * at most MAX_SESSIONS_PER_USER: the oldest is signed out
  * after a password change or reset, older sign-ins stop working immediately,
    except the device that changed it
"""
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core import security
from app.core.config import settings
from app.models.refresh_tokens import RefreshToken

EMAIL = "sessions.user@example.com"


def register(client, email=EMAIL):
    client.post("/api/v1/auth/register", json={"email": email, "password": "password123",
                                               "name": "Sipho", "sur_name": "S", "contact_number": "0893330001"})


def sign_in(client, email=EMAIL, password="password123"):
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"], response.cookies.get("refresh_token")


def old_token(user_id, minutes_ago=10):
    """An access token signed in a while ago (on another device)."""
    issued = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return jwt.encode({"sub": user_id, "role": "customer", "type": "access", "iat": issued,
                       "exp": issued + timedelta(minutes=60), "jti": secrets.token_urlsafe(8)},
                      settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def me(client, token):
    return client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})


def refresh(client, cookie):
    client.cookies.clear()
    return client.post("/api/v1/auth/refresh-access-token", cookies={"refresh_token": cookie})


def test_two_devices_stay_signed_in(client):
    register(client)
    _, tablet = sign_in(client)
    _, phone = sign_in(client)
    assert refresh(client, tablet).status_code == 200      # the tablet was NOT signed out by the phone
    assert refresh(client, phone).status_code == 200


def test_oldest_session_ends_beyond_the_limit(client, db, monkeypatch):
    monkeypatch.setattr(security, "MAX_SESSIONS_PER_USER", 3)
    register(client, "sessions.many@example.com")
    cookies = [sign_in(client, "sessions.many@example.com")[1] for _ in range(4)]
    assert refresh(client, cookies[0]).status_code == 401  # the oldest of four
    assert refresh(client, cookies[3]).status_code == 200


def test_replayed_refresh_token_still_ends_every_session(client):
    register(client, "sessions.replay@example.com")
    _, first = sign_in(client, "sessions.replay@example.com")
    _, second = sign_in(client, "sessions.replay@example.com")
    assert refresh(client, first).status_code == 200       # rotates: `first` is now used up
    assert refresh(client, first).status_code == 401       # replay = stolen: end all sessions
    assert refresh(client, second).status_code == 401


def test_password_change_signs_out_other_devices_at_once(client):
    register(client, "sessions.change@example.com")
    token, cookie = sign_in(client, "sessions.change@example.com")
    user_id = me(client, token).json()["id"]
    other_phone = old_token(user_id)
    assert me(client, other_phone).status_code == 200

    changed = client.post("/api/v1/auth/change-password", headers={"Authorization": f"Bearer {token}"},
                          cookies={"refresh_token": cookie},
                          json={"current_password": "password123", "new_password": "brand-new-pass"})
    assert changed.status_code == 200, changed.text
    assert me(client, other_phone).status_code == 401      # straight away, not an hour later
    assert me(client, token).status_code == 200            # the device that changed it stays in
    new_token, _ = sign_in(client, "sessions.change@example.com", "brand-new-pass")
    assert me(client, new_token).status_code == 200


def test_password_reset_signs_out_every_device(client, db):
    from app.services import auth_service
    register(client, "sessions.reset@example.com")
    token, _ = sign_in(client, "sessions.reset@example.com")
    user_id = me(client, token).json()["id"]
    earlier = old_token(user_id)

    reset_token = secrets.token_urlsafe(32)
    from app.core.redis import redis_client
    redis_client.setex(auth_service._reset_key(reset_token), 600, user_id)
    assert client.post("/api/v1/auth/reset-password", json={"token": reset_token, "password": "reset-pass-1"}).status_code == 200

    assert me(client, earlier).status_code == 401
    assert db.query(RefreshToken).filter(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False).count() == 0  # noqa: E712
