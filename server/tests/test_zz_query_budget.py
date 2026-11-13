"""
How many database round trips each common request costs.

The database is far from the app (hundreds of ms per round trip), so the number
of round trips IS the response time. These budgets stop a change from quietly
making a screen slow again. A round trip = one SQL statement, commit or rollback.

Runs last (file name) and reuses accounts created by test_real_data.py.
"""
from contextlib import contextmanager

import pytest
from sqlalchemy import event

from app.db.session import engine


@contextmanager
def count_round_trips():
    counter = {"n": 0, "sql": []}

    def on_execute(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1
        counter["sql"].append(" ".join(statement.split())[:90])

    def on_commit(conn):
        counter["n"] += 1
        counter["sql"].append("COMMIT")

    def on_rollback(conn):
        counter["n"] += 1
        counter["sql"].append("ROLLBACK")

    event.listen(engine, "before_cursor_execute", on_execute)
    event.listen(engine, "commit", on_commit)
    event.listen(engine, "rollback", on_rollback)
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", on_execute)
        event.remove(engine, "commit", on_commit)
        event.remove(engine, "rollback", on_rollback)


@pytest.fixture(scope="module")
def people(login):
    return {
        "owner": login("profile.owner@example.com"),
        "customer": login("profile.customer@example.com"),
        "driver": login("profile.driver@example.com"),
    }


# (who, method, path, most round trips allowed)
# Limits are the values measured when this was written: lower them as screens get faster.
BUDGETS = [
    ("customer", "get", "/auth/me", 0),
    ("customer", "get", "/users/me", 3),
    ("customer", "get", "/orders/my", 5),
    ("owner", "get", "/restaurant/mine", 3),
    ("owner", "get", "/restaurant/orders", 6),
    ("owner", "get", "/manage/stats", 9),
    ("owner", "get", "/manage/restaurant", 3),
    ("owner", "get", "/manage/billing", 8),
    ("driver", "get", "/orders/driver/jobs", 5),
    ("driver", "get", "/drivers/stats", 6),
]


@pytest.mark.parametrize("who, method, path, budget", BUDGETS)
def test_round_trips_per_request(people, who, method, path, budget):
    api = people[who]
    getattr(api, method)(path)  # warm caches the way a second click would find them
    with count_round_trips() as counter:
        response = getattr(api, method)(path)
    assert response.status_code == 200, response.text
    print(f"\n{who:9} {path:24} -> {counter['n']} round trips")
    assert counter["n"] <= budget, f"{path} used {counter['n']} round trips (budget {budget}):\n  " + "\n  ".join(counter["sql"])


def test_login_round_trips(client):
    with count_round_trips() as counter:
        response = client.post("/api/v1/auth/login", data={"username": "profile.customer@example.com", "password": "password123"})
    assert response.status_code == 200
    print(f"\nlogin -> {counter['n']} round trips")
    assert counter["n"] <= 7,"\n  ".join(counter["sql"])
