"""Tests for new iteration endpoints: /api/readings and /api/journal CRUD,
plus a brief smoke pass on previously-tested core endpoints.

Auth: We seed users + user_sessions directly in MongoDB and send
Authorization: Bearer <token>.
"""
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests


# ---------- second seeded user for cross-user isolation tests ----------
SECOND_USER_ID = "test_user_2"
SECOND_EMAIL = "test2@sanctus.app"
SECOND_TOKEN = "test_token_xyz_2"


@pytest.fixture(scope="module")
def second_user(mongo_db):
    mongo_db.users.update_one(
        {"user_id": SECOND_USER_ID},
        {"$set": {"user_id": SECOND_USER_ID, "email": SECOND_EMAIL,
                  "name": "Test User 2", "picture": None,
                  "created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    mongo_db.user_sessions.update_one(
        {"session_token": SECOND_TOKEN},
        {"$set": {"session_token": SECOND_TOKEN, "user_id": SECOND_USER_ID,
                  "created_at": datetime.now(timezone.utc),
                  "expires_at": datetime.now(timezone.utc) + timedelta(days=1)}},
        upsert=True,
    )
    yield {"user_id": SECOND_USER_ID, "token": SECOND_TOKEN}
    mongo_db.user_sessions.delete_many({"user_id": SECOND_USER_ID})
    mongo_db.users.delete_many({"user_id": SECOND_USER_ID})
    mongo_db.journal.delete_many({"user_id": SECOND_USER_ID})


@pytest.fixture(scope="module")
def second_client(second_user):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {second_user['token']}",
    })
    return s


