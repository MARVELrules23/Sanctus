"""Backend tests for Liturgical Challenges (Hallowtide/Advent/Lent).

Focus: list/detail, enroll idempotency, checkin streak, my-progress,
admin gating, admin patch, publish/unpublish, generate-days basic.
"""
from datetime import datetime, timedelta, timezone

import pytest
import requests

from conftest import BASE_URL  # type: ignore


ADMIN_USER_ID = "TEST_chal_admin_1"
ADMIN_EMAIL = "TEST_chal_admin@sanctus.app"
ADMIN_TOKEN = "TEST_chal_admin_tok"

USER_USER_ID = "TEST_chal_user_1"
USER_EMAIL = "TEST_chal_user@sanctus.app"
USER_TOKEN = "TEST_chal_user_tok"


@pytest.fixture(scope="module")
def admin_session(mongo_db):
    mongo_db.users.update_one(
        {"user_id": ADMIN_USER_ID},
        {"$set": {"user_id": ADMIN_USER_ID, "email": ADMIN_EMAIL,
                  "name": "TEST Chal Admin", "is_admin": True,
                  "created_at": datetime.now(timezone.utc)}}, upsert=True,
    )
    mongo_db.user_sessions.update_one(
        {"session_token": ADMIN_TOKEN},
        {"$set": {"session_token": ADMIN_TOKEN, "user_id": ADMIN_USER_ID,
                  "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
                  "created_at": datetime.now(timezone.utc)}}, upsert=True,
    )
    yield {"token": ADMIN_TOKEN, "user_id": ADMIN_USER_ID}
    mongo_db.user_sessions.delete_many({"user_id": ADMIN_USER_ID})
    mongo_db.users.delete_many({"user_id": ADMIN_USER_ID})


@pytest.fixture(scope="module")
def user_session(mongo_db):
    mongo_db.users.update_one(
        {"user_id": USER_USER_ID},
        {"$set": {"user_id": USER_USER_ID, "email": USER_EMAIL,
                  "name": "TEST Chal User", "is_admin": False,
                  "created_at": datetime.now(timezone.utc)}}, upsert=True,
    )
    mongo_db.user_sessions.update_one(
        {"session_token": USER_TOKEN},
        {"$set": {"session_token": USER_TOKEN, "user_id": USER_USER_ID,
                  "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
                  "created_at": datetime.now(timezone.utc)}}, upsert=True,
    )
    yield {"token": USER_TOKEN, "user_id": USER_USER_ID}
    mongo_db.challenge_enrollments.delete_many({"user_id": USER_USER_ID})
    mongo_db.challenge_checkins.delete_many({"user_id": USER_USER_ID})
    mongo_db.user_sessions.delete_many({"user_id": USER_USER_ID})
    mongo_db.users.delete_many({"user_id": USER_USER_ID})


def _hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def published_tracks(admin_session, mongo_db):
    """Ensure all 3 tracks are published for non-admin tests."""
    for slug in ("hallowtide", "advent", "lent"):
        requests.post(f"{BASE_URL}/api/challenges/admin/{slug}/publish",
                      headers=_hdr(admin_session["token"]), timeout=20)
    yield


# ----- Public list/detail -----

