"""Iter43 — Schedule feature backend tests.

Covers:
- Auth gating (401)
- CRUD: create weekly + once, list, update, delete (returns notif_ids)
- Validations (400): empty days_of_week, missing/invalid date, invalid time, empty title
- Day matching: GET /api/schedule/day/{date}
- Sources: active virtue plans + enrolled challenges
- PUT /notif-ids
"""
import os
import pytest
import requests
from datetime import date, timedelta

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or "https://divine-office.preview.emergentagent.com"
).rstrip("/")

ADMIN_TOKEN = "test_sched_admin_001"
FREE_TOKEN = "test_sched_free_001"


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
def free():
    return _client(FREE_TOKEN)


@pytest.fixture(scope="module")
def anon():
    return _client()


# ---------------- AUTH ----------------
class TestAuth:
    def test_list_requires_auth(self, anon):
        r = anon.get(f"{BASE_URL}/api/schedule")
        assert r.status_code == 401, r.text

    def test_create_requires_auth(self, anon):
        r = anon.post(f"{BASE_URL}/api/schedule", json={"title": "x", "recurrence": "weekly", "days_of_week": [1]})
        assert r.status_code == 401

    def test_day_requires_auth(self, anon):
        r = anon.get(f"{BASE_URL}/api/schedule/day/2026-06-25")
        assert r.status_code == 401

    def test_sources_requires_auth(self, anon):
        r = anon.get(f"{BASE_URL}/api/schedule/sources")
        assert r.status_code == 401


# ---------------- VALIDATIONS ----------------
class TestValidations:
    def test_weekly_empty_days(self, admin):
        r = admin.post(f"{BASE_URL}/api/schedule", json={
            "kind": "custom", "title": "no days", "recurrence": "weekly", "days_of_week": []
        })
        assert r.status_code == 400, r.text

    def test_once_missing_date(self, admin):
        r = admin.post(f"{BASE_URL}/api/schedule", json={
            "kind": "custom", "title": "no date", "recurrence": "once"
        })
        assert r.status_code == 400, r.text

    def test_once_invalid_date(self, admin):
        r = admin.post(f"{BASE_URL}/api/schedule", json={
            "kind": "custom", "title": "bad date", "recurrence": "once", "date": "06-25-2026"
        })
        assert r.status_code == 400, r.text

    def test_invalid_time(self, admin):
        r = admin.post(f"{BASE_URL}/api/schedule", json={
            "kind": "custom", "title": "bad time", "recurrence": "weekly",
            "days_of_week": [1], "time": "25:99"
        })
        assert r.status_code == 400, r.text

    def test_empty_title(self, admin):
        r = admin.post(f"{BASE_URL}/api/schedule", json={
            "kind": "custom", "title": "   ", "recurrence": "weekly", "days_of_week": [1]
        })
        assert r.status_code == 400, r.text


