"""Backend tests for Daily Practice Recommendations feature."""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or "http://localhost:8001"
).rstrip("/")


# -- Isolated user fixture (don't pollute the seeded ui_test_user_1) --
@pytest.fixture(scope="module")
def fresh_user(mongo_db):
    uid = f"test_dp_user_{uuid.uuid4().hex[:8]}"
    token = f"TEST_DP_TOKEN_{uuid.uuid4().hex[:10]}"
    mongo_db.users.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid, "email": f"{uid}@test.app",
                  "name": "DP Tester", "picture": None,
                  "created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    mongo_db.user_sessions.update_one(
        {"session_token": token},
        {"$set": {"session_token": token, "user_id": uid,
                  "created_at": datetime.now(timezone.utc),
                  "expires_at": datetime.now(timezone.utc) + timedelta(days=1)}},
        upsert=True,
    )
    yield {"user_id": uid, "token": token}
    # Cleanup
    mongo_db.daily_practices.delete_many({"user_id": uid})
    mongo_db.user_sessions.delete_many({"user_id": uid})
    mongo_db.users.delete_many({"user_id": uid})


@pytest.fixture(scope="module")
def dp_client(fresh_user):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {fresh_user['token']}",
    })
    return s


# -- Pool size constant (verified from daily_practices.PRACTICES) --
EXPECTED_POOL_MIN = 80
EXPECTED_POOL_MAX = 120


class TestDailyPracticeShape:
    """Test 1: GET returns proper shape."""

    def test_get_today_returns_expected_shape(self, dp_client):
        r = dp_client.get(f"{BASE_URL}/api/daily-practice?date=2026-06-08")
        assert r.status_code == 200, r.text
        body = r.json()
        for key in ("id", "category", "title", "body", "why", "virtue",
                    "intensity", "date", "completed_at", "note"):
            assert key in body, f"missing {key} in {body}"
        assert body["date"] == "2026-06-08"
        assert body["completed_at"] is None
        assert body["note"] is None
        assert isinstance(body["title"], str) and len(body["title"]) > 0
        assert body["intensity"] in {"easy", "moderate", "hard"}


class TestDailyPracticeIdempotency:
    """Test 2: same date returns same id."""

    def test_idempotent_same_date(self, dp_client):
        r1 = dp_client.get(f"{BASE_URL}/api/daily-practice?date=2026-06-09")
        r2 = dp_client.get(f"{BASE_URL}/api/daily-practice?date=2026-06-09")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"]


class TestDailyPracticeRotation:
    """Test 3: 30 consecutive dates → 30 unique practice ids (most important)."""

    def test_30_day_unique_rotation(self, dp_client):
        ids = []
        start = datetime(2026, 6, 8)
        for i in range(30):
            d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
            r = dp_client.get(f"{BASE_URL}/api/daily-practice?date={d}")
            assert r.status_code == 200, f"day {d}: {r.text}"
            ids.append(r.json()["id"])
        unique = set(ids)
        assert len(unique) == 30, (
            f"Expected 30 unique ids across 30 days, got {len(unique)}. "
            f"Duplicates: {[x for x in ids if ids.count(x) > 1][:10]}"
        )


class TestDailyPracticeCompletion:
    """Tests 4, 5, 6: complete / re-get / undo."""

    DATE = "2026-06-08"

    def test_complete_sets_completed_and_note(self, dp_client):
        r = dp_client.post(
            f"{BASE_URL}/api/daily-practice/complete",
            json={"date": self.DATE, "note": "offered for my brother"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["completed_at"] is not None
        assert body["note"] == "offered for my brother"

    def test_idempotent_after_completion(self, dp_client):
        # First record the original id
        orig = dp_client.get(f"{BASE_URL}/api/daily-practice?date={self.DATE}").json()
        assert orig["completed_at"] is not None, "should still be completed"
        assert orig["note"] == "offered for my brother"

    def test_undo_clears_completed(self, dp_client):
        r = dp_client.delete(
            f"{BASE_URL}/api/daily-practice/complete?date={self.DATE}"
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["completed_at"] is None
        assert body["note"] is None
        # confirm GET also shows null
        r2 = dp_client.get(f"{BASE_URL}/api/daily-practice?date={self.DATE}")
        assert r2.json()["completed_at"] is None


class TestDailyPracticeHistory:
    """Test 7: history sorted newest-first, total_pool present."""

    def test_history(self, dp_client):
        # Make sure rotation test has populated some data
        # (test ordering: rotation runs in same module first)
        r = dp_client.get(f"{BASE_URL}/api/daily-practice/history?limit=30")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and "total_pool" in data
        assert EXPECTED_POOL_MIN <= data["total_pool"] <= EXPECTED_POOL_MAX, (
            f"total_pool={data['total_pool']} not in expected range"
        )
        items = data["items"]
        # rotation test created assignments; should be >= 30 entries with our DATE values
        assert len(items) >= 1
        dates = [it["date"] for it in items]
        # newest-first
        assert dates == sorted(dates, reverse=True), f"not newest-first: {dates}"


class TestDailyPracticeAuth:
    """Test 8: 401 without Authorization header."""

    def test_get_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/daily-practice?date=2026-06-08")
        assert r.status_code == 401, r.text

    def test_post_complete_requires_auth(self):
        r = requests.post(
            f"{BASE_URL}/api/daily-practice/complete",
            json={"date": "2026-06-08"},
        )
        assert r.status_code == 401, r.text

    def test_delete_complete_requires_auth(self):
        r = requests.delete(
            f"{BASE_URL}/api/daily-practice/complete?date=2026-06-08"
        )
        assert r.status_code == 401, r.text

    def test_history_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/daily-practice/history?limit=30")
        assert r.status_code == 401, r.text


class TestDailyPracticeBadLimit:
    """Test 9: invalid limit → 400."""

    def test_history_bad_limit_too_high(self, dp_client):
        r = dp_client.get(f"{BASE_URL}/api/daily-practice/history?limit=999")
        assert r.status_code == 400, r.text

    def test_history_bad_limit_zero(self, dp_client):
        r = dp_client.get(f"{BASE_URL}/api/daily-practice/history?limit=0")
        assert r.status_code == 400, r.text
