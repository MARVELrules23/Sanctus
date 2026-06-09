"""Tests for the new manual-church mass/confession arrays and the
parish_events module. Backend only."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env", override=False)

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or ""
).rstrip("/")
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL not set"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

API = f"{BASE_URL}/api"

# ----- Seed three test users with their own session tokens -----
_TEST_USER_IDS = ["pe_user_a", "pe_user_b", "pe_user_c"]
_TEST_TOKENS = {u: f"pe_tok_{u}_{uuid.uuid4().hex[:8]}" for u in _TEST_USER_IDS}


@pytest.fixture(scope="module")
def mongo():
    cli = MongoClient(MONGO_URL)
    db = cli[DB_NAME]
    yield db
    cli.close()


@pytest.fixture(scope="module", autouse=True)
def seed_users(mongo):
    now = datetime.now(timezone.utc)
    for uid in _TEST_USER_IDS:
        mongo.users.update_one(
            {"user_id": uid},
            {"$set": {"user_id": uid, "email": f"{uid}@test.app",
                      "name": uid.replace("_", " ").title(),
                      "picture": None, "created_at": now}},
            upsert=True,
        )
        mongo.user_sessions.update_one(
            {"session_token": _TEST_TOKENS[uid]},
            {"$set": {"session_token": _TEST_TOKENS[uid], "user_id": uid,
                      "created_at": now,
                      "expires_at": now + timedelta(days=1)}},
            upsert=True,
        )
    # Cleanup any prior test artefacts
    mongo.community_churches.delete_many({"submitted_by": {"$in": _TEST_USER_IDS}})
    mongo.parish_events.delete_many({"organizer_user_id": {"$in": _TEST_USER_IDS}})
    yield
    # Teardown
    for uid in _TEST_USER_IDS:
        mongo.user_sessions.delete_many({"user_id": uid})
        mongo.users.delete_many({"user_id": uid})
    mongo.community_churches.delete_many({"submitted_by": {"$in": _TEST_USER_IDS}})
    mongo.parish_events.delete_many({"organizer_user_id": {"$in": _TEST_USER_IDS}})


def _client(user_id: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_TEST_TOKENS[user_id]}",
    })
    return s


# Use a unique coordinate so we don't collide with prior tests.
TEST_LAT = 41.123456
TEST_LNG = -73.654321


# ============================================================
# A. Manual church + mass_times / confession_times round-trip
# ============================================================
class TestManualChurchTimes:
    def test_post_manual_church_with_times(self, mongo):
        mongo.community_churches.delete_many({"submitted_by": "pe_user_a"})
        r = _client("pe_user_a").post(f"{API}/churches/manual", json={
            "name": f"TEST_Parish_{uuid.uuid4().hex[:6]}",
            "lat": TEST_LAT,
            "lng": TEST_LNG,
            "address": "1 Test Way",
            "mass_times": ["Sun 9am", "Sun 11am", "Daily 7am"],
            "confession_times": ["Sat 3:30-4:30pm"],
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["source"] == "community"
        assert body["mass_times"] == ["Sun 9am", "Sun 11am", "Daily 7am"], \
            f"mass_times not echoed: {body.get('mass_times')!r}"
        assert body["confession_times"] == ["Sat 3:30-4:30pm"], \
            f"confession_times not echoed: {body.get('confession_times')!r}"

    def test_nearby_surfaces_manual_times(self, mongo):
        mongo.community_churches.delete_many({"submitted_by": "pe_user_a"})
        name = f"TEST_NearbyParish_{uuid.uuid4().hex[:6]}"
        post = _client("pe_user_a").post(f"{API}/churches/manual", json={
            "name": name,
            "lat": TEST_LAT + 0.001,
            "lng": TEST_LNG + 0.001,
            "address": "2 Test Way",
            "mass_times": ["Sun 10am"],
            "confession_times": ["Sat 4pm"],
        })
        assert post.status_code == 200, post.text

        r = _client("pe_user_a").get(
            f"{API}/churches/nearby",
            params={"lat": TEST_LAT, "lng": TEST_LNG, "radius_m": 15000, "enrich": "false"},
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        match = next((c for c in items if c.get("name") == name), None)
        assert match is not None, "manual church not surfaced by /nearby"
        assert match["source"] == "community"
        assert match.get("submitted_by_name")
        assert match.get("mass_times") == ["Sun 10am"], \
            f"mass_times missing on /nearby: {match.get('mass_times')!r}"
        assert match.get("confession_times") == ["Sat 4pm"], \
            f"confession_times missing on /nearby: {match.get('confession_times')!r}"

    def test_dedupe_case_insensitive(self, mongo):
        mongo.community_churches.delete_many({"submitted_by": "pe_user_a"})
        r = _client("pe_user_a").post(f"{API}/churches/manual", json={
            "name": f"TEST_DedupeParish_{uuid.uuid4().hex[:6]}",
            "lat": TEST_LAT + 0.01,
            "lng": TEST_LNG + 0.01,
            "mass_times": ["Sun 9am", "sun 9am", "  SUN 9AM  ", "Sun 11am"],
        })
        assert r.status_code == 200, r.text
        body = r.json()
        # dedupe case-insensitively → only 2 entries
        mt = body.get("mass_times") or []
        lc = [s.lower().strip() for s in mt]
        assert len(set(lc)) == len(mt), f"duplicates not removed: {mt}"
        assert len(mt) == 2, f"expected 2 unique entries, got {mt}"

    def test_oversized_list_handled_gracefully(self, mongo):
        mongo.community_churches.delete_many({"submitted_by": "pe_user_a"})
        many = [f"Time {i}" for i in range(40)]
        r = _client("pe_user_a").post(f"{API}/churches/manual", json={
            "name": f"TEST_Over_{uuid.uuid4().hex[:6]}",
            "lat": TEST_LAT + 0.02,
            "lng": TEST_LNG + 0.02,
            "mass_times": many,
        })
        assert r.status_code < 500, f"5xx on oversized list: {r.status_code} {r.text}"
        # Acceptable: either 422 (Pydantic) or 200 with first 24
        if r.status_code == 200:
            mt = r.json().get("mass_times") or []
            assert len(mt) <= 24, f"too many entries returned: {len(mt)}"
        else:
            assert r.status_code == 422, r.status_code

    def test_omitted_times_default_to_empty(self, mongo):
        mongo.community_churches.delete_many({"submitted_by": "pe_user_a"})
        r = _client("pe_user_a").post(f"{API}/churches/manual", json={
            "name": f"TEST_NoTimes_{uuid.uuid4().hex[:6]}",
            "lat": TEST_LAT + 0.03,
            "lng": TEST_LNG + 0.03,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("mass_times") == []
        assert body.get("confession_times") == []


# ============================================================
# B. Parish Events end-to-end
# ============================================================
EV_LAT = 40.7128
EV_LNG = -74.0060


def _future_iso(days_ahead: float = 3.0, hours: float = 0) -> str:
    dt = datetime.now(timezone.utc) + timedelta(days=days_ahead, hours=hours)
    return dt.isoformat()


class TestParishEvents:
    def test_create_with_church(self, mongo):
        mongo.parish_events.delete_many({"organizer_user_id": "pe_user_a"})
        r = _client("pe_user_a").post(f"{API}/parish-events", json={
            "type": "mass",
            "title": "TEST_Healing Mass",
            "description": "A healing Mass for the parish",
            "start_at": _future_iso(2),
            "end_at": _future_iso(2, 1),
            "church_id": "osm:1234",
            "church_name": "Test Parish",
            "address": "1 Saint Way",
            "lat": EV_LAT,
            "lng": EV_LNG,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["id"].startswith("pe_")
        assert body["type"] == "mass"
        assert body["type_label"] == "Mass"
        assert body["is_owner"] is True
        assert body["church_id"] == "osm:1234"
        pytest.shared_event_id = body["id"]

    def test_create_without_church(self):
        r = _client("pe_user_a").post(f"{API}/parish-events", json={
            "type": "rosary",
            "title": "TEST_Outdoor rosary",
            "start_at": _future_iso(4),
            "lat": EV_LAT,
            "lng": EV_LNG,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["church_id"] is None
        assert body["type_label"] == "Rosary"

    def test_list_by_church(self):
        r = _client("pe_user_b").get(
            f"{API}/parish-events", params={"church_id": "osm:1234"},
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) >= 1
        assert all(i["church_id"] == "osm:1234" for i in items)
        # is_owner is false for other user
        assert all(i["is_owner"] is False for i in items)

    def test_list_by_geo_distance(self):
        r = _client("pe_user_b").get(
            f"{API}/parish-events",
            params={"lat": EV_LAT, "lng": EV_LNG, "radius_m": 20000},
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) >= 1
        assert all("distance_km" in i for i in items)

    def test_list_filter_event_type(self):
        r = _client("pe_user_b").get(
            f"{API}/parish-events",
            params={"lat": EV_LAT, "lng": EV_LNG, "radius_m": 20000,
                    "event_type": "mass"},
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert all(i["type"] == "mass" for i in items), items

    def test_list_days_window_excludes_far_future(self, mongo):
        # Create an event 60 days out, then query days=10 — should be excluded.
        r = _client("pe_user_a").post(f"{API}/parish-events", json={
            "type": "talk",
            "title": "TEST_FarFutureTalk",
            "start_at": _future_iso(60),
            "lat": EV_LAT,
            "lng": EV_LNG,
        })
        assert r.status_code == 200, r.text
        far_id = r.json()["id"]

        list_r = _client("pe_user_a").get(
            f"{API}/parish-events",
            params={"lat": EV_LAT, "lng": EV_LNG, "radius_m": 20000, "days": 10},
        )
        assert list_r.status_code == 200
        ids = [i["id"] for i in list_r.json()["items"]]
        assert far_id not in ids, "far-future event leaked through days=10 filter"

    def test_flag_quorum_auto_hides(self, mongo):
        # Create event owned by user_a, flagged by b and c → only 2 flags, still visible.
        r = _client("pe_user_a").post(f"{API}/parish-events", json={
            "type": "talk",
            "title": "TEST_FlaggableTalk",
            "start_at": _future_iso(5),
            "lat": EV_LAT,
            "lng": EV_LNG,
        })
        assert r.status_code == 200
        ev_id = r.json()["id"]

        # owner cannot flag own event
        own = _client("pe_user_a").post(f"{API}/parish-events/{ev_id}/flag", json={"reason": "x"})
        assert own.status_code == 400

        f1 = _client("pe_user_b").post(f"{API}/parish-events/{ev_id}/flag", json={"reason": "spam"})
        assert f1.status_code == 200
        # same user flags again → either 400 or idempotent
        f1b = _client("pe_user_b").post(f"{API}/parish-events/{ev_id}/flag", json={})
        assert f1b.status_code in (200, 400), f1b.text

        doc = mongo.parish_events.find_one({"id": ev_id})
        assert doc["flag_count"] == 1, f"double-count on repeat flag: {doc['flag_count']}"

        # Detail endpoint reflects has_flagged for user b
        det = _client("pe_user_b").get(f"{API}/parish-events/{ev_id}")
        assert det.status_code == 200
        assert det.json()["has_flagged"] is True
        assert det.json()["flag_count"] == 1

        # Second unique flagger → still visible, count=2
        f2 = _client("pe_user_c").post(f"{API}/parish-events/{ev_id}/flag", json={})
        assert f2.status_code == 200
        assert f2.json().get("auto_hidden") is False

        list_r = _client("pe_user_a").get(
            f"{API}/parish-events",
            params={"lat": EV_LAT, "lng": EV_LNG, "radius_m": 20000},
        )
        ids = [i["id"] for i in list_r.json()["items"]]
        assert ev_id in ids, "event hidden too early"

        # Third unique flagger — directly inject a third reporter session.
        third_uid = "pe_user_d"
        third_tok = f"pe_tok_d_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        mongo.users.update_one(
            {"user_id": third_uid},
            {"$set": {"user_id": third_uid, "email": "d@t.app", "name": "User D"}},
            upsert=True,
        )
        mongo.user_sessions.update_one(
            {"session_token": third_tok},
            {"$set": {"session_token": third_tok, "user_id": third_uid,
                      "created_at": now,
                      "expires_at": now + timedelta(days=1)}},
            upsert=True,
        )
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json",
                          "Authorization": f"Bearer {third_tok}"})
        f3 = s.post(f"{API}/parish-events/{ev_id}/flag", json={})
        assert f3.status_code == 200, f3.text
        assert f3.json().get("auto_hidden") is True

        list_after = _client("pe_user_a").get(
            f"{API}/parish-events",
            params={"lat": EV_LAT, "lng": EV_LNG, "radius_m": 20000},
        )
        ids = [i["id"] for i in list_after.json()["items"]]
        assert ev_id not in ids, "event NOT auto-hidden at 3 flags"

        # Cleanup
        mongo.user_sessions.delete_many({"user_id": third_uid})
        mongo.users.delete_many({"user_id": third_uid})

    def test_delete_owner_and_non_owner(self):
        # owner=a creates
        r = _client("pe_user_a").post(f"{API}/parish-events", json={
            "type": "social",
            "title": "TEST_Festival",
            "start_at": _future_iso(7),
            "lat": EV_LAT,
            "lng": EV_LNG,
        })
        ev_id = r.json()["id"]

        # non-owner b cannot delete
        d1 = _client("pe_user_b").delete(f"{API}/parish-events/{ev_id}")
        assert d1.status_code == 403, d1.text

        # owner can delete
        d2 = _client("pe_user_a").delete(f"{API}/parish-events/{ev_id}")
        assert d2.status_code == 200

        # Now absent from list
        list_r = _client("pe_user_a").get(
            f"{API}/parish-events",
            params={"lat": EV_LAT, "lng": EV_LNG, "radius_m": 20000},
        )
        ids = [i["id"] for i in list_r.json()["items"]]
        assert ev_id not in ids

        # 404 on subsequent detail GET
        det = _client("pe_user_a").get(f"{API}/parish-events/{ev_id}")
        assert det.status_code == 404

    def test_me_list_scoped_to_caller(self):
        # b should not see a's events
        ra = _client("pe_user_a").get(f"{API}/parish-events/me/list")
        rb = _client("pe_user_b").get(f"{API}/parish-events/me/list")
        assert ra.status_code == 200 and rb.status_code == 200
        a_ids = {i["id"] for i in ra.json()["items"]}
        b_ids = {i["id"] for i in rb.json()["items"]}
        assert a_ids.isdisjoint(b_ids)
        for it in ra.json()["items"]:
            assert it["organizer_user_id"] == "pe_user_a"


# ============================================================
# C. Negative cases
# ============================================================
class TestNegativeCases:
    def test_past_start_at_rejected(self):
        past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        r = _client("pe_user_a").post(f"{API}/parish-events", json={
            "type": "mass",
            "title": "TEST_Past",
            "start_at": past,
            "lat": EV_LAT,
            "lng": EV_LNG,
        })
        assert r.status_code == 400, r.status_code

    def test_end_before_start_rejected(self):
        start = _future_iso(2)
        end = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        r = _client("pe_user_a").post(f"{API}/parish-events", json={
            "type": "mass",
            "title": "TEST_BadEnd",
            "start_at": start,
            "end_at": end,
            "lat": EV_LAT,
            "lng": EV_LNG,
        })
        assert r.status_code == 400, r.text

    def test_invalid_type_rejected(self):
        r = _client("pe_user_a").post(f"{API}/parish-events", json={
            "type": "vandalism_meetup",
            "title": "TEST_Invalid",
            "start_at": _future_iso(1),
            "lat": EV_LAT,
            "lng": EV_LNG,
        })
        assert r.status_code == 422, r.text

    def test_flag_nonexistent(self):
        r = _client("pe_user_a").post(
            f"{API}/parish-events/pe_does_not_exist/flag", json={},
        )
        assert r.status_code == 404, r.text

    def test_invalid_event_type_filter(self):
        r = _client("pe_user_a").get(
            f"{API}/parish-events",
            params={"church_id": "osm:1234", "event_type": "nope"},
        )
        assert r.status_code == 400, r.status_code