# ---------------- CRUD ----------------
class TestCRUD:
    created_ids = []

    @classmethod
    def teardown_class(cls):
        c = _client(ADMIN_TOKEN)
        for iid in cls.created_ids:
            try:
                c.delete(f"{BASE_URL}/api/schedule/{iid}")
            except Exception:
                pass

    def test_create_weekly(self, admin):
        r = admin.post(f"{BASE_URL}/api/schedule", json={
            "kind": "workout",
            "title": "TEST_Weekly_Lift",
            "recurrence": "weekly",
            "days_of_week": [1, 3, 5],
            "time": "08:00",
            "notify": True,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["id"].startswith("sch_")
        assert d["recurrence"] == "weekly"
        assert d["days_of_week"] == [1, 3, 5]
        assert d["time"] == "08:00"
        assert d["kind"] == "workout"
        assert d["title"] == "TEST_Weekly_Lift"
        assert d["notify"] is True
        assert d["icon"] and d["color"]
        TestCRUD.created_ids.append(d["id"])

    def test_create_once(self, admin):
        r = admin.post(f"{BASE_URL}/api/schedule", json={
            "kind": "meal",
            "title": "TEST_OneOff_Feast",
            "recurrence": "once",
            "date": "2026-06-25",
            "time": "18:30",
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["recurrence"] == "once"
        assert d["date"] == "2026-06-25"
        assert d["time"] == "18:30"
        TestCRUD.created_ids.append(d["id"])

    def test_list_contains_created(self, admin):
        r = admin.get(f"{BASE_URL}/api/schedule")
        assert r.status_code == 200
        items = r.json()["items"]
        ids = [i["id"] for i in items]
        for iid in TestCRUD.created_ids:
            assert iid in ids

    def test_update_item(self, admin):
        iid = TestCRUD.created_ids[0]
        r = admin.put(f"{BASE_URL}/api/schedule/{iid}", json={
            "kind": "workout",
            "title": "TEST_Weekly_Lift_v2",
            "recurrence": "weekly",
            "days_of_week": [2, 4],
            "time": "09:15",
            "notify": False,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["title"] == "TEST_Weekly_Lift_v2"
        assert d["days_of_week"] == [2, 4]
        assert d["time"] == "09:15"
        assert d["notify"] is False

        # Verify persistence via GET list
        r2 = admin.get(f"{BASE_URL}/api/schedule")
        match = [i for i in r2.json()["items"] if i["id"] == iid][0]
        assert match["title"] == "TEST_Weekly_Lift_v2"
        assert match["days_of_week"] == [2, 4]

    def test_notif_ids_endpoint(self, admin):
        iid = TestCRUD.created_ids[0]
        r = admin.put(f"{BASE_URL}/api/schedule/{iid}/notif-ids", json={
            "notif_ids": ["nid_a", "nid_b", "nid_c"]
        })
        assert r.status_code == 200, r.text
        assert r.json()["notif_ids"] == ["nid_a", "nid_b", "nid_c"]
        # Verify persisted
        items = admin.get(f"{BASE_URL}/api/schedule").json()["items"]
        match = [i for i in items if i["id"] == iid][0]
        assert match["notif_ids"] == ["nid_a", "nid_b", "nid_c"]

    def test_delete_returns_notif_ids(self, admin):
        # Create a throwaway item with notif_ids set
        r = admin.post(f"{BASE_URL}/api/schedule", json={
            "kind": "custom", "title": "TEST_DeleteMe",
            "recurrence": "weekly", "days_of_week": [0],
        })
        iid = r.json()["id"]
        admin.put(f"{BASE_URL}/api/schedule/{iid}/notif-ids", json={"notif_ids": ["xx", "yy"]})

        rd = admin.delete(f"{BASE_URL}/api/schedule/{iid}")
        assert rd.status_code == 200, rd.text
        body = rd.json()
        assert body["ok"] is True
        assert body["notif_ids"] == ["xx", "yy"]

        # Verify gone
        items = admin.get(f"{BASE_URL}/api/schedule").json()["items"]
        assert iid not in [i["id"] for i in items]


# ---------------- DAY MATCHING ----------------
class TestDayMatching:
    weekly_id = None
    once_id = None

    @classmethod
    def teardown_class(cls):
        c = _client(ADMIN_TOKEN)
        for iid in [cls.weekly_id, cls.once_id]:
            if iid:
                try:
                    c.delete(f"{BASE_URL}/api/schedule/{iid}")
                except Exception:
                    pass

    def test_setup_items(self, admin):
        # weekly on Friday (5)
        r1 = admin.post(f"{BASE_URL}/api/schedule", json={
            "kind": "workout", "title": "TEST_DM_Friday", "recurrence": "weekly",
            "days_of_week": [5], "time": "07:00",
        })
        assert r1.status_code == 200
        TestDayMatching.weekly_id = r1.json()["id"]

        # one-off on a specific date (let's pick a Wednesday: 2026-06-24 is Wed)
        r2 = admin.post(f"{BASE_URL}/api/schedule", json={
            "kind": "meal", "title": "TEST_DM_OneOff", "recurrence": "once",
            "date": "2026-06-24",
        })
        assert r2.status_code == 200
        TestDayMatching.once_id = r2.json()["id"]

    def test_day_matches_weekly_friday(self, admin):
        # 2026-06-26 is a Friday
        r = admin.get(f"{BASE_URL}/api/schedule/day/2026-06-26")
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        titles = [i["title"] for i in items]
        assert "TEST_DM_Friday" in titles
        assert "TEST_DM_OneOff" not in titles  # not on a Friday

    def test_day_matches_once_date(self, admin):
        r = admin.get(f"{BASE_URL}/api/schedule/day/2026-06-24")
        assert r.status_code == 200
        titles = [i["title"] for i in r.json()["items"]]
        assert "TEST_DM_OneOff" in titles

    def test_day_excludes_nonmatching(self, admin):
        # 2026-06-23 is Tuesday — neither item should appear
        r = admin.get(f"{BASE_URL}/api/schedule/day/2026-06-23")
        titles = [i["title"] for i in r.json()["items"]]
        assert "TEST_DM_Friday" not in titles
        assert "TEST_DM_OneOff" not in titles

    def test_timed_sorted_before_allday(self, admin):
        # Add an all-day weekly on Friday + a timed weekly on Friday
        r1 = admin.post(f"{BASE_URL}/api/schedule", json={
            "kind": "custom", "title": "TEST_AllDay_Fri", "recurrence": "weekly",
            "days_of_week": [5],
        })
        r2 = admin.post(f"{BASE_URL}/api/schedule", json={
            "kind": "custom", "title": "TEST_Timed_Fri", "recurrence": "weekly",
            "days_of_week": [5], "time": "06:00",
        })
        try:
            items = admin.get(f"{BASE_URL}/api/schedule/day/2026-06-26").json()["items"]
            titles = [i["title"] for i in items]
            # All timed items come before any all-day item
            timed_idxs = [i for i, t in enumerate(items) if t.get("time")]
            allday_idxs = [i for i, t in enumerate(items) if not t.get("time")]
            if timed_idxs and allday_idxs:
                assert max(timed_idxs) < min(allday_idxs)
            assert titles.index("TEST_Timed_Fri") < titles.index("TEST_AllDay_Fri")
        finally:
            admin.delete(f"{BASE_URL}/api/schedule/{r1.json()['id']}")
            admin.delete(f"{BASE_URL}/api/schedule/{r2.json()['id']}")

    def test_day_bad_date(self, admin):
        r = admin.get(f"{BASE_URL}/api/schedule/day/not-a-date")
        assert r.status_code == 400


# ---------------- SOURCES ----------------
class TestSources:
    def test_sources_shape(self, admin):
        r = admin.get(f"{BASE_URL}/api/schedule/sources")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "virtue_plans" in body and "challenges" in body
        assert isinstance(body["virtue_plans"], list)
        assert isinstance(body["challenges"], list)
        # Each plan should have ref_id + title
        for p in body["virtue_plans"]:
            assert "ref_id" in p and "title" in p
        for c in body["challenges"]:
            assert "ref_slug" in c and "title" in c

    def test_sources_active_only(self, admin):
        r = admin.get(f"{BASE_URL}/api/schedule/sources")
        today = date.today().isoformat()
        for p in r.json()["virtue_plans"]:
            # If end_date present, must be >= today
            if p.get("end_date"):
                assert p["end_date"] >= today, f"Expired plan in sources: {p}"

    def test_sources_free_user(self, free):
        r = free.get(f"{BASE_URL}/api/schedule/sources")
        assert r.status_code == 200
        # Free user may have no enrollments/plans; just confirm shape
        body = r.json()
        assert isinstance(body["virtue_plans"], list)
        assert isinstance(body["challenges"], list)
