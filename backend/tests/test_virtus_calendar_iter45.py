"""
Iteration 45 — Virtus per-day calendar + journal backend tests.

Verifies:
- POST /api/virtues/plans (creates plan w/ checkins={}, journal={})
- POST /api/virtues/plans/{id}/checkin (toggle per-day; per-date isolation)
- PUT  /api/virtues/plans/{id}/journal (persists per-date)
- GET  /api/virtues/plans/{id} returns checkins, journal, days_logged,
        today, completed(=today count), total
- DELETE /api/virtues/plans/{id}
- Auth required for plan endpoints
- 400 on bad date format
- 404 on bad goal id
"""
import os
import pytest
import requests
from datetime import date, timedelta

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_premium_2453a541f1e0982d"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    })
    return s


@pytest.fixture(scope="module")
def plan(api):
    # Create a plan with 1 virtue so AI returns quickly. Use 7 days.
    r = api.post(f"{BASE_URL}/api/virtues/plans",
                 json={"virtue_slugs": ["patience"], "days": 7, "note": "TEST_ITER45"})
    assert r.status_code == 200, f"create plan failed: {r.status_code} {r.text}"
    p = r.json()
    assert p["id"].startswith("vp_")
    assert p["checkins"] == {}
    assert p["journal"] == {}
    assert p["total"] >= 1
    assert "today" in p and "start_date" in p and "end_date" in p
    yield p
    # cleanup
    api.delete(f"{BASE_URL}/api/virtues/plans/{p['id']}")


class TestVirtusCalendar:

    def test_auth_required(self):
        r = requests.get(f"{BASE_URL}/api/virtues/plans")
        assert r.status_code in (401, 403)

    def test_get_plan(self, api, plan):
        r = api.get(f"{BASE_URL}/api/virtues/plans/{plan['id']}")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == plan["id"]
        for k in ("checkins", "journal", "days_logged", "today", "completed", "total"):
            assert k in body, f"missing key {k}"

    def test_checkin_per_date_isolation(self, api, plan):
        goal_id = plan["goals"][0]["id"]
        today = plan["today"]
        # use yesterday (still inside start_date..end_date since start=today)
        # actually start_date == today, so use today and tomorrow-1? Use today and (today+1) future.
        # Tomorrow could be in plan range (end = start+7). Check today vs tomorrow.
        tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()

        # check-in today
        r = api.post(f"{BASE_URL}/api/virtues/plans/{plan['id']}/checkin",
                     json={"date": today, "goal_id": goal_id})
        assert r.status_code == 200, r.text
        body = r.json()
        assert goal_id in body["checkins"].get(today, [])
        assert goal_id not in body["checkins"].get(tomorrow, [])
        assert body["completed"] == len(body["checkins"].get(today, []))
        assert body["days_logged"] >= 1

        # check-in tomorrow
        r = api.post(f"{BASE_URL}/api/virtues/plans/{plan['id']}/checkin",
                     json={"date": tomorrow, "goal_id": goal_id})
        assert r.status_code == 200
        body = r.json()
        # day A still checked, day B newly checked = isolation
        assert goal_id in body["checkins"].get(today, [])
        assert goal_id in body["checkins"].get(tomorrow, [])

        # toggle off today
        r = api.post(f"{BASE_URL}/api/virtues/plans/{plan['id']}/checkin",
                     json={"date": today, "goal_id": goal_id})
        assert r.status_code == 200
        body = r.json()
        assert goal_id not in body["checkins"].get(today, [])
        assert goal_id in body["checkins"].get(tomorrow, [])  # other day untouched

    def test_checkin_bad_date(self, api, plan):
        goal_id = plan["goals"][0]["id"]
        r = api.post(f"{BASE_URL}/api/virtues/plans/{plan['id']}/checkin",
                     json={"date": "not-a-date", "goal_id": goal_id})
        assert r.status_code == 400

    def test_checkin_bad_goal(self, api, plan):
        r = api.post(f"{BASE_URL}/api/virtues/plans/{plan['id']}/checkin",
                     json={"date": plan["today"], "goal_id": "g_doesnotexist"})
        assert r.status_code == 404

    def test_journal_per_date(self, api, plan):
        today = plan["today"]
        tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()

        r = api.put(f"{BASE_URL}/api/virtues/plans/{plan['id']}/journal",
                    json={"date": today, "text": "TEST_today reflection"})
        assert r.status_code == 200
        body = r.json()
        assert body["journal"].get(today) == "TEST_today reflection"

        r = api.put(f"{BASE_URL}/api/virtues/plans/{plan['id']}/journal",
                    json={"date": tomorrow, "text": "TEST_tomorrow reflection"})
        assert r.status_code == 200
        body = r.json()
        assert body["journal"].get(today) == "TEST_today reflection"
        assert body["journal"].get(tomorrow) == "TEST_tomorrow reflection"

        # clear today -> should remove key
        r = api.put(f"{BASE_URL}/api/virtues/plans/{plan['id']}/journal",
                    json={"date": today, "text": ""})
        assert r.status_code == 200
        body = r.json()
        assert today not in body["journal"]
        assert body["journal"].get(tomorrow) == "TEST_tomorrow reflection"

    def test_journal_bad_date(self, api, plan):
        r = api.put(f"{BASE_URL}/api/virtues/plans/{plan['id']}/journal",
                    json={"date": "bad", "text": "x"})
        assert r.status_code == 400

    def test_get_plan_persistence(self, api, plan):
        # after the above test cases, re-fetch and confirm persisted journal
        r = api.get(f"{BASE_URL}/api/virtues/plans/{plan['id']}")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body["journal"], dict)
        # tomorrow journal should still be there
        today = plan["today"]
        tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
        assert body["journal"].get(tomorrow) == "TEST_tomorrow reflection"
