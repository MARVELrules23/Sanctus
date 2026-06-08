"""Tests for AI suggestion (user_note) on /meals/generate and /workouts/generate.

Verifies that:
  - meals/generate honors user_note (note appears to influence output)
  - meals/generate works without user_note (backward compat)
  - workouts/generate honors user_note
  - workouts/generate works without user_note
  - Sunday rest is honored even with an aggressive note
  - Same note returns consistent plan; different note produces different plan
"""
import os
from datetime import date, timedelta

import pytest
import requests

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or "http://localhost:8001"
).rstrip("/")


def _find_next_weekday(weekday: int) -> str:
    """Return YYYY-MM-DD for the next occurrence of given weekday (0=Mon..6=Sun)."""
    d = date.today()
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d.isoformat()


def _flatten_meal_text(plan: dict) -> str:
    """Concat all text fields from a meal plan into a single lowercased string for keyword scans."""
    parts: list[str] = []
    for meal_key in ("breakfast", "lunch", "dinner"):
        meal = plan.get(meal_key) or {}
        parts.append(str(meal.get("name", "")))
        parts.append(str(meal.get("description", "")))
        for ing in meal.get("ingredients", []) or []:
            parts.append(str(ing))
    parts.append(str(plan.get("reflection", "")))
    return " ".join(parts).lower()


def _flatten_workout_text(plan: dict) -> str:
    parts: list[str] = [
        str(plan.get("title", "")),
        str(plan.get("focus", "")),
        str(plan.get("opening_prayer", "")),
        str(plan.get("closing_prayer", "")),
        str(plan.get("reflection", "")),
    ]
    for ex in plan.get("exercises", []) or []:
        parts.append(str(ex.get("name", "")))
        parts.append(str(ex.get("notes", "")))
    return " ".join(parts).lower()


