"""Smoke tests for the new Mass Missals Hub (/api/missals).

Validates: listing, full detail, individual section payloads, error
paths for invalid slugs/indexes, and unauth gating.
"""
from __future__ import annotations

import os
import sys
import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import app  # noqa: E402


def _mint_token(email: str = "philipwils13@gmail.com") -> str:
    """Seed a session token in Mongo for the admin/test user.

    Uses synchronous pymongo to avoid clashing with the TestClient's
    event loop (which holds the app's motor client).
    """
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    cli = MongoClient(mongo_url)
    db = cli["sanctus_db"]
    u = db.users.find_one({"email": email})
    if not u:
        user_id = f"pytest_user_{uuid4().hex[:8]}"
        db.users.insert_one(
            {
                "user_id": user_id,
                "email": email,
                "name": "Missals Pytest",
                "created_at": datetime.now(timezone.utc),
            }
        )
    else:
        user_id = u["user_id"]
    token = f"pytest_missals_{uuid4().hex}"
    db.user_sessions.insert_one(
        {
            "session_token": token,
            "user_id": user_id,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }
    )
    cli.close()
    return token


@pytest.fixture(scope="module")
def auth_header() -> dict:
    token = _mint_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_missals_requires_auth(client: TestClient) -> None:
    r = client.get("/api/missals")
    assert r.status_code in (401, 403)


def test_missals_index(client: TestClient, auth_header: dict) -> None:
    r = client.get("/api/missals", headers=auth_header)
    assert r.status_code == 200
    data = r.json()
    items = data["items"]
    assert len(items) == 3
    slugs = {m["slug"] for m in items}
    assert slugs == {"novus-ordo", "tlm", "ordinariate"}
    for m in items:
        assert m["section_count"] >= 10
        assert m["name"]
        assert m["accent_color"].startswith("#")


@pytest.mark.parametrize("slug", ["novus-ordo", "tlm", "ordinariate"])
def test_missal_detail(client: TestClient, auth_header: dict, slug: str) -> None:
    r = client.get(f"/api/missals/{slug}", headers=auth_header)
    assert r.status_code == 200
    d = r.json()
    assert d["slug"] == slug
    assert d["sections"], "Missal must declare sections"
    # Sections must be contiguous & indexed from 0.
    indexes = [s["index"] for s in d["sections"]]
    assert indexes == list(range(len(indexes)))
    # Latin-bearing flag should be reasonable for each missal.
    has_any_latin = any(s["has_latin"] for s in d["sections"])
    if slug != "ordinariate":
        assert has_any_latin, f"{slug} should include Latin in at least one section"


def test_missal_section_payload(client: TestClient, auth_header: dict) -> None:
    # First section of Novus Ordo should have both Latin & English.
    r = client.get("/api/missals/novus-ordo/sections/0", headers=auth_header)
    assert r.status_code == 200
    sec = r.json()
    assert sec["index"] == 0
    assert sec["english"]
    assert sec["latin"]
    assert sec["prev"] is None
    assert sec["next"] == 1


def test_missal_unknown_slug(client: TestClient, auth_header: dict) -> None:
    r = client.get("/api/missals/unknown-rite", headers=auth_header)
    assert r.status_code == 404


def test_missal_out_of_range_section(client: TestClient, auth_header: dict) -> None:
    r = client.get("/api/missals/novus-ordo/sections/9999", headers=auth_header)
    assert r.status_code == 404
