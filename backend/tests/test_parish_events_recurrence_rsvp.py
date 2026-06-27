"""Tests for the new Parish Events recurrence + RSVP features (iter 72).

Covers:
  * POST /parish-events: recurrence in {once,weekly,biweekly,monthly,annually}; invalid -> 422.
  * GET /parish-events: weekly recurring base produces multiple expanded occurrences
    with recurrence_label and occurrence_key.
  * POST /parish-events/{id}/rsvp: toggles, returns {going, going_count}.
  * GET /parish-events/mine/attending: returns user's attended events as occurrences.
  * _shape includes going & going_count on list items.
"""
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

_UA = "per_user_a"
_UB = "per_user_b"
_TOKENS = {_UA: f"per_tok_a_{uuid.uuid4().hex[:8]}", _UB: f"per_tok_b_{uuid.uuid4().hex[:8]}"}


@pytest.fixture(scope="module")
def mongo():
    cli = MongoClient(MONGO_URL)
    db = cli[DB_NAME]
    yield db
    cli.close()


@pytest.fixture(scope="module", autouse=True)
def seed_users(mongo):
    now = datetime.now(timezone.utc)
    for uid in (_UA, _UB):
        mongo.users.update_one(
            {"user_id": uid},
            {"$set": {"user_id": uid, "email": f"{uid}@t.app", "name": uid, "created_at": now}},
            upsert=True,
        )
        mongo.user_sessions.update_one(
            {"session_token": _TOKENS[uid]},
            {"$set": {"session_token": _TOKENS[uid], "user_id": uid,
                      "created_at": now,
                      "expires_at": now + timedelta(days=1)}},
            upsert=True,
        )
    mongo.parish_events.delete_many({"organizer_user_id": {"$in": [_UA, _UB]}})
    yield
    for uid in (_UA, _UB):
        mongo.user_sessions.delete_many({"user_id": uid})
        mongo.users.delete_many({"user_id": uid})
    mongo.parish_events.delete_many({"organizer_user_id": {"$in": [_UA, _UB]}})


def _client(uid: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_TOKENS[uid]}",
    })
    return s


EV_LAT = 40.7128
EV_LNG = -74.0060


def _future_iso(days_ahead: float = 3.0, hours: float = 0) -> str:
    dt = datetime.now(timezone.utc) + timedelta(days=days_ahead, hours=hours)
    return dt.isoformat()


