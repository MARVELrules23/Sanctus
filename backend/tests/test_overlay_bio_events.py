"""Tests for the new overlay attribution / bio fields / my-events feature set
(iteration 22).

Scope:
- PUT /api/auth/me — new bio fields (denomination, tradition_path, age, show_attribution)
- PUT /api/churches/{church_id}/overlay — attribution opt-in, dedupe, replace semantics
- GET /api/churches/{church_id}/overlay
- /api/churches/nearby, /search, /saved — overlay metadata decoration
- GET /api/parish-events/me/list — per-user filtering
"""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or "http://localhost:8001"
).rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

USER_A_ID = "TEST_overlay_user_a"
USER_B_ID = "TEST_overlay_user_b"
USER_A_NAME = "TEST Anna A"
USER_B_NAME = "TEST Bob B"
USER_A_TOKEN = "TEST_overlay_token_a"
USER_B_TOKEN = "TEST_overlay_token_b"

OSM_CHURCH_ID = "osm:test123"


@pytest.fixture(scope="module")
def mongo_db():
    cli = MongoClient(MONGO_URL)
    db = cli[DB_NAME]
    yield db
    cli.close()


@pytest.fixture(scope="module", autouse=True)
def seed_users(mongo_db):
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=1)
    for uid, name, tok in [
        (USER_A_ID, USER_A_NAME, USER_A_TOKEN),
        (USER_B_ID, USER_B_NAME, USER_B_TOKEN),
    ]:
        mongo_db.users.update_one(
            {"user_id": uid},
            {"$set": {
                "user_id": uid,
                "email": f"{uid}@sanctus.test",
                "name": name,
                "picture": None,
                "created_at": now,
            }},
            upsert=True,
        )
        mongo_db.user_sessions.update_one(
            {"session_token": tok},
            {"$set": {
                "session_token": tok,
                "user_id": uid,
                "created_at": now,
                "expires_at": exp,
            }},
            upsert=True,
        )
    # clean any leftover overlay for the test osm church
    mongo_db.church_overlays.delete_many({"church_id": OSM_CHURCH_ID})
    mongo_db.community_churches.delete_many({"submitted_by": {"$in": [USER_A_ID, USER_B_ID]}})
    mongo_db.parish_events.delete_many({"organizer_user_id": {"$in": [USER_A_ID, USER_B_ID]}})
    mongo_db.user_churches.delete_many({"user_id": {"$in": [USER_A_ID, USER_B_ID]}})

    yield

    mongo_db.user_sessions.delete_many({"user_id": {"$in": [USER_A_ID, USER_B_ID]}})
    mongo_db.users.delete_many({"user_id": {"$in": [USER_A_ID, USER_B_ID]}})
    mongo_db.church_overlays.delete_many({"church_id": OSM_CHURCH_ID})
    mongo_db.community_churches.delete_many({"submitted_by": {"$in": [USER_A_ID, USER_B_ID]}})
    mongo_db.parish_events.delete_many({"organizer_user_id": {"$in": [USER_A_ID, USER_B_ID]}})
    mongo_db.user_churches.delete_many({"user_id": {"$in": [USER_A_ID, USER_B_ID]}})


def _client(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    })
    return s


@pytest.fixture(scope="module")
def client_a():
    return _client(USER_A_TOKEN)


@pytest.fixture(scope="module")
def client_b():
    return _client(USER_B_TOKEN)


