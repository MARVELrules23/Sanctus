"""Phase 1 backend additions:

- PUT /api/auth/me — update name/picture (validation, size, auth)
- POST /api/meals/generate and POST /api/workouts/generate — `goal_mode`
  ("liturgical" | "goals") field behavior with/without wellness profile
- Regression smoke for previously-working endpoints

Live AI calls go through Claude via the Emergent Universal Key (no mocking).
We intentionally do NOT assert AI content quality; only response shape and
status codes.
"""
import os
import time

import pytest
import requests

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or "http://localhost:8001"
).rstrip("/")


# ============================================================================
# PUT /api/auth/me
# ============================================================================
class TestUpdateMe:
    """PUT /api/auth/me — profile updates."""

    def test_update_name_success(self, auth_client, mongo_db, seeded_user):
        # Restore original name first so this test is order-independent
        mongo_db.users.update_one(
            {"user_id": seeded_user["user_id"]}, {"$set": {"name": "Test User"}}
        )
        r = auth_client.put(f"{BASE_URL}/api/auth/me", json={"name": "NewName"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["name"] == "NewName"
        assert body["user_id"] == seeded_user["user_id"]
        # Verify persistence
        doc = mongo_db.users.find_one({"user_id": seeded_user["user_id"]})
        assert doc["name"] == "NewName"

    def test_update_name_empty_rejected(self, auth_client):
        r = auth_client.put(f"{BASE_URL}/api/auth/me", json={"name": ""})
        assert r.status_code == 400, r.text
        assert "name" in r.json()["detail"].lower()

    def test_update_name_whitespace_rejected(self, auth_client):
        r = auth_client.put(f"{BASE_URL}/api/auth/me", json={"name": "  "})
        assert r.status_code == 400, r.text

    def test_update_name_too_long_rejected(self, auth_client):
        r = auth_client.put(f"{BASE_URL}/api/auth/me", json={"name": "x" * 80})
        assert r.status_code == 400, r.text

    def test_update_picture_data_uri_accepted(self, auth_client, mongo_db, seeded_user):
        # 1x1 transparent PNG
        data_uri = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lE"
            "QVQYV2NgAAIAAAUAAeImBZsAAAAASUVORK5CYII="
        )
        r = auth_client.put(f"{BASE_URL}/api/auth/me", json={"picture": data_uri})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["picture"] == data_uri
        doc = mongo_db.users.find_one({"user_id": seeded_user["user_id"]})
        assert doc["picture"] == data_uri

    def test_update_picture_empty_clears(self, auth_client, mongo_db, seeded_user):
        # First ensure something is set
        auth_client.put(f"{BASE_URL}/api/auth/me",
                        json={"picture": "https://example.com/x.jpg"})
        r = auth_client.put(f"{BASE_URL}/api/auth/me", json={"picture": ""})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["picture"] is None
        doc = mongo_db.users.find_one({"user_id": seeded_user["user_id"]})
        assert doc["picture"] is None

    def test_update_picture_http_url_accepted(self, auth_client):
        r = auth_client.put(f"{BASE_URL}/api/auth/me",
                            json={"picture": "https://example.com/x.jpg"})
        assert r.status_code == 200, r.text
        assert r.json()["picture"] == "https://example.com/x.jpg"

    def test_update_picture_invalid_url_rejected(self, auth_client):
        r = auth_client.put(f"{BASE_URL}/api/auth/me",
                            json={"picture": "not-a-url"})
        assert r.status_code == 400, r.text
        assert "picture" in r.json()["detail"].lower()

    def test_update_picture_too_large_rejected(self, auth_client):
        huge = "data:image/png;base64," + ("A" * 3_000_000)
        r = auth_client.put(f"{BASE_URL}/api/auth/me", json={"picture": huge})
        assert r.status_code == 413, r.text

    def test_update_me_requires_auth(self, anon_client):
        r = anon_client.put(f"{BASE_URL}/api/auth/me", json={"name": "Hacker"})
        assert r.status_code == 401, r.text


# ============================================================================
# POST /api/meals/generate — goal_mode
# ============================================================================
@pytest.fixture(scope="module")
def cleanup_phase1_data(mongo_db, seeded_user):
    """Make sure meals/workouts/wellness slate is clean between runs."""
    uid = seeded_user["user_id"]
    mongo_db.meals.delete_many({"user_id": uid})
    mongo_db.workouts.delete_many({"user_id": uid})
    mongo_db.wellness.delete_many({"user_id": uid})
    yield
    mongo_db.meals.delete_many({"user_id": uid})
    mongo_db.workouts.delete_many({"user_id": uid})
    mongo_db.wellness.delete_many({"user_id": uid})


def _assert_meal_plan_shape(body):
    assert "plan" in body
    plan = body["plan"]
    for slot in ("breakfast", "lunch", "dinner"):
        assert slot in plan, f"missing {slot} in plan: {plan}"
        assert "name" in plan[slot]


class TestMealsGenerateGoalMode:
    def test_liturgical_mode_explicit(self, auth_client, cleanup_phase1_data):
        r = auth_client.post(
            f"{BASE_URL}/api/meals/generate",
            json={"date": "2026-06-10", "goal_mode": "liturgical"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["goal_mode"] == "liturgical"
        _assert_meal_plan_shape(body)

    def test_goals_mode_without_wellness_profile(self, auth_client, mongo_db, seeded_user, cleanup_phase1_data):
        # Ensure no wellness profile exists
        mongo_db.wellness.delete_many({"user_id": seeded_user["user_id"]})
        r = auth_client.post(
            f"{BASE_URL}/api/meals/generate",
            json={"date": "2026-06-10", "goal_mode": "goals"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["goal_mode"] == "goals"
        _assert_meal_plan_shape(body)

    def test_default_goal_mode_is_liturgical(self, auth_client, cleanup_phase1_data):
        r = auth_client.post(
            f"{BASE_URL}/api/meals/generate",
            json={"date": "2026-06-11"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["goal_mode"] == "liturgical"
        _assert_meal_plan_shape(body)

    def test_goals_mode_with_wellness_profile(self, auth_client, cleanup_phase1_data):
        # Save a wellness profile first
        prof = auth_client.put(
            f"{BASE_URL}/api/wellness/profile",
            json={
                "weight_kg": 80,
                "height_cm": 180,
                "target_weight_kg": 75,
                "goal_type": "lose",
                "activity_level": "moderate",
            },
        )
        assert prof.status_code == 200, prof.text
        # Tiny delay to let LLM-side rate limiters breathe
        time.sleep(1)
        r = auth_client.post(
            f"{BASE_URL}/api/meals/generate",
            json={"date": "2026-06-10", "goal_mode": "goals"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["goal_mode"] == "goals"
        _assert_meal_plan_shape(body)
        # Reflection field should be present (may be empty string if AI omitted)
        assert "reflection" in body["plan"]

    def test_invalid_date_rejected(self, auth_client):
        r = auth_client.post(
            f"{BASE_URL}/api/meals/generate",
            json={"date": "not-a-date", "goal_mode": "liturgical"},
        )
        assert r.status_code == 400, r.text


# ============================================================================
# POST /api/workouts/generate — goal_mode
# ============================================================================
def _assert_workout_plan_shape(body):
    assert "plan" in body
    plan = body["plan"]
    assert "title" in plan
    assert "exercises" in plan
    assert isinstance(plan["exercises"], list)


class TestWorkoutsGenerateGoalMode:
    def test_liturgical_mode_explicit(self, auth_client, cleanup_phase1_data):
        r = auth_client.post(
            f"{BASE_URL}/api/workouts/generate",
            json={"date": "2026-06-10", "goal_mode": "liturgical"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["goal_mode"] == "liturgical"
        _assert_workout_plan_shape(body)

    def test_goals_mode_with_wellness_profile(self, auth_client, cleanup_phase1_data):
        # Ensure wellness profile exists (re-PUT to be safe; idempotent)
        auth_client.put(
            f"{BASE_URL}/api/wellness/profile",
            json={
                "weight_kg": 80,
                "height_cm": 180,
                "target_weight_kg": 75,
                "goal_type": "lose",
                "activity_level": "moderate",
            },
        )
        time.sleep(1)
        r = auth_client.post(
            f"{BASE_URL}/api/workouts/generate",
            json={"date": "2026-06-10", "goal_mode": "goals"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["goal_mode"] == "goals"
        _assert_workout_plan_shape(body)

    def test_default_goal_mode_is_liturgical(self, auth_client, cleanup_phase1_data):
        r = auth_client.post(
            f"{BASE_URL}/api/workouts/generate",
            json={"date": "2026-06-11"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["goal_mode"] == "liturgical"
        _assert_workout_plan_shape(body)


# ============================================================================
# Regression smoke
# ============================================================================
class TestPhase1Regressions:
    def test_get_auth_me(self, auth_client):
        r = auth_client.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "user_id" in body
        assert "email" in body

    def test_churches_nearby(self, auth_client):
        # Philadelphia-ish
        r = auth_client.get(
            f"{BASE_URL}/api/churches/nearby",
            params={"lat": 40.0387, "lng": -75.2207, "radius_m": 5000},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body
        assert isinstance(body["items"], list)

    def test_churches_search(self, auth_client):
        time.sleep(1.2)  # be polite to Nominatim
        r = auth_client.get(
            f"{BASE_URL}/api/churches/search",
            params={"q": "Holy Name"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body
        assert isinstance(body["items"], list)

    def test_wellness_profile_get(self, auth_client):
        r = auth_client.get(f"{BASE_URL}/api/wellness/profile")
        assert r.status_code == 200, r.text
        body = r.json()
        # _wellness_doc shape - keys always present
        for k in ("weight_kg", "height_cm", "goal_type", "activity_level"):
            assert k in body

    def test_wellness_log_post(self, auth_client, mongo_db, seeded_user):
        r = auth_client.post(
            f"{BASE_URL}/api/wellness/log",
            json={"date": "2026-06-12", "weight_kg": 79.2, "note": "TEST_phase1"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["weight_kg"] == 79.2
        assert body["date"] == "2026-06-12"
        # Cleanup
        mongo_db.weight_log.delete_many(
            {"user_id": seeded_user["user_id"], "date": "2026-06-12"}
        )

    def test_journal_create(self, auth_client, mongo_db, seeded_user):
        r = auth_client.post(
            f"{BASE_URL}/api/journal",
            json={"date": "2026-06-12", "kind": "free",
                  "body": "TEST_phase1 journal entry"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "entry_id" in body
        # Cleanup
        mongo_db.journal.delete_many({"entry_id": body["entry_id"]})