# ============================================================
# Recurrence validation
# ============================================================
class TestRecurrenceValidation:
    @pytest.mark.parametrize("rec", ["once", "weekly", "biweekly", "monthly", "annually"])
    def test_valid_recurrence_accepted(self, rec):
        r = _client(_UA).post(f"{API}/parish-events", json={
            "type": "mass",
            "title": f"TEST_Rec_{rec}",
            "start_at": _future_iso(2),
            "lat": EV_LAT, "lng": EV_LNG,
            "recurrence": rec,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["recurrence"] == rec
        # _shape should include recurrence_label
        assert body.get("recurrence_label"), f"missing recurrence_label: {body}"
        # going + going_count default
        assert body["going"] is False
        assert body["going_count"] == 0
        # occurrence_key present
        assert "#" in (body.get("occurrence_key") or "")

    def test_invalid_recurrence_rejected(self):
        r = _client(_UA).post(f"{API}/parish-events", json={
            "type": "mass",
            "title": "TEST_BadRec",
            "start_at": _future_iso(2),
            "lat": EV_LAT, "lng": EV_LNG,
            "recurrence": "biennially",
        })
        assert r.status_code == 422, r.text


# ============================================================
# Recurrence expansion in list
# ============================================================
class TestRecurrenceExpansion:
    def test_weekly_event_expands_to_multiple_occurrences(self, mongo):
        # Clear unique geo area
        mongo.parish_events.delete_many({"organizer_user_id": _UA})
        start = _future_iso(1)
        r = _client(_UA).post(f"{API}/parish-events", json={
            "type": "adoration",
            "title": "TEST_WeeklyHolyHour",
            "start_at": start,
            "end_at": (datetime.fromisoformat(start) + timedelta(hours=1)).isoformat(),
            "lat": EV_LAT, "lng": EV_LNG,
            "recurrence": "weekly",
        })
        assert r.status_code == 200, r.text
        base_id = r.json()["id"]

        # List within 30-day window
        lst = _client(_UA).get(f"{API}/parish-events", params={
            "lat": EV_LAT, "lng": EV_LNG, "radius_m": 20000, "days": 30,
        })
        assert lst.status_code == 200, lst.text
        items = [i for i in lst.json()["items"] if i["id"] == base_id]
        # weekly across 30 days ~> 4-5 occurrences
        assert len(items) >= 4, f"expected >=4 weekly occurrences, got {len(items)}: {items}"
        # All share the base id but have distinct occurrence_keys
        keys = {i["occurrence_key"] for i in items}
        assert len(keys) == len(items), "occurrence_keys must be unique"
        # All carry recurrence + label
        assert all(i["recurrence"] == "weekly" for i in items)
        assert all(i["recurrence_label"] for i in items)

    def test_once_event_single_occurrence(self):
        r = _client(_UA).post(f"{API}/parish-events", json={
            "type": "talk",
            "title": "TEST_OneTime",
            "start_at": _future_iso(3),
            "lat": EV_LAT, "lng": EV_LNG,
            "recurrence": "once",
        })
        assert r.status_code == 200
        eid = r.json()["id"]
        lst = _client(_UA).get(f"{API}/parish-events", params={
            "lat": EV_LAT, "lng": EV_LNG, "radius_m": 20000, "days": 30,
        })
        items = [i for i in lst.json()["items"] if i["id"] == eid]
        assert len(items) == 1, f"once event should expand to 1 occurrence, got {len(items)}"


# ============================================================
# RSVP toggle + attending
# ============================================================
class TestRSVPAndAttending:
    def test_rsvp_toggle_and_count(self, mongo):
        # Fresh single event
        r = _client(_UA).post(f"{API}/parish-events", json={
            "type": "social",
            "title": "TEST_RSVPFest",
            "start_at": _future_iso(5),
            "lat": EV_LAT, "lng": EV_LNG,
        })
        assert r.status_code == 200, r.text
        eid = r.json()["id"]

        # B RSVPs - going True, count 1
        rb = _client(_UB).post(f"{API}/parish-events/{eid}/rsvp")
        assert rb.status_code == 200, rb.text
        assert rb.json() == {"going": True, "going_count": 1}

        # A RSVPs as organiser - going True, count 2
        ra = _client(_UA).post(f"{API}/parish-events/{eid}/rsvp")
        assert ra.status_code == 200
        assert ra.json()["going"] is True
        assert ra.json()["going_count"] == 2

        # B toggles off
        rb2 = _client(_UB).post(f"{API}/parish-events/{eid}/rsvp")
        assert rb2.status_code == 200
        assert rb2.json() == {"going": False, "going_count": 1}

        # List shows going state per viewer
        lst_b = _client(_UB).get(f"{API}/parish-events", params={
            "lat": EV_LAT, "lng": EV_LNG, "radius_m": 20000, "days": 30,
        })
        item_b = next((i for i in lst_b.json()["items"] if i["id"] == eid), None)
        assert item_b is not None
        assert item_b["going"] is False
        assert item_b["going_count"] == 1

        lst_a = _client(_UA).get(f"{API}/parish-events", params={
            "lat": EV_LAT, "lng": EV_LNG, "radius_m": 20000, "days": 30,
        })
        item_a = next((i for i in lst_a.json()["items"] if i["id"] == eid), None)
        assert item_a is not None
        assert item_a["going"] is True
        assert item_a["going_count"] == 1

    def test_rsvp_nonexistent_returns_404(self):
        r = _client(_UA).post(f"{API}/parish-events/pe_nope/rsvp")
        assert r.status_code == 404

    def test_mine_attending_returns_user_events_expanded(self, mongo):
        # B attends a NEW weekly event; verify /mine/attending expands & filters to B's.
        start = _future_iso(2)
        r = _client(_UA).post(f"{API}/parish-events", json={
            "type": "adoration",
            "title": "TEST_AttendingWeekly",
            "start_at": start,
            "lat": EV_LAT, "lng": EV_LNG,
            "recurrence": "weekly",
        })
        assert r.status_code == 200
        eid = r.json()["id"]

        rsvp = _client(_UB).post(f"{API}/parish-events/{eid}/rsvp")
        assert rsvp.status_code == 200
        assert rsvp.json()["going"] is True

        att = _client(_UB).get(f"{API}/parish-events/mine/attending", params={"days": 60})
        assert att.status_code == 200, att.text
        items = att.json()["items"]
        assert isinstance(items, list)
        for it in items:
            assert it["going"] is True, f"non-going leaked into attending: {it}"
        # Multiple occurrences of the weekly event
        mine = [i for i in items if i["id"] == eid]
        assert len(mine) >= 4, f"weekly attending should expand: got {len(mine)}"
        keys = {i["occurrence_key"] for i in mine}
        assert len(keys) == len(mine)

        # User A (who hasn't RSVPed) sees nothing for this event
        att_a = _client(_UA).get(f"{API}/parish-events/mine/attending", params={"days": 60})
        assert att_a.status_code == 200
        assert all(i["id"] != eid for i in att_a.json()["items"])