class TestPublicList:
    def test_list_published_for_user(self, user_session, published_tracks):
        r = requests.get(f"{BASE_URL}/api/challenges",
                         headers=_hdr(user_session["token"]), timeout=20)
        assert r.status_code == 200
        data = r.json()
        slugs = {it["slug"] for it in data["items"]}
        assert {"hallowtide", "advent", "lent"} <= slugs
        for it in data["items"]:
            assert it["status"] == "published"
            assert "enrolled" in it

    def test_get_hallowtide_detail_has_soul_cakes(self, user_session, published_tracks):
        r = requests.get(f"{BASE_URL}/api/challenges/hallowtide",
                         headers=_hdr(user_session["token"]), timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["opening_prayer"]
        assert isinstance(d.get("days"), list)
        prep = d.get("preparation_content") or {}
        recipe_blob = str(prep).lower()
        assert "soul cake" in recipe_blob

    def test_day_shape(self, user_session, published_tracks):
        r = requests.get(f"{BASE_URL}/api/challenges/hallowtide",
                         headers=_hdr(user_session["token"]), timeout=20)
        d = r.json()
        if d.get("days"):
            day = d["days"][0]
            for k in ("day_id", "day_index", "patron_saint", "reflection", "prayer_items"):
                assert k in day


# ----- Enroll / Unenroll / Checkin -----

class TestEnrollAndCheckin:
    def test_enroll_idempotent(self, user_session, published_tracks):
        slug = "advent"
        r1 = requests.post(f"{BASE_URL}/api/challenges/{slug}/enroll",
                           headers=_hdr(user_session["token"]), timeout=15)
        assert r1.status_code == 200 and r1.json()["ok"] is True
        r2 = requests.post(f"{BASE_URL}/api/challenges/{slug}/enroll",
                           headers=_hdr(user_session["token"]), timeout=15)
        assert r2.status_code == 200 and r2.json().get("already") is True

    def test_unenroll(self, user_session, published_tracks):
        slug = "lent"
        requests.post(f"{BASE_URL}/api/challenges/{slug}/enroll",
                      headers=_hdr(user_session["token"]), timeout=15)
        r = requests.delete(f"{BASE_URL}/api/challenges/{slug}/enroll",
                            headers=_hdr(user_session["token"]), timeout=15)
        assert r.status_code == 200 and r.json()["removed"] >= 1

    def test_checkin_idempotent_and_streak(self, user_session, published_tracks):
        slug = "hallowtide"
        # Enroll first
        requests.post(f"{BASE_URL}/api/challenges/{slug}/enroll",
                      headers=_hdr(user_session["token"]), timeout=15)
        today_iso = datetime.now(timezone.utc).date().isoformat()
        payload = {"date": today_iso, "completed": True, "items_done": ["a"]}
        r1 = requests.post(f"{BASE_URL}/api/challenges/{slug}/checkin",
                           headers=_hdr(user_session["token"]), json=payload, timeout=15)
        assert r1.status_code == 200, r1.text
        s1 = r1.json()["total_days_completed"]
        # Duplicate same date — should not double count
        r2 = requests.post(f"{BASE_URL}/api/challenges/{slug}/checkin",
                           headers=_hdr(user_session["token"]), json=payload, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["total_days_completed"] == s1
        assert r2.json()["current_streak"] >= 1

    def test_my_progress(self, user_session, published_tracks):
        r = requests.get(f"{BASE_URL}/api/challenges/hallowtide/my-progress",
                         headers=_hdr(user_session["token"]), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["enrolled"] is True
        assert isinstance(d["checkins"], list) and len(d["checkins"]) >= 1


# ----- Admin -----

class TestAdmin:
    def test_admin_all_ok(self, admin_session):
        r = requests.get(f"{BASE_URL}/api/challenges/admin/all",
                         headers=_hdr(admin_session["token"]), timeout=15)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 3

    def test_admin_all_forbidden_for_non_admin(self, user_session):
        r = requests.get(f"{BASE_URL}/api/challenges/admin/all",
                         headers=_hdr(user_session["token"]), timeout=15)
        assert r.status_code == 403

    def test_admin_patch_challenge(self, admin_session, mongo_db):
        slug = "advent"
        new_blurb = "TEST_QA blurb " + datetime.now(timezone.utc).isoformat()
        r = requests.patch(f"{BASE_URL}/api/challenges/admin/{slug}",
                           headers=_hdr(admin_session["token"]),
                           json={"blurb": new_blurb}, timeout=15)
        assert r.status_code == 200
        assert r.json()["blurb"] == new_blurb

    def test_admin_patch_day(self, admin_session, mongo_db):
        # Find a day for hallowtide
        doc = mongo_db.liturgical_challenges.find_one({"slug": "hallowtide"})
        if not doc:
            pytest.skip("no hallowtide challenge")
        day = mongo_db.challenge_days.find_one({"challenge_id": doc["challenge_id"]})
        if not day:
            pytest.skip("no day docs; generate-days has not yet run")
        new_title = "TEST_QA Day title"
        r = requests.patch(f"{BASE_URL}/api/challenges/admin/days/{day['day_id']}",
                           headers=_hdr(admin_session["token"]),
                           json={"title": new_title}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["title"] == new_title

    def test_publish_unpublish_cycle(self, admin_session):
        slug = "lent"
        r = requests.post(f"{BASE_URL}/api/challenges/admin/{slug}/unpublish",
                          headers=_hdr(admin_session["token"]), timeout=15)
        assert r.status_code == 200 and r.json()["status"] == "draft"
        r = requests.post(f"{BASE_URL}/api/challenges/admin/{slug}/publish",
                          headers=_hdr(admin_session["token"]), timeout=15)
        assert r.status_code == 200 and r.json()["status"] == "published"

    def test_generate_days_overwrite_false_skips(self, admin_session, mongo_db):
        """overwrite=false: existing days are skipped (no AI cost)."""
        doc = mongo_db.liturgical_challenges.find_one({"slug": "hallowtide"})
        # Just request a single existing day to keep it fast.
        if not doc:
            pytest.skip("no hallowtide")
        existing = mongo_db.challenge_days.find_one({"challenge_id": doc["challenge_id"]})
        if not existing:
            pytest.skip("no days to test skip-path")
        day_str = existing.get("date_str") or existing["date"].date().isoformat()
        r = requests.post(
            f"{BASE_URL}/api/challenges/admin/hallowtide/generate-days",
            headers=_hdr(admin_session["token"]),
            json={"overwrite": False, "days": [day_str]}, timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert any(it.get("skipped") for it in body["results"])