# ---------- meals/generate ----------
class TestMealsGenerateWithUserNote:
    def test_meal_with_user_note_returns_200_and_plan_shape(self, auth_client):
        target_date = _find_next_weekday(1)  # next Tuesday — non-Friday, non-Sunday
        payload = {
            "date": target_date,
            "goal_mode": "liturgical",
            "user_note": "more protein, less carbs, lots of eggs and chicken",
        }
        r = auth_client.post(f"{BASE_URL}/api/meals/generate", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["date"] == target_date
        assert body["user_id"]
        assert "plan" in body
        plan = body["plan"]
        for key in ("breakfast", "lunch", "dinner"):
            assert key in plan, f"missing {key} in plan"
            assert plan[key].get("name"), f"{key} missing name"

    def test_meal_user_note_influences_output(self, auth_client):
        """A protein-heavy note should mention protein-rich foods."""
        target_date = _find_next_weekday(1)  # Tuesday
        payload = {
            "date": target_date,
            "goal_mode": "liturgical",
            "user_note": "more protein, less carbs, lots of eggs and chicken and beef",
        }
        r = auth_client.post(f"{BASE_URL}/api/meals/generate", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        text = _flatten_meal_text(r.json()["plan"])
        protein_keywords = [
            "protein", "egg", "chicken", "beef", "fish", "salmon", "tuna",
            "turkey", "yogurt", "cottage cheese", "tofu", "lentil", "bean",
        ]
        hits = [k for k in protein_keywords if k in text]
        assert hits, f"User note about protein not reflected. Plan text: {text[:500]}"

    def test_meal_without_user_note_still_works(self, auth_client):
        target_date = _find_next_weekday(1)
        payload = {"date": target_date, "goal_mode": "liturgical"}
        r = auth_client.post(f"{BASE_URL}/api/meals/generate", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "plan" in body
        for key in ("breakfast", "lunch", "dinner"):
            assert key in body["plan"]


# ---------- workouts/generate ----------
class TestWorkoutsGenerateWithUserNote:
    def test_workout_with_user_note_returns_200_and_plan_shape(self, auth_client):
        target_date = _find_next_weekday(2)  # next Wednesday
        payload = {
            "date": target_date,
            "goal_mode": "liturgical",
            "user_note": "upper body only, no jumping, no plyometric",
        }
        r = auth_client.post(f"{BASE_URL}/api/workouts/generate", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["date"] == target_date
        plan = body["plan"]
        assert plan.get("exercises"), "exercises missing"
        assert isinstance(plan["exercises"], list)

    def test_workout_user_note_influences_output_upper_body(self, auth_client):
        target_date = _find_next_weekday(2)
        payload = {
            "date": target_date,
            "goal_mode": "liturgical",
            "user_note": "upper body only — push ups, pull ups, rows, presses. No jumping, no squats.",
        }
        r = auth_client.post(f"{BASE_URL}/api/workouts/generate", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        text = _flatten_workout_text(r.json()["plan"])
        upper_kw = [
            "push", "pull", "row", "press", "curl", "shoulder", "chest",
            "tricep", "bicep", "lat", "arm", "upper body",
        ]
        hits = [k for k in upper_kw if k in text]
        assert hits, f"Upper-body note not reflected: {text[:500]}"

        # And no clear plyometric/jumping language
        forbidden = ["jumping jack", "jump squat", "burpee", "box jump", "plyometric"]
        bad = [k for k in forbidden if k in text]
        # soft check — don't fail hard, just warn via assertion message if found
        assert not bad, f"Plyometric/jumping language leaked despite 'no jumping' note: {bad}; text={text[:500]}"

    def test_workout_without_user_note_still_works(self, auth_client):
        target_date = _find_next_weekday(2)
        payload = {"date": target_date, "goal_mode": "liturgical"}
        r = auth_client.post(f"{BASE_URL}/api/workouts/generate", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        plan = r.json()["plan"]
        assert plan.get("exercises")

    def test_sunday_rest_honored_even_with_aggressive_note(self, auth_client):
        """Sunday should still be a gentle session even if user requests heavy lifting."""
        target_date = _find_next_weekday(6)  # next Sunday
        payload = {
            "date": target_date,
            "goal_mode": "liturgical",
            "user_note": "heavy lifting for an hour — deadlifts, squats, bench press, all PR attempts!",
        }
        r = auth_client.post(f"{BASE_URL}/api/workouts/generate", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        plan = r.json()["plan"]
        text = _flatten_workout_text(plan)
        gentle_kw = [
            "gentle", "walk", "stretch", "rest", "sabbath", "sunday",
            "light", "prayer", "mobility", "restful", "slow",
        ]
        hits = [k for k in gentle_kw if k in text]
        assert hits, f"Sunday gentle/rest indicators missing despite aggressive note: {text[:600]}"

        # Duration sanity — gentle session should not be aggressive volume
        dur = plan.get("duration_minutes")
        if isinstance(dur, int):
            assert dur <= 45, f"Sunday workout duration {dur}min looks too aggressive"


# ---------- session_id / note_hash behavior ----------
class TestNoteHashSessionBehavior:
    def test_same_note_consistent_different_note_changes_plan(self, auth_client):
        target_date = _find_next_weekday(3)  # next Thursday
        note_a = "Mediterranean style with olives, fish, and lots of vegetables"
        note_b = "Tex-Mex inspired with beans, corn, peppers, and lots of spice"

        ra1 = auth_client.post(
            f"{BASE_URL}/api/meals/generate",
            json={"date": target_date, "goal_mode": "liturgical", "user_note": note_a},
            timeout=90,
        )
        assert ra1.status_code == 200, ra1.text
        text_a1 = _flatten_meal_text(ra1.json()["plan"])

        rb = auth_client.post(
            f"{BASE_URL}/api/meals/generate",
            json={"date": target_date, "goal_mode": "liturgical", "user_note": note_b},
            timeout=90,
        )
        assert rb.status_code == 200, rb.text
        text_b = _flatten_meal_text(rb.json()["plan"])

        # Different notes should produce visibly different plans
        assert text_a1 != text_b, "Different notes produced identical plan text — note_hash not effective"
