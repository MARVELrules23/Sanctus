"""Iteration 68 — viewport-driven bbox loading of Catholic sites.

Tests the new GET /api/sites/bbox endpoint plus regression coverage for the
existing /api/sites, /api/sites/nearby and /api/sites/{slug} routes.
"""
from __future__ import annotations

import os
import time

import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_feat_aug25"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update(HEADERS)
    return sess


def _bbox(s, south, west, north, east, zoom, timeout=60):
    return s.get(
        f"{BASE_URL}/api/sites/bbox",
        params={"south": south, "west": west, "north": north, "east": east, "zoom": zoom},
        timeout=timeout,
    )


# ---------- Auth ----------
class TestAuth:
    def test_bbox_requires_auth(self):
        r = requests.get(
            f"{BASE_URL}/api/sites/bbox",
            params={"south": 41.85, "west": 12.45, "north": 41.95, "east": 12.55, "zoom": 12},
            timeout=20,
        )
        assert r.status_code == 401, f"Expected 401, got {r.status_code} body={r.text[:200]}"


# ---------- World view (low zoom -> curated only) ----------
class TestWorldView:
    def test_world_view_curated_only(self, s):
        r = _bbox(s, -60, -180, 80, 180, 2)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        assert "items" in j and "total" in j and "osm_count" in j
        assert j["osm_count"] == 0, f"World view must not fetch OSM, got osm_count={j['osm_count']}"
        assert j["total"] >= 50, f"Expected many curated sites globally, got {j['total']}"
        # Item shape
        for it in j["items"][:5]:
            for k in ("slug", "name", "type", "lat", "lng"):
                assert k in it, f"missing {k} in item {it}"
            assert isinstance(it.get("osm"), bool)


# ---------- City views ----------
class TestCityViews:
    def test_rome(self, s):
        r = _bbox(s, 41.85, 12.45, 41.95, 12.55, 12)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        assert j["osm_count"] > 50, f"Rome should yield many OSM churches; got {j['osm_count']}"
        # all items within (or very near) bounds — backend snaps bbox to 0.1deg
        # so allow ~0.15deg of slack on each side.
        for it in j["items"]:
            assert 41.70 <= it["lat"] <= 42.10, f"lat out of bounds: {it}"
            assert 12.30 <= it["lng"] <= 12.70, f"lng out of bounds: {it}"
        # at least one is osm
        assert any(it.get("osm") for it in j["items"])

    def test_rome_cache_repeat(self, s):
        # First call may already be cached from prior test; measure a fresh repeat
        t0 = time.time()
        r1 = _bbox(s, 41.85, 12.45, 41.95, 12.55, 12)
        t1 = time.time()
        r2 = _bbox(s, 41.85, 12.45, 41.95, 12.55, 12)
        t2 = time.time()
        assert r1.status_code == 200 and r2.status_code == 200
        j1, j2 = r1.json(), r2.json()
        assert j1["osm_count"] == j2["osm_count"], "Cache should yield identical osm_count"
        assert j1["total"] == j2["total"]
        # Second call should not be slower (allow generous margin)
        first_dur = t1 - t0
        second_dur = t2 - t1
        print(f"Rome timing: first={first_dur:.2f}s second={second_dur:.2f}s")
        assert second_dur <= first_dur + 2.0, (
            f"Repeat slower than first: {second_dur:.2f}s vs {first_dur:.2f}s"
        )

    def test_london(self, s):
        r = _bbox(s, 51.45, -0.20, 51.55, -0.05, 12)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        assert j["osm_count"] > 0, f"London expected OSM churches; got {j['osm_count']}"
        names = " ".join((it.get("name") or "") for it in j["items"]).lower()
        # heuristic: real church names should appear
        assert any(tok in names for tok in ("church", "cathedral", "chapel", "st ", "st.", "saint")), (
            f"No church-like names found in London: {names[:200]}"
        )

    def test_paris(self, s):
        r = _bbox(s, 48.82, 2.30, 48.90, 2.40, 12)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        assert j["osm_count"] > 0, f"Paris expected OSM churches; got {j['osm_count']}"


# ---------- Span guard ----------
class TestSpanGuard:
    def test_large_bbox_high_zoom_skips_osm(self, s):
        t0 = time.time()
        r = _bbox(s, 30, -10, 55, 30, 12, timeout=30)
        dur = time.time() - t0
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        assert j["osm_count"] == 0, f"Large span must skip OSM; got {j['osm_count']}"
        assert dur < 15, f"Span-guarded call should be fast; took {dur:.2f}s"


# ---------- Regression: existing endpoints ----------
class TestRegression:
    def test_sites_list(self, s):
        r = s.get(f"{BASE_URL}/api/sites", timeout=60)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        assert "items" in j and "total" in j
        assert j["total"] >= 200, f"Expected ~270 curated sites; got {j['total']}"

    def test_sites_nearby_rome(self, s):
        r = s.get(
            f"{BASE_URL}/api/sites/nearby",
            params={"lat": 41.9028, "lng": 12.4964},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        for k in ("items", "featured", "nearby_churches", "total"):
            assert k in j, f"Missing key {k}"
        assert j["featured"] is not None
        # featured should be relic-bearing
        if j["featured"]:
            assert j["featured"].get("relics"), "featured should carry relics"
        assert isinstance(j["nearby_churches"], list)

    def test_lourdes_slug(self, s):
        r = s.get(f"{BASE_URL}/api/sites/lourdes", timeout=20)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        assert (j.get("slug") == "lourdes") or ("lourdes" in (j.get("name") or "").lower())
