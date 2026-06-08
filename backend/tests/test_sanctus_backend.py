"""Sanctus backend test suite.
Covers health, liturgical calendar, auth, preferences, and AI-generated meal/workout flows.
"""
import re
import time
import pytest


# ---------- Health ----------
class TestHealth:
    def test_root_health(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/")
        assert r.status_code == 200
        data = r.json()
        assert data == {"app": "Sanctus", "status": "ok"}


# ---------- Liturgical calendar ----------
class TestLiturgical:
    def test_friday_ordinary_time_abstinence(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/liturgical/day", params={"date": "2026-02-13"})
        assert r.status_code == 200
        d = r.json()
        assert d["season"] == "Ordinary Time", d
        assert d["is_abstinence"] is True
        assert d["is_sunday"] is False

    def test_good_friday_2026(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/liturgical/day", params={"date": "2026-04-03"})
        assert r.status_code == 200
        d = r.json()
        assert d["feast"] == "Good Friday of the Lord's Passion"
        assert d["color"] == "red"
        assert d["is_fast"] is True
        assert d["is_abstinence"] is True

    def test_easter_sunday_2026(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/liturgical/day", params={"date": "2026-04-05"})
        assert r.status_code == 200
        d = r.json()
        assert d["season"] == "Easter"
        assert d["color"] == "white"
        assert d["feast"] == "Easter Sunday \u2014 Resurrection of the Lord"

    def test_christmas_2026(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/liturgical/day", params={"date": "2026-12-25"})
        assert r.status_code == 200
        d = r.json()
        assert d["season"] == "Christmas"
        assert d["rank"] == "solemnity"
        assert d["color"] == "white"

    def test_ash_wednesday_2026(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/liturgical/day", params={"date": "2026-02-18"})
        assert r.status_code == 200
        d = r.json()
        assert d["feast"] == "Ash Wednesday"
        assert d["color"] == "purple"
        assert d["is_fast"] is True

    def test_invalid_date_format(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/liturgical/day", params={"date": "bad-date"})
        assert r.status_code == 400

    def test_month_april_2026_lent_to_easter(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/liturgical/month", params={"year": 2026, "month": 4})
        assert r.status_code == 200
        body = r.json()
        days = body["days"]
        assert len(days) == 30
        # April 1-4: Lent/Triduum; April 5 onward: Easter
        by_date = {d["date"]: d for d in days}
        assert by_date["2026-04-01"]["season"] == "Lent"
        assert by_date["2026-04-03"]["season"] == "Paschal Triduum"
        assert by_date["2026-04-05"]["season"] == "Easter"
        assert by_date["2026-04-30"]["season"] == "Easter"

    def test_invalid_month(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/liturgical/month", params={"year": 2026, "month": 13})
        assert r.status_code == 400


# ---------- Auth (unauthenticated) ----------
class TestAuthUnauth:
    def test_me_no_token(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/auth/me")
        assert r.status_code == 401

    def test_session_invalid(self, anon_client, base_url):
        r = anon_client.post(f"{base_url}/api/auth/session", json={"session_id": "totally-bogus"})
        assert r.status_code == 401

    def test_preferences_no_token(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/preferences")
        assert r.status_code == 401

    def test_meals_no_token(self, anon_client, base_url):
        r = anon_client.get(f"{base_url}/api/meals", params={"date": "2026-02-13"})
        assert r.status_code == 401


# ---------- Authenticated flow ----------
class TestAuthenticatedFlow:
    def test_auth_me(self, auth_client, base_url, seeded_user):
        r = auth_client.get(f"{base_url}/api/auth/me")
        assert r.status_code == 200
        body = r.json()
        assert body["user_id"] == seeded_user["user_id"]
        assert body["email"] == seeded_user["email"]

    def test_preferences_default(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/preferences")
        assert r.status_code == 200
        body = r.json()
        assert body["dietary"] == "balanced"
        assert body["fitness_level"] == "intermediate"

    def test_preferences_update(self, auth_client, base_url):
        payload = {"dietary": "vegetarian", "fitness_level": "advanced",
                   "allergies": "peanuts", "fitness_goal": "endurance",
                   "devotion_focus": "rosary"}
        r = auth_client.put(f"{base_url}/api/preferences", json=payload)
        assert r.status_code == 200
        # Verify via GET (persistence)
        g = auth_client.get(f"{base_url}/api/preferences")
        assert g.status_code == 200
        data = g.json()
        assert data["dietary"] == "vegetarian"
        assert data["fitness_level"] == "advanced"


def _flatten_meat_text(plan_doc):
    plan = plan_doc.get("plan", {})
    parts = []
    for meal_key in ("breakfast", "lunch", "dinner"):
        m = plan.get(meal_key) or {}
        parts.append((m.get("name") or "").lower())
        parts.append((m.get("description") or "").lower())
        for ing in m.get("ingredients") or []:
            parts.append(str(ing).lower())
    return " | ".join(parts)


class TestAIGeneration:
    @pytest.fixture(scope="class")
    def meal_doc(self, auth_client, base_url):
        # Friday 2026-02-13 -> abstinence
        r = auth_client.post(f"{base_url}/api/meals/generate", json={"date": "2026-02-13"}, timeout=90)
        assert r.status_code == 200, r.text
        return r.json()

    @pytest.fixture(scope="class")
    def workout_doc(self, auth_client, base_url):
        # Sunday 2026-02-15
        r = auth_client.post(f"{base_url}/api/workouts/generate", json={"date": "2026-02-15"}, timeout=90)
        assert r.status_code == 200, r.text
        return r.json()

    def test_meal_structure(self, meal_doc):
        assert "_id" not in meal_doc
        plan = meal_doc["plan"]
        for k in ("breakfast", "lunch", "dinner", "reflection"):
            assert k in plan, f"missing {k}"
        for meal_key in ("breakfast", "lunch", "dinner"):
            m = plan[meal_key]
            assert "name" in m and "ingredients" in m and "prep_minutes" in m
            assert isinstance(m["ingredients"], list)

    def test_friday_abstinence_no_meat(self, meal_doc):
        """CRITICAL: Friday abstinence -- no chicken/beef/pork in dinner."""
        plan = meal_doc["plan"]
        dinner = plan["dinner"]
        text = " ".join([
            (dinner.get("name") or "").lower(),
            (dinner.get("description") or "").lower(),
            " ".join(str(i).lower() for i in dinner.get("ingredients") or []),
        ])
        # Forbidden land-animal meats (allow fish/seafood/turkey-bacon? strict per spec)
        forbidden = ["chicken", "beef", "pork", "bacon", "ham", "steak", "lamb", "veal", "sausage"]
        # Use word boundary check to avoid e.g. "porkchop" tricks too
        offenders = [m for m in forbidden if re.search(rf"\b{m}\b", text)]
        assert not offenders, f"Friday meal contains meat: {offenders}; dinner={dinner}"

    def test_workout_structure(self, workout_doc):
        assert "_id" not in workout_doc
        plan = workout_doc["plan"]
        for k in ("title", "focus", "duration_minutes", "exercises",
                  "opening_prayer", "closing_prayer", "reflection"):
            assert k in plan, f"missing {k}"
        assert isinstance(plan["exercises"], list)

    def test_sunday_rest_content(self, workout_doc):
        plan = workout_doc["plan"]
        blob = " ".join([
            (plan.get("title") or "").lower(),
            (plan.get("focus") or "").lower(),
            (plan.get("reflection") or "").lower(),
            " ".join((ex.get("name") or "").lower() for ex in plan.get("exercises") or []),
            " ".join((ex.get("notes") or "").lower() for ex in plan.get("exercises") or []),
        ])
        # Expect at least one of: rest / gentle / walk / stretch
        assert any(w in blob for w in ("rest", "gentle", "walk", "stretch", "restoration", "leisure")), \
            f"Sunday workout doesn't reference rest/gentle/walking: {plan}"


class TestMealWorkoutRetrieval:
    def test_get_meal_persists(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/meals", params={"date": "2026-02-13"})
        assert r.status_code == 200
        body = r.json()
        assert body, "no saved meal doc returned"
        assert "_id" not in body
        assert body.get("date") == "2026-02-13"
        assert "plan" in body

    def test_meals_week(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/meals/week", params={"start": "2026-02-09"})
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 7
        # The Friday should contain the doc generated above
        assert body.get("2026-02-13") is not None
        # MongoDB _id should not appear in any returned doc
        for v in body.values():
            if v:
                assert "_id" not in v

    def test_workouts_week(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/workouts/week", params={"start": "2026-02-09"})
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 7
        assert body.get("2026-02-15") is not None
        for v in body.values():
            if v:
                assert "_id" not in v

    def test_meals_week_bad_date(self, auth_client, base_url):
        r = auth_client.get(f"{base_url}/api/meals/week", params={"start": "not-a-date"})
        assert r.status_code == 400


class TestLogout:
    def test_logout_removes_session(self, base_url, mongo_db):
        """Insert a fresh ephemeral session, then log it out."""
        from datetime import datetime, timedelta, timezone
        token = "test_token_logout_xyz"
        mongo_db.user_sessions.insert_one({
            "session_token": token,
            "user_id": "test_user_1",
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
        })
        import requests
        r = requests.post(f"{base_url}/api/auth/logout",
                          headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        # Verify session removed
        assert mongo_db.user_sessions.find_one({"session_token": token}) is None
        # And /auth/me now 401
        me = requests.get(f"{base_url}/api/auth/me",
                          headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 401