# =========================================================================
# /api/readings
# =========================================================================
class TestReadings:
    def test_readings_requires_auth(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/readings", params={"date": "2026-01-15"})
        assert r.status_code == 401

    def test_readings_invalid_date(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/readings", params={"date": "not-a-date"})
        assert r.status_code == 400

    def test_readings_today_universalis(self, auth_client, base_url, mongo_db):
        """Today's readings should ideally come from Universalis (live).
        Also accept usccb or ai-fallback. Validate structure."""
        today = datetime.now(timezone.utc).date().isoformat()
        # Clear any pre-existing cache to exercise live fetch
        mongo_db.readings.delete_one({"date": today})

        t0 = time.time()
        r = auth_client.get(f"{base_url}/api/readings", params={"date": today}, timeout=60)
        first_dur = time.time() - t0
        assert r.status_code == 200, r.text
        body = r.json()
        # Structural checks
        for k in ("date", "liturgical", "source", "usccb_url",
                  "first_reading", "psalm", "gospel", "gospel_acclamation",
                  "reflection", "cached_at"):
            assert k in body, f"missing field {k}"
        assert body["date"] == today
        assert body["source"] in ("universalis", "usccb", "ai-fallback")
        assert body["usccb_url"].startswith("https://bible.usccb.org/")
        # Source-specific: live source should have a non-empty gospel citation
        if body["source"] in ("universalis", "usccb"):
            assert body["gospel"], "live readings should include a gospel citation"
            assert body["first_reading"], "live readings should include first reading citation"
        # Cache check — second call should be much faster and same source
        t1 = time.time()
        r2 = auth_client.get(f"{base_url}/api/readings", params={"date": today}, timeout=30)
        second_dur = time.time() - t1
        assert r2.status_code == 200
        body2 = r2.json()
        # If first was universalis, the cache code path only short-circuits for source=='usccb'.
        # Either way, second call must succeed; we just log timings.
        print(f"readings first={first_dur:.2f}s second={second_dur:.2f}s "
              f"source={body['source']} second_source={body2['source']}")
        assert body2["date"] == today

    def test_readings_future_date_fallback(self, auth_client, base_url, mongo_db):
        """For a future date, Universalis won't serve and USCCB likely 403s — expect ai-fallback (or usccb if lucky)."""
        future_date = "2027-03-21"
        mongo_db.readings.delete_one({"date": future_date})
        r = auth_client.get(f"{base_url}/api/readings", params={"date": future_date}, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["source"] in ("usccb", "ai-fallback")
        assert body["usccb_url"].startswith("https://bible.usccb.org/")
        assert "liturgical" in body and body["liturgical"]["date"] == future_date
        assert "_id" not in body

    def test_readings_no_mongo_id(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/readings",
                            params={"date": datetime.now(timezone.utc).date().isoformat()},
                            timeout=60)
        assert r.status_code == 200
        assert "_id" not in r.json()


# =========================================================================
# /api/journal CRUD
# =========================================================================
class TestJournal:
    @pytest.fixture(autouse=True)
    def _clean(self, mongo_db):
        # cleanup any leftover from a previous run before each test class instance
        yield
        mongo_db.journal.delete_many({"user_id": {"$in": ["test_user_1", SECOND_USER_ID]}})

    # ----- auth requirements -----
    def test_journal_list_requires_auth(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/journal")
        assert r.status_code == 401

    def test_journal_create_requires_auth(self, anon_client, base_url):
        r = anon_client.post(f"{base_url}/api/journal",
                             json={"date": "2026-01-15", "body": "x"})
        assert r.status_code == 401

    def test_journal_get_requires_auth(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/journal/jrn_does_not_exist")
        assert r.status_code == 401

    def test_journal_update_requires_auth(self, anon_client, base_url):
        r = anon_client.put(f"{base_url}/api/journal/jrn_x",
                            json={"date": "2026-01-15", "body": "y"})
        assert r.status_code == 401

    def test_journal_delete_requires_auth(self, anon_client, base_url):
        r = anon_client.delete(f"{base_url}/api/journal/jrn_x")
        assert r.status_code == 401

    # ----- create / read flow -----
    def test_create_journal_minimal(self, auth_client, base_url):
        payload = {"date": "2026-01-15",
                   "title": "TEST_morning offering",
                   "body": "Lord, I offer this day.",
                   "mood": "grateful"}
        r = auth_client.post(f"{base_url}/api/journal", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["entry_id"].startswith("jrn_")
        assert body["date"] == payload["date"]
        assert body["title"] == payload["title"]
        assert body["body"] == payload["body"]
        assert body["mood"] == "grateful"
        assert "liturgical" in body and body["liturgical"]["date"] == "2026-01-15"
        assert "_id" not in body

        # Verify persistence via GET single
        eid = body["entry_id"]
        g = auth_client.get(f"{base_url}/api/journal/{eid}")
        assert g.status_code == 200
        gbody = g.json()
        assert gbody["entry_id"] == eid
        assert gbody["body"] == payload["body"]
        assert "_id" not in gbody

    def test_create_journal_empty_body_400(self, auth_client, base_url):
        r = auth_client.post(f"{base_url}/api/journal",
                             json={"date": "2026-01-15", "body": "   "})
        assert r.status_code == 400

    def test_create_journal_invalid_date_400(self, auth_client, base_url):
        r = auth_client.post(f"{base_url}/api/journal",
                             json={"date": "bad-date", "body": "hi"})
        assert r.status_code == 400

    def test_list_journal_sorted_and_filter(self, auth_client, base_url):
        # Create 3 entries across 2 dates
        a = auth_client.post(f"{base_url}/api/journal",
                             json={"date": "2026-01-10", "body": "TEST_a"})
        b = auth_client.post(f"{base_url}/api/journal",
                             json={"date": "2026-01-11", "body": "TEST_b"})
        c = auth_client.post(f"{base_url}/api/journal",
                             json={"date": "2026-01-11", "body": "TEST_c"})
        assert a.status_code == b.status_code == c.status_code == 200

        # List all
        r = auth_client.get(f"{base_url}/api/journal")
        assert r.status_code == 200
        items = r.json()["items"]
        # Most-recent first (c was created last)
        bodies = [it["body"] for it in items if it["body"].startswith("TEST_")]
        assert bodies[0] == "TEST_c", bodies
        # Filter by date
        r2 = auth_client.get(f"{base_url}/api/journal",
                             params={"date": "2026-01-11"})
        assert r2.status_code == 200
        items2 = r2.json()["items"]
        for it in items2:
            assert it["date"] == "2026-01-11"
        # At least our 2 TEST_ entries on that date
        test_bodies = sorted(it["body"] for it in items2 if it["body"].startswith("TEST_"))
        assert test_bodies == ["TEST_b", "TEST_c"]

        # Filter by date invalid
        r3 = auth_client.get(f"{base_url}/api/journal", params={"date": "bad-date"})
        assert r3.status_code == 400

        # Limit param
        r4 = auth_client.get(f"{base_url}/api/journal", params={"limit": 1})
        assert r4.status_code == 200
        assert len(r4.json()["items"]) <= 1

    def test_update_journal(self, auth_client, base_url):
        create = auth_client.post(
            f"{base_url}/api/journal",
            json={"date": "2026-01-12", "title": "TEST_old", "body": "old body", "mood": "sad"},
        )
        assert create.status_code == 200
        eid = create.json()["entry_id"]

        upd = auth_client.put(
            f"{base_url}/api/journal/{eid}",
            json={"date": "2026-01-12", "title": "TEST_new",
                  "body": "updated body", "mood": "joyful"},
        )
        assert upd.status_code == 200, upd.text
        ubody = upd.json()
        assert ubody["title"] == "TEST_new"
        assert ubody["body"] == "updated body"
        assert ubody["mood"] == "joyful"

        # Verify via GET
        g = auth_client.get(f"{base_url}/api/journal/{eid}")
        assert g.status_code == 200
        gbody = g.json()
        assert gbody["body"] == "updated body"
        assert gbody["mood"] == "joyful"

    def test_update_journal_empty_body_400(self, auth_client, base_url):
        create = auth_client.post(f"{base_url}/api/journal",
                                  json={"date": "2026-01-12", "body": "x"})
        eid = create.json()["entry_id"]
        r = auth_client.put(f"{base_url}/api/journal/{eid}",
                            json={"date": "2026-01-12", "body": "   "})
        assert r.status_code == 400

    def test_update_journal_not_found(self, auth_client, base_url):
        r = auth_client.put(f"{base_url}/api/journal/jrn_doesnotexist",
                            json={"date": "2026-01-12", "body": "hello"})
        assert r.status_code == 404

    def test_get_journal_not_found(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/journal/jrn_doesnotexist_xyz")
        assert r.status_code == 404

    def test_delete_journal(self, auth_client, base_url):
        create = auth_client.post(f"{base_url}/api/journal",
                                  json={"date": "2026-01-13", "body": "delete me"})
        assert create.status_code == 200
        eid = create.json()["entry_id"]
        d1 = auth_client.delete(f"{base_url}/api/journal/{eid}")
        assert d1.status_code == 200
        assert d1.json() == {"ok": True}
        # Second delete → 404
        d2 = auth_client.delete(f"{base_url}/api/journal/{eid}")
        assert d2.status_code == 404
        # GET → 404
        g = auth_client.get(f"{base_url}/api/journal/{eid}")
        assert g.status_code == 404

    # ----- cross-user isolation -----
    def test_journal_user_scoping(self, auth_client, base_url, second_client):
        # User 1 creates an entry
        r = auth_client.post(f"{base_url}/api/journal",
                             json={"date": "2026-01-14", "title": "TEST_priv",
                                   "body": "user 1 secret"})
        assert r.status_code == 200
        eid = r.json()["entry_id"]

        # User 2 cannot GET it
        g = second_client.get(f"{base_url}/api/journal/{eid}")
        assert g.status_code == 404

        # User 2 cannot UPDATE it
        u = second_client.put(f"{base_url}/api/journal/{eid}",
                              json={"date": "2026-01-14", "body": "hijack"})
        assert u.status_code == 404

        # User 2 cannot DELETE it
        d = second_client.delete(f"{base_url}/api/journal/{eid}")
        assert d.status_code == 404

        # User 2 list does not include user 1's entry
        ll = second_client.get(f"{base_url}/api/journal")
        assert ll.status_code == 200
        for it in ll.json()["items"]:
            assert it["entry_id"] != eid

        # User 1 still sees it
        g2 = auth_client.get(f"{base_url}/api/journal/{eid}")
        assert g2.status_code == 200
        assert g2.json()["body"] == "user 1 secret"


# =========================================================================
# Smoke regression for existing endpoints
# =========================================================================
class TestSmokeRegression:
    def test_liturgical_day(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/liturgical/day", params={"date": "2026-02-13"})
        assert r.status_code == 200
        assert r.json()["is_abstinence"] is True

    def test_meals_grocery_endpoint(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/meals/grocery", params={"start": "2026-02-09"})
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and isinstance(body["items"], list)
        assert "days_with_meals" in body

    def test_meals_grocery_bad_date(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/meals/grocery", params={"start": "bad"})
        assert r.status_code == 400

    def test_save_meal_endpoint(self, auth_client, base_url):
        payload = {
            "date": "2026-02-20",
            "breakfast": {"name": "TEST oats", "ingredients": ["oats", "milk"], "prep_minutes": 5},
            "lunch": {"name": "TEST salad", "ingredients": ["lettuce", "tuna"], "prep_minutes": 10},
            "dinner": {"name": "TEST fish", "ingredients": ["salmon", "rice"], "prep_minutes": 25},
            "reflection": "Friday abstinence meal.",
        }
        r = auth_client.post(f"{base_url}/api/meals/save", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["source"] == "user"
        assert body["plan"]["dinner"]["name"] == "TEST fish"
        # Verify persistence
        g = auth_client.get(f"{base_url}/api/meals", params={"date": "2026-02-20"})
        assert g.status_code == 200
        assert g.json()["plan"]["lunch"]["name"] == "TEST salad"

    def test_save_workout_endpoint(self, auth_client, base_url):
        payload = {
            "date": "2026-02-21",
            "title": "TEST workout",
            "focus": "strength",
            "duration_minutes": 30,
            "exercises": [{"name": "Pushups", "sets": "3x10", "notes": ""}],
            "opening_prayer": "Begin in His name",
            "closing_prayer": "Thanks be to God",
            "reflection": "offered up",
        }
        r = auth_client.post(f"{base_url}/api/workouts/save", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["source"] == "user"
        assert body["plan"]["title"] == "TEST workout"
        g = auth_client.get(f"{base_url}/api/workouts", params={"date": "2026-02-21"})
        assert g.status_code == 200
        assert g.json()["plan"]["title"] == "TEST workout"
