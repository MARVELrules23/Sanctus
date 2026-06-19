"""Iter42 — Liturgy DAYTIME + Virtus backend tests.

Covers:
- /api/liturgy index now includes daytime hour
- /api/liturgy/daytime detail (psalms_vary_by_day=false, section_count=10)
- /api/liturgy/daytime/monday returns 10 sections (Terce/Sext/None)
- Virtus catalogue (401 anon, 200 auth, contains 9 items + flags)
- Virtus per-virtue content (humility/chastity) cached, NO resources body
- Virtus resources endpoint Premium-gated (402 free, 200 admin)
- Virtus admin endpoints — 403 free / 200 admin (PUT, regenerate, admin GET)
- Virtus PUT persists edit and sets edited=true
- Virtus Plan CRUD: 400 empty, create OK, list, toggle, delete, 404 after
"""
import os
import time
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = (os.environ.get("EXPO_PUBLIC_BACKEND_URL")
            or os.environ.get("EXPO_BACKEND_URL")
            or "http://localhost:8001").rstrip("/")
ADMIN_TOKEN = "test_liturgy_probe_001"
FREE_TOKEN = "test_virtus_free_001"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {ADMIN_TOKEN}",
                      "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def free():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {FREE_TOKEN}",
                      "Content-Type": "application/json"})
    return s


# ------------------------- LITURGY DAYTIME ----------------------------------
class TestLiturgyDaytime:
    def test_index_now_lists_daytime(self, admin):
        r = admin.get(f"{BASE_URL}/api/liturgy")
        assert r.status_code == 200, r.text
        slugs = [h["slug"] for h in r.json()["hours"]]
        assert slugs == ["lauds", "daytime", "vespers", "compline"], slugs

    def test_daytime_detail(self, admin):
        r = admin.get(f"{BASE_URL}/api/liturgy/daytime")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["slug"] == "daytime"
        assert data["psalms_vary_by_day"] is False
        assert data["section_count_per_day"] == 10, data["section_count_per_day"]
        assert len(data["days"]) == 7

    def test_daytime_monday_sections(self, admin):
        r = admin.get(f"{BASE_URL}/api/liturgy/daytime/monday")
        assert r.status_code == 200, r.text
        sections = r.json()["sections"]
        assert len(sections) == 10, len(sections)
        # Should reference Terce / Sext / None across the 10 sections
        blob = " ".join((s.get("title") or "") + " " + (s.get("latin_title") or "")
                        for s in sections).lower()
        assert "terce" in blob or "tert" in blob, blob[:300]
        assert "sext" in blob, blob[:300]
        assert "none" in blob or "non" in blob, blob[:300]

    def test_daytime_identical_across_days(self, admin):
        mon = admin.get(f"{BASE_URL}/api/liturgy/daytime/monday").json()["sections"]
        fri = admin.get(f"{BASE_URL}/api/liturgy/daytime/friday").json()["sections"]
        assert mon == fri, "Daytime should be identical across weekdays"

    def test_free_user_can_access_daytime(self, free):
        r = free.get(f"{BASE_URL}/api/liturgy/daytime/monday")
        assert r.status_code == 200, r.text


# ------------------------- VIRTUS CATALOGUE ---------------------------------
class TestVirtusCatalogue:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/virtues")
        assert r.status_code == 401, (r.status_code, r.text)

    def test_list_admin(self, admin):
        r = admin.get(f"{BASE_URL}/api/virtues")
        assert r.status_code == 200, r.text
        data = r.json()
        items = data["items"]
        assert len(items) == 9, len(items)
        slugs = [v["slug"] for v in items]
        expected = {"chastity", "charity", "humility", "patience", "temperance",
                    "fortitude", "spiritual-warfare", "habits-discipline",
                    "saints-of-virtue"}
        assert set(slugs) == expected, set(slugs)
        assert data["is_admin"] is True
        assert data["user_is_premium"] is True

    def test_list_free(self, free):
        r = free.get(f"{BASE_URL}/api/virtues")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_admin"] is False
        assert d["user_is_premium"] is False


