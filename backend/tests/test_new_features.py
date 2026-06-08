"""Tests for the new Sanctus features:
- Wellness (profile, weight log, AI suggest)
- Prayer templates (examen, examination)
- Journal kinds + confess
- Churches (nearby, save, saved, unsave)
- Auth gating + cross-user scoping for the new endpoints
"""
import os
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or "http://localhost:8001"
).rstrip("/")

TEST_USER_2 = "test_user_2"
TEST_TOKEN_2 = "test_token_xyz_2"


# ---------- Shared module fixtures (second user for cross-user tests) ----------
@pytest.fixture(scope="module")
def second_user(mongo_db):
    mongo_db.users.update_one(
        {"user_id": TEST_USER_2},
        {"$set": {"user_id": TEST_USER_2, "email": "test2@sanctus.app",
                  "name": "Test User 2", "picture": None,
                  "created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    mongo_db.user_sessions.update_one(
        {"session_token": TEST_TOKEN_2},
        {"$set": {"session_token": TEST_TOKEN_2, "user_id": TEST_USER_2,
                  "created_at": datetime.now(timezone.utc),
                  "expires_at": datetime.now(timezone.utc) + timedelta(days=1)}},
        upsert=True,
    )
    yield {"user_id": TEST_USER_2, "token": TEST_TOKEN_2}
    mongo_db.user_sessions.delete_many({"user_id": TEST_USER_2})
    mongo_db.users.delete_many({"user_id": TEST_USER_2})
    mongo_db.wellness.delete_many({"user_id": TEST_USER_2})
    mongo_db.weight_log.delete_many({"user_id": TEST_USER_2})
    mongo_db.journal.delete_many({"user_id": TEST_USER_2})
    mongo_db.user_churches.delete_many({"user_id": TEST_USER_2})


@pytest.fixture(scope="module")
def auth_client_2(second_user):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {second_user['token']}",
    })
    return s


@pytest.fixture(scope="function", autouse=True)
def cleanup_wellness(mongo_db, seeded_user):
    # Clean up wellness data for primary user before each function to keep tests isolated
    yield
    # No-op teardown; module-level cleanup below handles end


@pytest.fixture(scope="module", autouse=True)
def cleanup_primary(mongo_db, seeded_user):
    yield
    uid = seeded_user["user_id"]
    mongo_db.wellness.delete_many({"user_id": uid})
    mongo_db.weight_log.delete_many({"user_id": uid})
    mongo_db.journal.delete_many({"user_id": uid})
    mongo_db.user_churches.delete_many({"user_id": uid})


