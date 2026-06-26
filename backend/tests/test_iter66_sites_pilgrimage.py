"""Iteration 66 — Sanctus map expansion to 270 sites + 'Saint of the place near you' + mini pilgrimage.

Covers:
- GET /api/sites returns 270 sites; idempotent on repeat
- GET /api/sites/nearby (no params) returns up to 8 daily-rotating items
- GET /api/sites/nearby?lat=41.9&lng=12.45 returns items sorted by distance_km, nearest = St. Peter's Basilica
- Accept-Language: es localizes /api/sites/nearby
- POST /api/schedule with kind='pilgrimage' creates an item; GET /api/schedule lists it; DELETE removes it
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_feat_aug25"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


# ---------------- Sites ----------------
class TestSites:
    def test_sites_returns_270(self):
        r = requests.get(f"{BASE_URL}/api/sites", headers=HEADERS, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total"] == 270, f"expected 270, got {data['total']}"
        assert len(data["items"]) == 270
        # 84 countries (per spec)
        countries = {x["country"] for x in data["items"]}
        assert len(countries) == 84, f"expected 84 countries, got {len(countries)}"
        # site_id uniqueness
        ids = [x["site_id"] for x in data["items"]]
        assert len(set(ids)) == 270

    def test_sites_idempotent(self):
        r1 = requests.get(f"{BASE_URL}/api/sites", headers=HEADERS, timeout=60).json()
        r2 = requests.get(f"{BASE_URL}/api/sites", headers=HEADERS, timeout=60).json()
        assert r1["total"] == r2["total"] == 270


# ---------------- Nearby ----------------
class TestNearby:
    def test_nearby_no_params_returns_up_to_8(self):
        r = requests.get(f"{BASE_URL}/api/sites/nearby", headers=HEADERS, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and isinstance(data["items"], list)
        assert 1 <= len(data["items"]) <= 8
        # No distance_km expected when location not provided
        for it in data["items"]:
            assert "name" in it and "country" in it

    def test_nearby_rome_nearest_is_st_peters(self):
        # Rome coords
        r = requests.get(
            f"{BASE_URL}/api/sites/nearby",
            params={"lat": 41.9, "lng": 12.45},
            headers=HEADERS,
            timeout=30,
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert items, "expected at least one nearby site"
        # All items should have distance_km
        for it in items:
            assert "distance_km" in it and isinstance(it["distance_km"], (int, float))
        # Sorted ascending
        dists = [it["distance_km"] for it in items]
        assert dists == sorted(dists), f"items not sorted by distance: {dists}"
        # Nearest = St. Peter's Basilica
        nearest_slug = items[0].get("slug", "")
        nearest_name = items[0].get("name", "")
        assert "peter" in nearest_slug.lower() or "peter" in nearest_name.lower(), (
            f"expected St. Peter's nearest to Rome, got {nearest_name} / {nearest_slug}"
        )

    def test_nearby_localized_es(self):
        # First call may be slow if translate cache cold — give long timeout
        h = dict(HEADERS); h["Accept-Language"] = "es"
        r_en = requests.get(f"{BASE_URL}/api/sites/nearby", params={"lat": 41.9, "lng": 12.45},
                            headers=HEADERS, timeout=30)
        r_es = requests.get(f"{BASE_URL}/api/sites/nearby", params={"lat": 41.9, "lng": 12.45},
                            headers=h, timeout=120)
        assert r_es.status_code == 200, r_es.text
        en_items = r_en.json()["items"]
        es_items = r_es.json()["items"]
        # Compare history/name strings — at least one item should differ between EN and ES
        # (some proper-noun-only names may match; history should differ for at least one)
        differed = False
        en_by_slug = {x["slug"]: x for x in en_items}
        for x in es_items:
            en = en_by_slug.get(x["slug"])
            if not en:
                continue
            if (x.get("history") or "") != (en.get("history") or "") and (x.get("history") or ""):
                differed = True
                break
            if (x.get("name") or "") != (en.get("name") or ""):
                differed = True
                break
        assert differed, "Expected at least one localized field (name/history) to differ between EN and ES"


# ---------------- Schedule pilgrimage ----------------
class TestPilgrimageSchedule:
    created_id: str | None = None

    def test_create_pilgrimage_item(self):
        body = {
            "kind": "pilgrimage",
            "title": "Pilgrimage: Lourdes",
            "recurrence": "once",
            "date": "2026-07-11",
            "ref_slug": "lourdes",
            "icon": "footsteps-outline",
            "color": "#7A5CB0",
        }
        r = requests.post(f"{BASE_URL}/api/schedule", json=body, headers=HEADERS, timeout=30)
        assert r.status_code in (200, 201), r.text
        item = r.json()
        assert item["kind"] == "pilgrimage", f"kind didn't persist: {item.get('kind')}"
        assert item["title"] == "Pilgrimage: Lourdes"
        assert item["date"] == "2026-07-11"
        assert item["recurrence"] == "once"
        assert item["ref_slug"] == "lourdes"
        TestPilgrimageSchedule.created_id = item["id"]

    def test_list_includes_pilgrimage(self):
        assert TestPilgrimageSchedule.created_id, "create test must run first"
        r = requests.get(f"{BASE_URL}/api/schedule", headers=HEADERS, timeout=30)
        assert r.status_code == 200, r.text
        ids = [x["id"] for x in r.json()["items"]]
        assert TestPilgrimageSchedule.created_id in ids
        match = next(x for x in r.json()["items"] if x["id"] == TestPilgrimageSchedule.created_id)
        assert match["kind"] == "pilgrimage"

    def test_delete_pilgrimage(self):
        assert TestPilgrimageSchedule.created_id, "create test must run first"
        r = requests.delete(
            f"{BASE_URL}/api/schedule/{TestPilgrimageSchedule.created_id}",
            headers=HEADERS, timeout=30,
        )
        assert r.status_code in (200, 204), r.text
        # Verify gone
        r2 = requests.get(f"{BASE_URL}/api/schedule", headers=HEADERS, timeout=30)
        ids = [x["id"] for x in r2.json()["items"]]
        assert TestPilgrimageSchedule.created_id not in ids