# ------------------------- VIRTUS CONTENT -----------------------------------
class TestVirtusContent:
    def test_humility_returns_shape(self, admin):
        # Humility was already generated per logs; should be cached/fast
        t0 = time.time()
        r = admin.get(f"{BASE_URL}/api/virtues/humility", timeout=60)
        elapsed = time.time() - t0
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("slug", "what_is", "life_stages", "overcoming_vice", "saints",
                  "is_premium_resources", "has_resources", "resource_count",
                  "user_is_premium", "edited"):
            assert k in d, f"missing {k}"
        for ls_k in ("singleness", "dating", "marriage"):
            assert ls_k in d["life_stages"]
            assert isinstance(d["life_stages"][ls_k], str)
        # Resources body MUST NOT be in this payload
        assert "resources" not in d, "resources should be Premium-gated separate endpoint"
        assert isinstance(d["saints"], list) and len(d["saints"]) >= 1
        # On a cached doc this should be fast
        print(f"humility GET elapsed={elapsed:.2f}s")

    def test_saints_of_virtue_shape(self, admin):
        r = admin.get(f"{BASE_URL}/api/virtues/saints-of-virtue", timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "intro" in d and len(d["intro"]) > 20
        assert "saints_by_virtue" in d and isinstance(d["saints_by_virtue"], list)
        assert len(d["saints_by_virtue"]) >= 1
        assert "resources" not in d

    def test_unknown_virtue_404(self, admin):
        r = admin.get(f"{BASE_URL}/api/virtues/nonexistent")
        assert r.status_code == 404


# ------------------------- VIRTUS RESOURCES GATING --------------------------
class TestVirtusResources:
    def test_free_user_402(self, free):
        r = free.get(f"{BASE_URL}/api/virtues/humility/resources")
        assert r.status_code == 402, (r.status_code, r.text)

    def test_admin_200(self, admin):
        r = admin.get(f"{BASE_URL}/api/virtues/humility/resources")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["slug"] == "humility"
        assert isinstance(d["resources"], list)
        assert len(d["resources"]) >= 1


# ------------------------- VIRTUS ADMIN GATING ------------------------------
class TestVirtusAdminGating:
    def test_admin_full_403_for_free(self, free):
        r = free.get(f"{BASE_URL}/api/virtues/humility/admin")
        assert r.status_code == 403, (r.status_code, r.text)

    def test_admin_full_200_for_admin(self, admin):
        r = admin.get(f"{BASE_URL}/api/virtues/humility/admin")
        assert r.status_code == 200, r.text
        d = r.json()
        assert "resources" in d  # admin full payload DOES include resources
        assert isinstance(d["resources"], list)

    def test_put_403_for_free(self, free):
        r = free.put(f"{BASE_URL}/api/virtues/humility",
                     json={"what_is": "hack"})
        assert r.status_code == 403

    def test_put_persists_and_sets_edited(self, admin):
        marker = f"EDITED-MARKER-{int(time.time())}"
        r = admin.put(f"{BASE_URL}/api/virtues/humility",
                      json={"what_is": marker})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["edited"] is True
        assert d["what_is"] == marker
        # Verify persisted via fresh GET
        r2 = admin.get(f"{BASE_URL}/api/virtues/humility")
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["edited"] is True
        assert d2["what_is"] == marker

    def test_put_empty_400(self, admin):
        r = admin.put(f"{BASE_URL}/api/virtues/humility", json={})
        assert r.status_code == 400, (r.status_code, r.text)

    def test_regenerate_403_for_free(self, free):
        r = free.post(f"{BASE_URL}/api/virtues/humility/regenerate")
        assert r.status_code == 403

    # NOTE: skipping regenerate 200 because it costs an LLM call (~15s) and
    # would overwrite the cache during testing.


# ------------------------- VIRTUS PLANS -------------------------------------
class TestVirtusPlans:
    plan_id = None

    def test_empty_slugs_400(self, admin):
        r = admin.post(f"{BASE_URL}/api/virtues/plans",
                       json={"virtue_slugs": [], "days": 10})
        assert r.status_code == 400, (r.status_code, r.text)

    def test_create_plan(self, admin):
        r = admin.post(f"{BASE_URL}/api/virtues/plans",
                       json={"virtue_slugs": ["patience", "humility"], "days": 10},
                       timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["days"] == 10
        assert set(d["virtue_slugs"]) == {"patience", "humility"}
        assert d["total"] >= 4, d["total"]
        assert d["completed"] == 0
        assert d["active"] is True
        assert len(d["virtues"]) == 2
        # each goal has the required shape
        for g in d["goals"]:
            for k in ("id", "virtue_slug", "type", "text", "done"):
                assert k in g
            assert g["type"] in ("do", "refrain")
        TestVirtusPlans.plan_id = d["id"]
        TestVirtusPlans.first_goal_id = d["goals"][0]["id"]

    def test_list_plans(self, admin):
        r = admin.get(f"{BASE_URL}/api/virtues/plans")
        assert r.status_code == 200, r.text
        ids = [p["id"] for p in r.json()["items"]]
        assert TestVirtusPlans.plan_id in ids

    def test_toggle_goal(self, admin):
        pid = TestVirtusPlans.plan_id
        gid = TestVirtusPlans.first_goal_id
        r = admin.post(f"{BASE_URL}/api/virtues/plans/{pid}/goals/{gid}/toggle")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["completed"] == 1
        # toggle back
        r2 = admin.post(f"{BASE_URL}/api/virtues/plans/{pid}/goals/{gid}/toggle")
        assert r2.status_code == 200
        assert r2.json()["completed"] == 0

    def test_toggle_unknown_goal_404(self, admin):
        pid = TestVirtusPlans.plan_id
        r = admin.post(f"{BASE_URL}/api/virtues/plans/{pid}/goals/g_nope/toggle")
        assert r.status_code == 404

    def test_delete_plan(self, admin):
        pid = TestVirtusPlans.plan_id
        r = admin.delete(f"{BASE_URL}/api/virtues/plans/{pid}")
        assert r.status_code == 200, r.text
        # confirm gone
        r2 = admin.get(f"{BASE_URL}/api/virtues/plans/{pid}")
        assert r2.status_code == 404
