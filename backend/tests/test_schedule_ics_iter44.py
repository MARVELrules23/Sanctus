"""Iter44 — Schedule calendar export (.ics) backend tests.

Covers:
- GET /api/schedule/ics/{token}.ics is PUBLIC (no auth) and returns text/calendar
- 404 for unknown token
- VCALENDAR/VEVENT shape, VALARM present
- Weekly item -> RRULE:FREQ=WEEKLY;BYDAY=... and BYDAY order matches days_of_week
- One-off item -> no RRULE, single DTSTART
- Every schedule item has ics_token (new items + lazy on list for older items without one)
"""
import os
import re
import pytest
import requests
from pymongo import MongoClient

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or "https://divine-office.preview.emergentagent.com"
).rstrip("/")

ADMIN_TOKEN = "test_sched_admin_001"
USER_ID = "user_ade7a898e281"

_BYDAY = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"]


def _client(token=None):
    s = requests.Session()
    s.headers["Content-Type"] = "application/json"
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _client(ADMIN_TOKEN)


@pytest.fixture(scope="module")
def anon():
    return _client()


@pytest.fixture(scope="module")
def created_items(admin):
    """Create one weekly + one once item; clean up after."""
    weekly = admin.post(f"{BASE_URL}/api/schedule", json={
        "kind": "workout",
        "title": "TEST_ICS_Weekly",
        "note": "Test weekly export; with commas, and ;semis",
        "recurrence": "weekly",
        "days_of_week": [1, 3, 5],
        "time": "08:00",
    })
    assert weekly.status_code == 200, weekly.text
    once = admin.post(f"{BASE_URL}/api/schedule", json={
        "kind": "meal",
        "title": "TEST_ICS_Once",
        "recurrence": "once",
        "date": "2026-06-25",
        "time": "18:30",
    })
    assert once.status_code == 200, once.text
    items = {"weekly": weekly.json(), "once": once.json()}
    yield items
    for it in items.values():
        try:
            admin.delete(f"{BASE_URL}/api/schedule/{it['id']}")
        except Exception:
            pass


# ---------------- ics_token presence ----------------
class TestIcsTokenPresence:
    def test_create_returns_ics_token(self, created_items):
        for it in created_items.values():
            tok = it.get("ics_token")
            assert tok and isinstance(tok, str) and len(tok) >= 16, f"Bad ics_token: {it}"

    def test_list_items_have_ics_token(self, admin, created_items):
        r = admin.get(f"{BASE_URL}/api/schedule")
        assert r.status_code == 200
        items = r.json()["items"]
        for it in items:
            assert it.get("ics_token"), f"Missing ics_token on listed item: {it.get('id')}"

    def test_lazy_token_for_older_item(self, admin):
        """Insert an item directly without ics_token; list endpoint must lazily add one."""
        mc = MongoClient("mongodb://localhost:27017")
        db = mc["sanctus_db"]
        legacy_id = "sch_legacy_ics_test1"
        db.schedule_items.delete_one({"id": legacy_id})
        db.schedule_items.insert_one({
            "id": legacy_id,
            "user_id": USER_ID,
            "kind": "custom",
            "title": "TEST_ICS_Legacy",
            "recurrence": "weekly",
            "days_of_week": [2],
            "time": None,
            "notify": False,
            "notif_ids": [],
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:00:00+00:00",
        })
        try:
            r = admin.get(f"{BASE_URL}/api/schedule")
            assert r.status_code == 200
            match = [i for i in r.json()["items"] if i["id"] == legacy_id]
            assert match, "legacy item not listed"
            assert match[0].get("ics_token"), "ics_token not assigned lazily"
            # Verify it's persisted
            doc = db.schedule_items.find_one({"id": legacy_id})
            assert doc.get("ics_token"), "ics_token not persisted in DB"
        finally:
            db.schedule_items.delete_one({"id": legacy_id})


# ---------------- public access + 404 ----------------
class TestPublicAccess:
    def test_ics_endpoint_is_public(self, anon, created_items):
        tok = created_items["weekly"]["ics_token"]
        r = anon.get(f"{BASE_URL}/api/schedule/ics/{tok}.ics")
        assert r.status_code == 200, r.text
        ct = r.headers.get("content-type", "")
        assert "text/calendar" in ct.lower(), f"bad content-type: {ct}"
        # Content-Disposition attachment with .ics
        cd = r.headers.get("content-disposition", "")
        assert ".ics" in cd.lower()

    def test_ics_unknown_token_404(self, anon):
        r = anon.get(f"{BASE_URL}/api/schedule/ics/nonexistent_token_xyz.ics")
        assert r.status_code == 404, r.text


# ---------------- VCALENDAR content ----------------
class TestIcsContent:
    def test_weekly_has_rrule(self, anon, created_items):
        tok = created_items["weekly"]["ics_token"]
        body = anon.get(f"{BASE_URL}/api/schedule/ics/{tok}.ics").text
        assert "BEGIN:VCALENDAR" in body and "END:VCALENDAR" in body
        assert "BEGIN:VEVENT" in body and "END:VEVENT" in body
        assert "BEGIN:VALARM" in body and "END:VALARM" in body
        # Weekly has RRULE w/ BYDAY for [1,3,5] -> MO,WE,FR
        m = re.search(r"RRULE:FREQ=WEEKLY;BYDAY=([A-Z,]+)", body)
        assert m, f"No RRULE in body:\n{body}"
        byday = m.group(1)
        assert byday == "MO,WE,FR", f"Unexpected BYDAY: {byday}"
        # SUMMARY contains title; DTSTART timed (no VALUE=DATE)
        assert "SUMMARY:TEST_ICS_Weekly" in body
        # DTSTART must include a 'T' time component (timed event)
        m2 = re.search(r"DTSTART:(\d{8}T\d{6})", body)
        assert m2, "Expected timed DTSTART for weekly with time=08:00"

    def test_once_no_rrule(self, anon, created_items):
        tok = created_items["once"]["ics_token"]
        body = anon.get(f"{BASE_URL}/api/schedule/ics/{tok}.ics").text
        assert "BEGIN:VCALENDAR" in body
        assert "RRULE" not in body, "One-off must not have RRULE"
        # one-off on 2026-06-25 with time 18:30 -> DTSTART:20260625T183000
        assert "DTSTART:20260625T183000" in body, body
        assert "SUMMARY:TEST_ICS_Once" in body

    def test_ics_text_escaping(self, anon, created_items):
        """Commas & semicolons in note must be escaped per RFC 5545."""
        tok = created_items["weekly"]["ics_token"]
        body = anon.get(f"{BASE_URL}/api/schedule/ics/{tok}.ics").text
        # Note had: "with commas, and ;semis"
        # Find DESCRIPTION line
        for line in body.splitlines():
            if line.startswith("DESCRIPTION:"):
                # Raw commas/semicolons must not appear unescaped
                assert "\\," in line, f"comma not escaped: {line}"
                assert "\\;" in line, f"semicolon not escaped: {line}"
                break
        else:
            pytest.fail("No DESCRIPTION line in ics output")
