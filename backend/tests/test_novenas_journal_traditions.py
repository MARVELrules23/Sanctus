"""Iteration 70 tests:
   - Multiple-active novenas, per-slug start/stop/complete
   - Intentions journal CRUD + persistence after stop
   - Companion daily_traditions field
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_feat_aug25"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

SLUG_A = "st-joseph"
SLUG_B = "st-jude"
SLUG_C = "st-therese-little-flower"
START_DATE = "2026-01-10"


@pytest.fixture(scope="module", autouse=True)
def cleanup_state():
    """Stop any pre-existing actives & clear journal entries before/after run."""
    for slug in [SLUG_A, SLUG_B, SLUG_C]:
        requests.post(f"{BASE_URL}/api/novenas/{slug}/stop", headers=HEADERS, timeout=20)
        try:
            j = requests.get(f"{BASE_URL}/api/novenas/{slug}/journal", headers=HEADERS, timeout=20).json()
            for it in j.get("items", []):
                requests.delete(f"{BASE_URL}/api/novenas/{slug}/journal/{it['id']}", headers=HEADERS, timeout=20)
        except Exception:
            pass
    yield
    for slug in [SLUG_A, SLUG_B, SLUG_C]:
        requests.post(f"{BASE_URL}/api/novenas/{slug}/stop", headers=HEADERS, timeout=20)
        try:
            j = requests.get(f"{BASE_URL}/api/novenas/{slug}/journal", headers=HEADERS, timeout=20).json()
            for it in j.get("items", []):
                requests.delete(f"{BASE_URL}/api/novenas/{slug}/journal/{it['id']}", headers=HEADERS, timeout=20)
        except Exception:
            pass


# ---------- Multiple-active novenas ---------- #
class TestMultipleActiveNovenas:
    def test_start_two_concurrent(self):
        r1 = requests.post(f"{BASE_URL}/api/novenas/{SLUG_A}/start",
                           json={"start_date": START_DATE}, headers=HEADERS, timeout=20)
        assert r1.status_code == 200, r1.text
        assert r1.json()["slug"] == SLUG_A and r1.json()["status"] == "active"

        r2 = requests.post(f"{BASE_URL}/api/novenas/{SLUG_B}/start",
                           json={"start_date": START_DATE}, headers=HEADERS, timeout=20)
        assert r2.status_code == 200, f"Second start should not 409: {r2.text}"
        assert r2.json()["slug"] == SLUG_B and r2.json()["status"] == "active"

    def test_list_returns_both_actives(self):
        r = requests.get(f"{BASE_URL}/api/novenas", headers=HEADERS, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and "actives" in body
        slugs = {a["slug"] for a in body["actives"]}
        assert SLUG_A in slugs and SLUG_B in slugs, f"Expected both actives, got {slugs}"

    def test_active_endpoint_embeds_catalog(self):
        r = requests.get(f"{BASE_URL}/api/novenas/active", headers=HEADERS, timeout=20)
        assert r.status_code == 200
        actives = r.json()["actives"]
        slugs = {a["slug"] for a in actives}
        assert SLUG_A in slugs and SLUG_B in slugs
        for a in actives:
            assert "novena" in a and a["novena"]["slug"] == a["slug"]
            assert a["novena"].get("name")

    def test_restart_same_slug_replaces_only_that(self):
        # Start st-joseph again with different start date
        r = requests.post(f"{BASE_URL}/api/novenas/{SLUG_A}/start",
                          json={"start_date": "2026-02-01"}, headers=HEADERS, timeout=20)
        assert r.status_code == 200
        # Both should still be active, st-joseph with the new date
        r2 = requests.get(f"{BASE_URL}/api/novenas", headers=HEADERS, timeout=30).json()
        actives = {a["slug"]: a for a in r2["actives"]}
        assert SLUG_A in actives and SLUG_B in actives
        assert actives[SLUG_A]["start_date"] == "2026-02-01"
        # No duplicate
        only_a = [a for a in r2["actives"] if a["slug"] == SLUG_A]
        assert len(only_a) == 1

    def test_per_slug_stop_only_marks_that(self):
        r = requests.post(f"{BASE_URL}/api/novenas/{SLUG_A}/stop", headers=HEADERS, timeout=20)
        assert r.status_code == 200
        body = requests.get(f"{BASE_URL}/api/novenas", headers=HEADERS, timeout=30).json()
        slugs = {a["slug"] for a in body["actives"]}
        assert SLUG_A not in slugs, "st-joseph should no longer be active"
        assert SLUG_B in slugs, "st-jude should remain active"

    def test_complete_day_per_slug(self):
        r = requests.post(f"{BASE_URL}/api/novenas/{SLUG_B}/complete-day",
                          json={"day": 1}, headers=HEADERS, timeout=20)
        assert r.status_code == 200
        assert 1 in r.json()["completed_days"]

    def test_complete_day_out_of_range(self):
        r = requests.post(f"{BASE_URL}/api/novenas/{SLUG_B}/complete-day",
                          json={"day": 10}, headers=HEADERS, timeout=20)
        assert r.status_code == 400
        r2 = requests.post(f"{BASE_URL}/api/novenas/{SLUG_B}/complete-day",
                           json={"day": 0}, headers=HEADERS, timeout=20)
        assert r2.status_code == 400


# ---------- Journal ---------- #
class TestJournal:
    created_ids = []

    def test_unknown_slug_returns_404(self):
        r = requests.get(f"{BASE_URL}/api/novenas/does-not-exist-xyz/journal", headers=HEADERS, timeout=20)
        assert r.status_code == 404
        r2 = requests.post(f"{BASE_URL}/api/novenas/does-not-exist-xyz/journal",
                           json={"text": "abc"}, headers=HEADERS, timeout=20)
        assert r2.status_code == 404

    def test_empty_text_400(self):
        r = requests.post(f"{BASE_URL}/api/novenas/{SLUG_C}/journal",
                          json={"text": "   "}, headers=HEADERS, timeout=20)
        assert r.status_code == 400

    def test_add_two_entries(self):
        for text in ["TEST_for my mother's healing", "TEST_for peace at work"]:
            r = requests.post(f"{BASE_URL}/api/novenas/{SLUG_C}/journal",
                              json={"text": text}, headers=HEADERS, timeout=20)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["text"] == text
            assert "id" in body and "created_at" in body
            TestJournal.created_ids.append(body["id"])

    def test_get_journal_newest_first(self):
        r = requests.get(f"{BASE_URL}/api/novenas/{SLUG_C}/journal", headers=HEADERS, timeout=20)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 2
        # newest first => created_at descending
        for i in range(len(items) - 1):
            assert items[i]["created_at"] >= items[i + 1]["created_at"]

    def test_journal_persists_after_stop(self):
        # Start the novena, then stop it, journal should remain.
        requests.post(f"{BASE_URL}/api/novenas/{SLUG_C}/start",
                      json={"start_date": START_DATE}, headers=HEADERS, timeout=20)
        requests.post(f"{BASE_URL}/api/novenas/{SLUG_C}/stop", headers=HEADERS, timeout=20)
        r = requests.get(f"{BASE_URL}/api/novenas/{SLUG_C}/journal", headers=HEADERS, timeout=20)
        assert r.status_code == 200
        ids = {it["id"] for it in r.json()["items"]}
        for cid in TestJournal.created_ids:
            assert cid in ids, "Journal entries must persist across stop"

    def test_delete_entry(self):
        if not TestJournal.created_ids:
            pytest.skip("nothing to delete")
        eid = TestJournal.created_ids[0]
        r = requests.delete(f"{BASE_URL}/api/novenas/{SLUG_C}/journal/{eid}",
                            headers=HEADERS, timeout=20)
        assert r.status_code == 200
        items = requests.get(f"{BASE_URL}/api/novenas/{SLUG_C}/journal",
                             headers=HEADERS, timeout=20).json()["items"]
        assert eid not in {it["id"] for it in items}


# ---------- Companion daily_traditions ---------- #
class TestCompanionDailyTraditions:
    @pytest.mark.parametrize("slug", ["st-joseph", "blessed-virgin-mary", "padre-pio", "guardian-angel"])
    def test_daily_traditions_present(self, slug):
        r = requests.get(f"{BASE_URL}/api/companions/{slug}", headers=HEADERS, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "daily_traditions" in body, f"missing daily_traditions for {slug}"
        dt = body["daily_traditions"]
        assert isinstance(dt, list) and len(dt) >= 1, f"empty daily_traditions for {slug}"
        for item in dt:
            assert "title" in item and item["title"]
            assert "body" in item and item["body"]
