"""Iteration 90: Family companions CRUD + companion options + coloring-pages sanity.

Covers backend endpoints backing the new Family tab UI:
- GET /api/family/members
- POST /api/family/members  {name, companion_slug}
- DELETE /api/family/members/{id}
- GET /api/companions  (options list)
- GET /api/coloring-pages (used by the share/canvas screen)
- GET /api/family/today   (Family screen top-level payload)
- GET /api/library/books/<slug>  (deep-links from For Children / For Parents tiles)
"""
import os
import time
import pytest
import requests

BASE = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or "https://divine-office.preview.emergentagent.com"
BASE = BASE.rstrip("/")
TOKEN = "test_feat_aug25"

CHILDREN_SLUGS = [
    "bible-stories-for-little-souls",
    "little-saints-for-little-hearts",
    "the-holy-mass-for-little-ones",
]
PARENT_SLUGS = [
    "parents-guide-to-the-mass",
    "parents-guide-to-confession",
    "teaching-your-child-the-faith",
    "humanae-vitae",
]


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    })
    return s


# --- companion options ---
class TestCompanions:
    def test_companions_list(self, api):
        r = api.get(f"{BASE}/api/companions", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        arr = data if isinstance(data, list) else (data.get("items") or data.get("companions") or [])
        assert isinstance(arr, list) and len(arr) > 0
        first = arr[0]
        assert "slug" in first and "name" in first


# --- family members CRUD ---
class TestFamilyMembers:
    created_id: str = ""
    picked_slug: str = ""

    def test_00_pick_companion(self, api):
        r = api.get(f"{BASE}/api/companions", timeout=20)
        assert r.status_code == 200
        arr = r.json()
        arr = arr if isinstance(arr, list) else (arr.get("items") or arr.get("companions") or [])
        TestFamilyMembers.picked_slug = arr[0]["slug"]
        assert TestFamilyMembers.picked_slug

    def test_01_list_initial(self, api):
        r = api.get(f"{BASE}/api/family/members", timeout=20)
        assert r.status_code == 200, r.text
        assert isinstance(r.json().get("items"), list)

    def test_02_add_member(self, api):
        payload = {"name": f"TEST_iter90_{int(time.time())}", "companion_slug": TestFamilyMembers.picked_slug}
        r = api.post(f"{BASE}/api/family/members", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["name"] == payload["name"]
        assert body["companion_slug"] == payload["companion_slug"]
        assert body.get("companion_name"), "companion_name should be resolved from slug"
        assert body.get("id"), "id required for delete"
        TestFamilyMembers.created_id = body["id"]

    def test_03_verify_persisted(self, api):
        r = api.get(f"{BASE}/api/family/members", timeout=20)
        assert r.status_code == 200
        ids = [m["id"] for m in r.json()["items"]]
        assert TestFamilyMembers.created_id in ids

    def test_04_add_without_name_rejected(self, api):
        r = api.post(f"{BASE}/api/family/members", json={"name": "   "}, timeout=20)
        assert r.status_code == 400

    def test_05_add_without_companion(self, api):
        r = api.post(f"{BASE}/api/family/members", json={"name": "TEST_iter90_no_patron"}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["companion_slug"] in (None, "")
        # cleanup this one
        api.delete(f"{BASE}/api/family/members/{body['id']}", timeout=20)

    def test_06_delete_member(self, api):
        r = api.delete(f"{BASE}/api/family/members/{TestFamilyMembers.created_id}", timeout=20)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_07_delete_verified(self, api):
        r = api.get(f"{BASE}/api/family/members", timeout=20)
        ids = [m["id"] for m in r.json()["items"]]
        assert TestFamilyMembers.created_id not in ids

    def test_08_unauthenticated(self):
        r = requests.get(f"{BASE}/api/family/members", timeout=20)
        assert r.status_code in (401, 403)


# --- coloring pages backing the share button ---
class TestColoringPages:
    def test_pages_load(self, api):
        r = api.get(f"{BASE}/api/coloring-pages", timeout=20)
        assert r.status_code == 200, r.text
        items = r.json().get("items")
        assert isinstance(items, list) and len(items) > 0
        p = items[0]
        for k in ("slug", "title", "image"):
            assert k in p


# --- family/today (top of Family screen) ---
class TestFamilyToday:
    def test_today(self, api):
        r = api.get(f"{BASE}/api/family/today", timeout=25)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("morning_prayer", "night_prayer", "devotional", "question", "saint"):
            assert k in data


# --- library deep-link targets ---
class TestLibraryDeepLinks:
    @pytest.mark.parametrize("slug", CHILDREN_SLUGS + PARENT_SLUGS)
    def test_book_exists(self, api, slug):
        r = api.get(f"{BASE}/api/library/books/{slug}", timeout=20)
        assert r.status_code == 200, f"{slug} -> {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("slug") == slug
        assert body.get("title")