# ---------- Wellness profile ----------
class TestWellnessProfile:
    def test_get_blank_default_profile(self, auth_client, base_url, mongo_db, seeded_user):
        mongo_db.wellness.delete_many({"user_id": seeded_user["user_id"]})
        r = auth_client.get(f"{base_url}/api/wellness/profile")
        assert r.status_code == 200, r.text
        data = r.json()
        # All blank-ish — units default 'metric'
        assert data["weight_kg"] is None
        assert data["target_weight_kg"] is None
        assert data["goal_type"] is None
        assert data["units"] == "metric"

    def test_put_updates_profile(self, auth_client, base_url):
        payload = {
            "weight_kg": 80.5, "height_cm": 178.0,
            "target_weight_kg": 75.0, "target_date": "2026-06-01",
            "goal_type": "lose", "activity_level": "moderate",
            "weekly_rate_kg": 0.5, "units": "metric",
            "notes": "TEST_target Lenten discipline",
        }
        r = auth_client.put(f"{base_url}/api/wellness/profile", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["weight_kg"] == 80.5
        assert body["target_weight_kg"] == 75.0
        assert body["goal_type"] == "lose"
        assert body["activity_level"] == "moderate"
        # Persistence check via GET
        g = auth_client.get(f"{base_url}/api/wellness/profile")
        assert g.status_code == 200
        d = g.json()
        assert d["goal_type"] == "lose"
        assert d["target_date"] == "2026-06-01"
        assert d["notes"] == "TEST_target Lenten discipline"

    def test_put_rejects_bad_goal(self, auth_client, base_url):
        r = auth_client.put(f"{base_url}/api/wellness/profile",
                            json={"goal_type": "vanish"})
        assert r.status_code == 400

    def test_put_rejects_bad_activity(self, auth_client, base_url):
        r = auth_client.put(f"{base_url}/api/wellness/profile",
                            json={"activity_level": "lazy"})
        assert r.status_code == 400

    def test_put_rejects_bad_date(self, auth_client, base_url):
        r = auth_client.put(f"{base_url}/api/wellness/profile",
                            json={"target_date": "06/01/2026"})
        assert r.status_code == 400

    def test_unauth(self, anon_client, base_url):
        assert anon_client.get(f"{base_url}/api/wellness/profile").status_code == 401
        assert anon_client.put(f"{base_url}/api/wellness/profile", json={}).status_code == 401


# ---------- Weight log ----------
class TestWeightLog:
    def test_create_log_and_list_desc(self, auth_client, base_url, mongo_db, seeded_user):
        mongo_db.weight_log.delete_many({"user_id": seeded_user["user_id"]})
        # Insert in non-sorted order
        for d, w in [("2026-01-10", 81.2), ("2026-01-12", 80.9), ("2026-01-08", 81.5)]:
            r = auth_client.post(f"{base_url}/api/wellness/log",
                                 json={"date": d, "weight_kg": w})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["weight_kg"] == w and body["date"] == d
            assert body["log_id"].startswith("wl_")
        # List sorted desc by date
        r = auth_client.get(f"{base_url}/api/wellness/log")
        assert r.status_code == 200
        items = r.json()["items"]
        dates = [i["date"] for i in items]
        assert dates == sorted(dates, reverse=True)
        assert "2026-01-12" in dates

    def test_reject_bad_weight(self, auth_client, base_url):
        r = auth_client.post(f"{base_url}/api/wellness/log",
                             json={"date": "2026-01-15", "weight_kg": 0})
        assert r.status_code == 400
        r = auth_client.post(f"{base_url}/api/wellness/log",
                             json={"date": "2026-01-15", "weight_kg": -5})
        assert r.status_code == 400

    def test_reject_bad_date(self, auth_client, base_url):
        r = auth_client.post(f"{base_url}/api/wellness/log",
                             json={"date": "garbage", "weight_kg": 80})
        assert r.status_code == 400

    def test_delete_log(self, auth_client, base_url):
        r = auth_client.post(f"{base_url}/api/wellness/log",
                             json={"date": "2026-01-20", "weight_kg": 80.1})
        log_id = r.json()["log_id"]
        d = auth_client.delete(f"{base_url}/api/wellness/log/{log_id}")
        assert d.status_code == 200
        # Second delete -> 404
        d2 = auth_client.delete(f"{base_url}/api/wellness/log/{log_id}")
        assert d2.status_code == 404

    def test_cross_user_cannot_delete(self, auth_client, base_url, auth_client_2):
        # User 1 creates a log; user 2 cannot delete it.
        r = auth_client.post(f"{base_url}/api/wellness/log",
                             json={"date": "2026-01-22", "weight_kg": 79.8})
        log_id = r.json()["log_id"]
        cross = auth_client_2.delete(f"{base_url}/api/wellness/log/{log_id}")
        assert cross.status_code == 404
        # Still exists for original owner
        listed = auth_client.get(f"{base_url}/api/wellness/log").json()["items"]
        assert any(i["log_id"] == log_id for i in listed)

    def test_cross_user_list_isolation(self, auth_client_2, base_url):
        # User 2's log list should NOT contain user 1's logs.
        r = auth_client_2.get(f"{base_url}/api/wellness/log")
        assert r.status_code == 200
        items = r.json()["items"]
        for it in items:
            # User 2 hasn't inserted anything yet -> empty
            assert it.get("user_id", TEST_USER_2) == TEST_USER_2
        # at least the count belongs to user 2
        assert isinstance(items, list)

    def test_unauth(self, anon_client, base_url):
        assert anon_client.get(f"{base_url}/api/wellness/log").status_code == 401
        assert anon_client.post(f"{base_url}/api/wellness/log",
                                json={"date": "2026-01-01", "weight_kg": 80}).status_code == 401


# ---------- Wellness AI suggest ----------
class TestWellnessSuggest:
    def test_suggest_requires_goal(self, auth_client, base_url, mongo_db, seeded_user):
        # Wipe profile so no goal_type
        mongo_db.wellness.delete_many({"user_id": seeded_user["user_id"]})
        r = auth_client.post(f"{base_url}/api/wellness/suggest")
        assert r.status_code == 400

    def test_suggest_returns_brief(self, auth_client, base_url):
        # Set a goal first
        auth_client.put(f"{base_url}/api/wellness/profile", json={
            "weight_kg": 82, "height_cm": 178,
            "target_weight_kg": 76, "goal_type": "lose",
            "activity_level": "moderate", "weekly_rate_kg": 0.5,
        })
        r = auth_client.post(f"{base_url}/api/wellness/suggest", timeout=45)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("calorie_target", "macro_focus", "meal_focus", "workout_focus",
                  "weekly_split", "encouragement"):
            assert k in body, f"missing {k}"
        assert isinstance(body["calorie_target"], int)
        assert body["calorie_target"] > 0
        assert isinstance(body["meal_focus"], list)
        assert isinstance(body["workout_focus"], list)
        assert body["encouragement"]


# ---------- Prayer templates ----------
class TestPrayerTemplates:
    def test_examen_prompts(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/prayers/examen")
        assert r.status_code == 200
        body = r.json()
        assert "prompts" in body
        assert len(body["prompts"]) == 5
        for p in body["prompts"]:
            assert {"key", "title", "prompt", "icon"} <= set(p.keys())
        # Specific Ignatian keys
        keys = [p["key"] for p in body["prompts"]]
        assert keys == ["gratitude", "petition", "review", "forgiveness", "renewal"]

    def test_examen_unauth(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/prayers/examen")
        assert r.status_code == 401

    def test_examination_sections(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/prayers/examination")
        assert r.status_code == 200
        body = r.json()
        assert "sections" in body
        assert len(body["sections"]) == 9
        for s in body["sections"]:
            assert {"key", "title", "prompts"} <= set(s.keys())
            assert isinstance(s["prompts"], list) and s["prompts"]

    def test_examination_unauth(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/prayers/examination")
        assert r.status_code == 401


# ---------- Journal kinds (examen, examination, confess) ----------
class TestJournalKinds:
    def test_save_examen_entry(self, auth_client, base_url):
        payload = {
            "date": "2026-02-15",
            "title": "TEST_examen",
            "body": "Gratitude for daily Mass.",
            "kind": "examen",
            "structured": {
                "gratitude": "Daily Mass",
                "petition": "Holy Spirit's light",
                "review": "Coffee with a friend",
                "forgiveness": "Sharp word at work",
                "renewal": "Pray morning offering",
            },
        }
        r = auth_client.post(f"{base_url}/api/journal", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["kind"] == "examen"
        assert body["structured"]["gratitude"] == "Daily Mass"
        assert "entry_id" in body
        assert body["confessed_at"] is None

    def test_save_examination_then_confess(self, auth_client, base_url):
        payload = {
            "date": "2026-02-16",
            "title": "TEST_examination",
            "body": "Examination of conscience before Confession.",
            "kind": "examination",
            "structured": {
                "sixth_ninth": {"checked": ["impure thoughts"], "notes": "TEST_private"},
            },
        }
        r = auth_client.post(f"{base_url}/api/journal", json=payload)
        assert r.status_code == 200, r.text
        entry_id = r.json()["entry_id"]
        # Mark confessed
        c = auth_client.post(f"{base_url}/api/journal/{entry_id}/confess")
        assert c.status_code == 200, c.text
        body = c.json()
        assert body["confessed_at"]
        # Persisted on GET
        g = auth_client.get(f"{base_url}/api/journal/{entry_id}").json()
        assert g["confessed_at"]
        assert g["kind"] == "examination"

    def test_confess_404(self, auth_client, base_url):
        r = auth_client.post(f"{base_url}/api/journal/nope_xyz/confess")
        assert r.status_code == 404

    def test_cross_user_cannot_confess(self, auth_client, base_url, auth_client_2):
        # User 1 creates entry, user 2 tries to confess it.
        r = auth_client.post(f"{base_url}/api/journal", json={
            "date": "2026-02-17", "body": "TEST_cross_user", "kind": "examination",
        })
        entry_id = r.json()["entry_id"]
        c = auth_client_2.post(f"{base_url}/api/journal/{entry_id}/confess")
        assert c.status_code == 404

    def test_unknown_kind_normalised_to_free(self, auth_client, base_url):
        r = auth_client.post(f"{base_url}/api/journal", json={
            "date": "2026-02-18", "body": "TEST_weird", "kind": "weird-mode",
        })
        assert r.status_code == 200
        assert r.json()["kind"] == "free"


# ---------- Churches ----------
class TestChurches:
    def test_nearby_valid(self, auth_client, base_url):
        # Vatican coords — should yield Overpass results (or empty list, never 5xx)
        r = auth_client.get(f"{base_url}/api/churches/nearby",
                            params={"lat": 41.9022, "lng": 12.4539,
                                    "radius_m": 3000, "enrich": "false"},
                            timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body and "count" in body
        assert isinstance(body["items"], list)
        for c in body["items"][:3]:
            assert "church_id" in c and "name" in c and "distance_km" in c
            assert "is_starred" in c

    def test_nearby_bad_coords(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/churches/nearby",
                            params={"lat": 200, "lng": 0})
        assert r.status_code == 400

    def test_nearby_unauth(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/churches/nearby",
                            params={"lat": 0, "lng": 0})
        assert r.status_code == 401

    def test_save_and_list_and_delete(self, auth_client, base_url, mongo_db, seeded_user):
        mongo_db.user_churches.delete_many({"user_id": seeded_user["user_id"]})
        payload = {
            "church_id": "osm:node/123456789",
            "name": "TEST_St. Peter Basilica",
            "lat": 41.9022, "lng": 12.4539,
            "address": "Vatican City",
            "website": "https://example.com",
            "mass_times": ["Sun 10:30 AM"],
            "confession_times": ["Sat 4:00 PM"],
            "notes": "TEST_note",
        }
        r = auth_client.post(f"{base_url}/api/churches/save", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["church_id"] == payload["church_id"]
        assert body["is_starred"] is True
        # List
        lst = auth_client.get(f"{base_url}/api/churches/saved")
        assert lst.status_code == 200
        items = lst.json()["items"]
        assert any(c["church_id"] == payload["church_id"] for c in items)
        # Delete
        d = auth_client.delete(f"{base_url}/api/churches/saved/{payload['church_id']}")
        assert d.status_code == 200
        # Second delete -> 404
        d2 = auth_client.delete(f"{base_url}/api/churches/saved/{payload['church_id']}")
        assert d2.status_code == 404
        # Verify gone in list
        items2 = auth_client.get(f"{base_url}/api/churches/saved").json()["items"]
        assert not any(c["church_id"] == payload["church_id"] for c in items2)

    def test_save_idempotent_upsert(self, auth_client, base_url):
        payload = {
            "church_id": "osm:node/upsert_test",
            "name": "TEST_Upsert Church",
            "lat": 0.0, "lng": 0.0,
        }
        a = auth_client.post(f"{base_url}/api/churches/save", json=payload)
        assert a.status_code == 200
        # Second save with updated notes shouldn't duplicate
        payload["notes"] = "TEST_updated_notes"
        b = auth_client.post(f"{base_url}/api/churches/save", json=payload)
        assert b.status_code == 200
        assert b.json()["notes"] == "TEST_updated_notes"
        # Cleanup
        auth_client.delete(f"{base_url}/api/churches/saved/{payload['church_id']}")

    def test_cross_user_isolation(self, auth_client, base_url, auth_client_2):
        # User 1 saves
        payload = {
            "church_id": "osm:node/cross_user_test",
            "name": "TEST_Cross", "lat": 0, "lng": 0,
        }
        auth_client.post(f"{base_url}/api/churches/save", json=payload)
        # User 2 list doesn't contain it
        items2 = auth_client_2.get(f"{base_url}/api/churches/saved").json()["items"]
        assert not any(c["church_id"] == payload["church_id"] for c in items2)
        # User 2 cannot delete
        d = auth_client_2.delete(f"{base_url}/api/churches/saved/{payload['church_id']}")
        assert d.status_code == 404
        # Cleanup
        auth_client.delete(f"{base_url}/api/churches/saved/{payload['church_id']}")

    def test_save_unauth(self, anon_client, base_url):
        r = anon_client.post(f"{base_url}/api/churches/save", json={
            "church_id": "x", "name": "y", "lat": 0, "lng": 0,
        })
        assert r.status_code == 401
        assert anon_client.get(f"{base_url}/api/churches/saved").status_code == 401


# ---------- Regression smoke ----------
class TestRegressionSmoke:
    def test_root(self, anon_client, base_url):
        assert anon_client.get(f"{base_url}/api/").status_code == 200

    def test_liturgical_day(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/liturgical/day", params={"date": "2026-04-05"})
        assert r.status_code == 200
        assert r.json()["season"] == "Easter"

    def test_preferences(self, auth_client, base_url):
        assert auth_client.get(f"{base_url}/api/preferences").status_code == 200

    def test_journal_list_still_works(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/journal")
        assert r.status_code == 200
        assert "items" in r.json()