# ---------------------------------------------------------------------------
# 1) PUT /api/auth/me — bio fields
# ---------------------------------------------------------------------------
class TestAuthMeBio:
    def test_set_valid_bio_fields(self, client_a):
        r = client_a.put(f"{BASE_URL}/api/auth/me", json={
            "denomination": "catholic",
            "tradition_path": "convert",
            "age": 32,
            "show_attribution": True,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["denomination"] == "catholic"
        assert d["tradition_path"] == "convert"
        assert d["age"] == 32
        assert d["show_attribution"] is True

        # GET /auth/me should reflect persistence
        g = client_a.get(f"{BASE_URL}/api/auth/me")
        assert g.status_code == 200
        gd = g.json()
        assert gd["denomination"] == "catholic"
        assert gd["tradition_path"] == "convert"
        assert gd["age"] == 32
        assert gd["show_attribution"] is True

    def test_clear_bio_with_empty_strings_and_zero_age(self, client_a):
        r = client_a.put(f"{BASE_URL}/api/auth/me", json={
            "denomination": "",
            "tradition_path": "",
            "age": 0,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["denomination"] is None
        assert d["tradition_path"] is None
        assert d["age"] is None

    def test_reject_invalid_denomination(self, client_a):
        r = client_a.put(f"{BASE_URL}/api/auth/me", json={"denomination": "buddhist"})
        assert r.status_code == 400

    def test_reject_invalid_tradition_path(self, client_a):
        r = client_a.put(f"{BASE_URL}/api/auth/me", json={"tradition_path": "lapsed"})
        assert r.status_code == 400

    def test_reject_out_of_range_age(self, client_a):
        r = client_a.put(f"{BASE_URL}/api/auth/me", json={"age": 10})
        assert r.status_code == 400
        r = client_a.put(f"{BASE_URL}/api/auth/me", json={"age": 200})
        assert r.status_code == 400

    def test_accept_orthodox_and_revert(self, client_b):
        r = client_b.put(f"{BASE_URL}/api/auth/me", json={
            "denomination": "orthodox",
            "tradition_path": "revert",
            "age": 45,
            "show_attribution": False,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["denomination"] == "orthodox"
        assert d["tradition_path"] == "revert"
        assert d["age"] == 45
        assert d["show_attribution"] is False


# ---------------------------------------------------------------------------
# 2) PUT /api/churches/{church_id}/overlay — attribution & dedupe
# ---------------------------------------------------------------------------
class TestChurchOverlay:
    def test_user_a_submits_with_show_name_true(self, client_a):
        r = client_a.put(
            f"{BASE_URL}/api/churches/{OSM_CHURCH_ID}/overlay",
            json={
                "mass_times": ["Sun 9 AM"],
                "website": "https://parish.example",
                "show_name": True,
            },
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert "Sun 9 AM" in d["mass_times"]
        assert d["website"] == "https://parish.example"
        assert d["editor_count"] == 1
        assert d["contributors"] == [USER_A_NAME]
        assert d["last_edited_by"] == USER_A_NAME

    def test_get_overlay_returns_attribution(self, client_a):
        r = client_a.get(f"{BASE_URL}/api/churches/{OSM_CHURCH_ID}/overlay")
        assert r.status_code == 200
        d = r.json()
        assert d["contributors"] == [USER_A_NAME]
        assert d["editor_count"] == 1
        assert d["last_edited_by"] == USER_A_NAME

    def test_user_b_submits_opt_out(self, client_b):
        r = client_b.put(
            f"{BASE_URL}/api/churches/{OSM_CHURCH_ID}/overlay",
            json={
                "confession_times": ["Sat 3 PM"],
                "show_name": False,
            },
        )
        assert r.status_code == 200, r.text
        d = r.json()
        # editor_count counts both users by user_id
        assert d["editor_count"] == 2
        # contributors should still only include user A (B opted out)
        assert d["contributors"] == [USER_A_NAME]
        # last_edited_by is null because the most recent editor opted out
        assert d["last_edited_by"] is None
        assert "Sat 3 PM" in d["confession_times"]

    def test_dedupes_case_insensitively(self, client_a):
        r = client_a.put(
            f"{BASE_URL}/api/churches/{OSM_CHURCH_ID}/overlay",
            json={"mass_times": ["sun 9 am", "SUN 9 AM", "Mon 8 AM"], "show_name": True},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        # Existing "Sun 9 AM" must not duplicate; "Mon 8 AM" should append once
        lc = [t.lower() for t in d["mass_times"]]
        assert lc.count("sun 9 am") == 1
        assert lc.count("mon 8 am") == 1

    def test_replace_mass_wipes_existing(self, client_a):
        r = client_a.put(
            f"{BASE_URL}/api/churches/{OSM_CHURCH_ID}/overlay",
            json={"mass_times": [], "replace_mass": True, "show_name": True},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["mass_times"] == []
        # confession_times untouched
        assert "Sat 3 PM" in d["confession_times"]

    def test_reject_bad_church_id_format(self, client_a):
        r = client_a.put(
            f"{BASE_URL}/api/churches/random_invalid_id/overlay",
            json={"mass_times": ["Sun 9 AM"]},
        )
        assert r.status_code == 400

    def test_unauth_blocked(self):
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        r = s.put(
            f"{BASE_URL}/api/churches/{OSM_CHURCH_ID}/overlay",
            json={"mass_times": ["x"]},
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# 3) Decorated listing endpoints
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def community_church(client_a):
    # Create a community-added church we control
    payload = {
        "name": "TEST Overlay Parish",
        "lat": 40.7501,
        "lng": -73.9851,
        "address": "5 TEST Street",
    }
    r = client_a.post(f"{BASE_URL}/api/churches/manual", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


class TestListingDecoration:
    def test_search_decorates_with_overlay_metadata(self, client_a, community_church):
        cid = community_church["church_id"]
        # Add overlay with attribution
        r = client_a.put(
            f"{BASE_URL}/api/churches/{cid}/overlay",
            json={
                "mass_times": ["Sun 10 AM", "Sun 12 PM"],
                "website": "https://overlay.example",
                "show_name": True,
            },
        )
        assert r.status_code == 200, r.text

        # Search by name (community)
        r = client_a.get(
            f"{BASE_URL}/api/churches/search",
            params={"q": "TEST Overlay Parish"},
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        match = next((c for c in items if c["church_id"] == cid), None)
        assert match is not None, "community church should appear in search results"
        # Decorated metadata
        assert match.get("editor_count") == 1
        assert USER_A_NAME in (match.get("contributors") or [])
        assert match.get("last_edited_by") == USER_A_NAME
        # Merged mass times — should contain overlay's entries
        mass = [t.lower() for t in match.get("mass_times") or []]
        assert "sun 10 am" in mass
        assert "sun 12 pm" in mass

    def test_nearby_decorates_with_overlay_metadata(self, client_a, community_church):
        r = client_a.get(
            f"{BASE_URL}/api/churches/nearby",
            params={"lat": 40.7501, "lng": -73.9851, "radius_m": 2000, "enrich": "false"},
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        match = next((c for c in items if c["church_id"] == community_church["church_id"]), None)
        assert match is not None, "community church should appear in nearby results"
        assert match.get("editor_count") == 1
        assert match.get("last_edited_by") == USER_A_NAME

    def test_saved_decorates_with_overlay_metadata(self, client_a, community_church):
        # Save the community church
        sp = {
            "church_id": community_church["church_id"],
            "name": community_church["name"],
            "lat": community_church["lat"],
            "lng": community_church["lng"],
        }
        r = client_a.post(f"{BASE_URL}/api/churches/save", json=sp)
        assert r.status_code == 200, r.text

        r = client_a.get(f"{BASE_URL}/api/churches/saved")
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        match = next((c for c in items if c["church_id"] == community_church["church_id"]), None)
        assert match is not None
        assert match.get("editor_count") == 1
        assert USER_A_NAME in (match.get("contributors") or [])


# ---------------------------------------------------------------------------
# 4) GET /api/parish-events/me/list
# ---------------------------------------------------------------------------
class TestMyEvents:
    def test_my_events_returns_only_my_events(self, client_a, client_b):
        # User A creates an event
        future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        end = (datetime.now(timezone.utc) + timedelta(days=3, hours=1)).isoformat()
        payload = {
            "type": "adoration",
            "title": "TEST Holy Hour A",
            "description": "Adoration for testing",
            "start_at": future,
            "end_at": end,
            "lat": 40.7500,
            "lng": -73.9800,
            "church_name": "TEST Parish A",
        }
        r = client_a.post(f"{BASE_URL}/api/parish-events", json=payload)
        assert r.status_code == 200, r.text
        ev_id_a = r.json()["id"]

        # User B creates a different event
        payload_b = dict(payload, title="TEST Holy Hour B")
        r = client_b.post(f"{BASE_URL}/api/parish-events", json=payload_b)
        assert r.status_code == 200, r.text
        ev_id_b = r.json()["id"]

        # /me/list for A contains A's event, not B's
        r = client_a.get(f"{BASE_URL}/api/parish-events/me/list")
        assert r.status_code == 200, r.text
        ids_a = [e["id"] for e in r.json()["items"]]
        assert ev_id_a in ids_a
        assert ev_id_b not in ids_a

        # /me/list for B contains B's event, not A's
        r = client_b.get(f"{BASE_URL}/api/parish-events/me/list")
        assert r.status_code == 200, r.text
        ids_b = [e["id"] for e in r.json()["items"]]
        assert ev_id_b in ids_b
        assert ev_id_a not in ids_b

    def test_my_events_requires_auth(self):
        s = requests.Session()
        r = s.get(f"{BASE_URL}/api/parish-events/me/list")
        assert r.status_code == 401
