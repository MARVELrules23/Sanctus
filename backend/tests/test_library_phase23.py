"""Iteration 33 — Sanctus Library Phase 2 (Radio) & Phase 3 (Films) backend tests.

Pre-req: run /app/test_reports/iter32_setup.py setup (mints admin + non-admin tokens).
Reuses the same tokens minted for iter32:
  - admin: TEST_iter32_admin_tok  (philipwils13@gmail.com)
  - user : TEST_iter32_user_tok
"""
import os
import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path
from pymongo import MongoClient

load_dotenv(Path("/app/backend/.env"))
load_dotenv(Path("/app/frontend/.env"))

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or ""
).rstrip("/")
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL not set"
ADMIN_TOK = "TEST_iter32_admin_tok"
USER_TOK = "TEST_iter32_user_tok"

EXPECTED_FILM_CATEGORIES = {"saints", "doctrine", "animated", "documentary"}


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ============================================================================
# RADIO — Public endpoints
# ============================================================================

class TestRadioPublic:
    def test_list_radio_unauthed_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/library/radio", timeout=15)
        assert r.status_code == 401, r.text

    def test_list_radio_invalid_token_401(self):
        r = requests.get(f"{BASE_URL}/api/library/radio", headers=_h("garbage"), timeout=15)
        assert r.status_code == 401

    def test_list_radio_returns_8_seeded_stations(self):
        r = requests.get(f"{BASE_URL}/api/library/radio", headers=_h(USER_TOK), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and "total" in data
        items = data["items"]
        assert len(items) >= 8, f"expected >=8 stations, got {len(items)}"
        # All published
        for s in items:
            assert s["status"] == "published"
        # Schema check on first station
        sample = items[0]
        expected = {"station_id", "slug", "name", "blurb", "country", "language",
                    "stream_url", "accent_color", "icon", "status"}
        missing = expected - set(sample.keys())
        assert not missing, f"missing fields: {missing}"
        # website_url is optional but should be present on at least one
        assert any(s.get("website_url") for s in items), "no station has website_url"

    def test_get_station_by_slug(self):
        r = requests.get(
            f"{BASE_URL}/api/library/radio/ewtn-radio",
            headers=_h(USER_TOK), timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["slug"] == "ewtn-radio"
        assert data["name"] == "EWTN Radio"
        assert data["stream_url"].startswith("http")
        assert data["status"] == "published"

    def test_get_station_not_found_404(self):
        r = requests.get(
            f"{BASE_URL}/api/library/radio/does-not-exist-zzz",
            headers=_h(USER_TOK), timeout=15,
        )
        assert r.status_code == 404


# ============================================================================
# RADIO — Admin endpoints
# ============================================================================

class TestRadioAdmin:
    def test_admin_list_radio_401_no_token(self):
        r = requests.get(f"{BASE_URL}/api/library/admin/radio", timeout=15)
        assert r.status_code == 401

    def test_admin_list_radio_403_for_regular_user(self):
        r = requests.get(
            f"{BASE_URL}/api/library/admin/radio",
            headers=_h(USER_TOK), timeout=15,
        )
        assert r.status_code == 403

    def test_admin_radio_full_crud_round_trip(self):
        slug = "TEST-station-rt"
        # Defensive cleanup
        requests.delete(
            f"{BASE_URL}/api/library/admin/radio/{slug}",
            headers=_h(ADMIN_TOK), timeout=15,
        )

        # 1) admin list (initial)
        r = requests.get(
            f"{BASE_URL}/api/library/admin/radio",
            headers=_h(ADMIN_TOK), timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["total"] >= 8

        # 2) create
        payload = {
            "slug": slug,
            "name": "TEST RT Station",
            "blurb": "round-trip test",
            "country": "US",
            "language": "English",
            "stream_url": "https://example.com/test.mp3",
            "accent_color": "#123456",
            "icon": "radio-outline",
        }
        r = requests.post(
            f"{BASE_URL}/api/library/admin/radio",
            headers=_h(ADMIN_TOK), json=payload, timeout=15,
        )
        assert r.status_code == 200, r.text
        created = r.json()
        assert created["slug"] == slug
        assert created["name"] == "TEST RT Station"
        assert created["status"] == "published"
        assert created["station_id"].startswith("st_")

        # 3) duplicate slug → 409
        r = requests.post(
            f"{BASE_URL}/api/library/admin/radio",
            headers=_h(ADMIN_TOK), json=payload, timeout=15,
        )
        assert r.status_code == 409, r.text

        # 4) public GET returns it
        r = requests.get(
            f"{BASE_URL}/api/library/radio/{slug}",
            headers=_h(USER_TOK), timeout=15,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "TEST RT Station"

        # 5) PATCH: update blurb + set status draft
        r = requests.patch(
            f"{BASE_URL}/api/library/admin/radio/{slug}",
            headers=_h(ADMIN_TOK),
            json={"blurb": "patched blurb", "status": "draft"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        patched = r.json()
        assert patched["blurb"] == "patched blurb"
        assert patched["status"] == "draft"

        # 6) public GET hides drafts → 404
        r = requests.get(
            f"{BASE_URL}/api/library/radio/{slug}",
            headers=_h(USER_TOK), timeout=15,
        )
        assert r.status_code == 404

        # 7) admin list still shows it
        r = requests.get(
            f"{BASE_URL}/api/library/admin/radio",
            headers=_h(ADMIN_TOK), timeout=15,
        )
        slugs = [s["slug"] for s in r.json()["items"]]
        assert slug in slugs

        # 8) DELETE
        r = requests.delete(
            f"{BASE_URL}/api/library/admin/radio/{slug}",
            headers=_h(ADMIN_TOK), timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True

        # 9) DELETE again → 404
        r = requests.delete(
            f"{BASE_URL}/api/library/admin/radio/{slug}",
            headers=_h(ADMIN_TOK), timeout=15,
        )
        assert r.status_code == 404

    def test_admin_patch_non_existent_station_404(self):
        r = requests.patch(
            f"{BASE_URL}/api/library/admin/radio/does-not-exist-zzz",
            headers=_h(ADMIN_TOK), json={"name": "x"}, timeout=15,
        )
        assert r.status_code == 404


# ============================================================================
# FILMS — Public endpoints
# ============================================================================

class TestFilmsPublic:
    def test_list_films_unauthed_401(self):
        r = requests.get(f"{BASE_URL}/api/library/films", timeout=15)
        assert r.status_code == 401

    def test_list_films_returns_12_seeded(self):
        r = requests.get(f"{BASE_URL}/api/library/films", headers=_h(USER_TOK), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data
        items = data["items"]
        assert len(items) >= 12, f"expected >=12 films, got {len(items)}"
        # Schema
        sample = items[0]
        expected = {"film_id", "slug", "title", "blurb", "youtube_id",
                    "duration_label", "category", "accent_color", "status"}
        missing = expected - set(sample.keys())
        assert not missing, f"missing fields: {missing}"
        # All categories present
        cats = {f["category"] for f in items}
        assert cats == EXPECTED_FILM_CATEGORIES, f"got categories {cats}"
        # All published
        for f in items:
            assert f["status"] == "published"
            assert f["youtube_id"], "youtube_id missing"

    @pytest.mark.parametrize("cat", ["saints", "doctrine", "animated", "documentary"])
    def test_films_category_filter(self, cat):
        r = requests.get(
            f"{BASE_URL}/api/library/films?category={cat}",
            headers=_h(USER_TOK), timeout=15,
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) >= 1, f"no films for category {cat}"
        for f in items:
            assert f["category"] == cat, f"got film with cat={f['category']} under {cat}"

    def test_films_invalid_category_ignored_returns_all(self):
        # Category not in whitelist → treated as no filter (returns all published)
        r = requests.get(
            f"{BASE_URL}/api/library/films?category=invalid",
            headers=_h(USER_TOK), timeout=15,
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) >= 12

    def test_get_film_by_slug(self):
        r = requests.get(
            f"{BASE_URL}/api/library/films/molokai-damien",
            headers=_h(USER_TOK), timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["slug"] == "molokai-damien"
        assert data["category"] == "saints"
        assert data["youtube_id"] == "iqJSp5Ph2Vg"

    def test_get_film_not_found_404(self):
        r = requests.get(
            f"{BASE_URL}/api/library/films/does-not-exist-zzz",
            headers=_h(USER_TOK), timeout=15,
        )
        assert r.status_code == 404


# ============================================================================
# FILMS — Admin endpoints
# ============================================================================

class TestFilmsAdmin:
    def test_admin_list_films_401_no_token(self):
        r = requests.get(f"{BASE_URL}/api/library/admin/films", timeout=15)
        assert r.status_code == 401

    def test_admin_list_films_403_for_regular_user(self):
        r = requests.get(
            f"{BASE_URL}/api/library/admin/films",
            headers=_h(USER_TOK), timeout=15,
        )
        assert r.status_code == 403

    def test_admin_films_full_crud_round_trip(self):
        slug = "TEST-film-rt"
        # Defensive cleanup
        requests.delete(
            f"{BASE_URL}/api/library/admin/films/{slug}",
            headers=_h(ADMIN_TOK), timeout=15,
        )

        # admin list initial
        r = requests.get(
            f"{BASE_URL}/api/library/admin/films",
            headers=_h(ADMIN_TOK), timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["total"] >= 12

        # create
        payload = {
            "slug": slug,
            "title": "TEST RT Film",
            "blurb": "round-trip film",
            "youtube_id": "abc123XYZ",
            "duration_label": "10m",
            "category": "documentary",
            "accent_color": "#abcdef",
        }
        r = requests.post(
            f"{BASE_URL}/api/library/admin/films",
            headers=_h(ADMIN_TOK), json=payload, timeout=15,
        )
        assert r.status_code == 200, r.text
        created = r.json()
        assert created["slug"] == slug
        assert created["youtube_id"] == "abc123XYZ"
        assert created["status"] == "published"
        assert created["film_id"].startswith("fm_")

        # duplicate slug → 409
        r = requests.post(
            f"{BASE_URL}/api/library/admin/films",
            headers=_h(ADMIN_TOK), json=payload, timeout=15,
        )
        assert r.status_code == 409

        # invalid category on create → 422
        bad = {**payload, "slug": "TEST-film-bad", "category": "horror"}
        r = requests.post(
            f"{BASE_URL}/api/library/admin/films",
            headers=_h(ADMIN_TOK), json=bad, timeout=15,
        )
        assert r.status_code == 422

        # PATCH: change category + status draft
        r = requests.patch(
            f"{BASE_URL}/api/library/admin/films/{slug}",
            headers=_h(ADMIN_TOK),
            json={"category": "saints", "status": "draft"}, timeout=15,
        )
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["category"] == "saints"
        assert p["status"] == "draft"

        # public GET hides draft → 404
        r = requests.get(
            f"{BASE_URL}/api/library/films/{slug}",
            headers=_h(USER_TOK), timeout=15,
        )
        assert r.status_code == 404

        # DELETE
        r = requests.delete(
            f"{BASE_URL}/api/library/admin/films/{slug}",
            headers=_h(ADMIN_TOK), timeout=15,
        )
        assert r.status_code == 200
        # DELETE again → 404
        r = requests.delete(
            f"{BASE_URL}/api/library/admin/films/{slug}",
            headers=_h(ADMIN_TOK), timeout=15,
        )
        assert r.status_code == 404

    def test_admin_patch_film_invalid_category_422(self):
        r = requests.patch(
            f"{BASE_URL}/api/library/admin/films/molokai-damien",
            headers=_h(ADMIN_TOK), json={"category": "horror"}, timeout=15,
        )
        assert r.status_code == 422


# ============================================================================
# Cleanup
# ============================================================================

def teardown_module(module):
    """Sweep any TEST_ stations/films that survived."""
    try:
        cli = MongoClient(os.environ["MONGO_URL"])
        db = cli[os.environ["DB_NAME"]]
        db.library_radio_stations.delete_many({"slug": {"$regex": "^TEST-"}})
        db.library_films.delete_many({"slug": {"$regex": "^TEST-"}})
        cli.close()
    except Exception as e:
        print(f"teardown warning: {e}")
