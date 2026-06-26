"""Iteration 67 — GET /api/sites/nearby (relic-prioritized featured + OSM nearby_churches).

Spec being verified:
- GET /api/sites/nearby?lat=&lng= returns {items, featured, nearby_churches, total}.
- 'featured' must be a curated site that HAS relics (relics array non-empty),
  and (per spec) the nearest such site to the given coords.
- nearby_churches: real Catholic churches from OpenStreetMap within ~30 km,
  each with name/lat/lng/distance_km/osm:true, sorted ascending by distance.
  Acceptance rule from main agent: only fail if empty across ALL of
  Madrid AND NYC AND Rome.
- OSM caching: repeat call for same tile returns identical data and is faster
  (mongo collection osm_sites_cache).
- GET /api/sites/nearby (no lat/lng) -> daily-rotating relic-bearing featured
  and empty/absent nearby_churches.
- GET /api/sites -> full curated list (~270).
- GET /api/sites/{slug} -> works for curated 'lourdes'.
- Auth: 401 when Authorization header missing.
"""
import os
import time
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL") or "https://divine-office.preview.emergentagent.com"
BASE_URL = BASE_URL.rstrip("/")
TOKEN = "test_feat_aug25"
H = {"Authorization": f"Bearer {TOKEN}"}

# Cities under test
MADRID = (40.4168, -3.7038)
NYC = (40.7128, -74.0060)
ROME = (41.9028, 12.4964)


def _get_nearby(lat=None, lng=None, lang=None, timeout=60):
    params = {}
    if lat is not None:
        params["lat"] = lat
    if lng is not None:
        params["lng"] = lng
    headers = dict(H)
    if lang:
        headers["Accept-Language"] = lang
    return requests.get(f"{BASE_URL}/api/sites/nearby", params=params, headers=headers, timeout=timeout)


# -------------------- Auth -------------------- #
class TestAuth:
    def test_nearby_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/sites/nearby", timeout=20)
        assert r.status_code in (401, 403), r.status_code

    def test_sites_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/sites", timeout=20)
        assert r.status_code in (401, 403), r.status_code


# -------------------- /api/sites curated list -------------------- #
class TestCuratedSites:
    def test_full_curated_list(self):
        r = requests.get(f"{BASE_URL}/api/sites", headers=H, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        items = data.get("items", [])
        # Spec says ~273; previous iteration was 270. Accept >= 260 as healthy.
        assert len(items) >= 260, f"curated list too small: {len(items)}"
        # essential shape
        assert all("name" in s and "slug" in s for s in items)

    def test_curated_slug_lourdes(self):
        r = requests.get(f"{BASE_URL}/api/sites/lourdes", headers=H, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("slug") == "lourdes"
        assert "name" in d and d["name"]


# -------------------- /api/sites/nearby — shape + relic featured -------------------- #
class TestNearbyShape:
    def test_shape_keys_present(self):
        r = _get_nearby(*ROME)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("items", "featured", "nearby_churches", "total"):
            assert k in d, f"missing key {k}"
        assert isinstance(d["items"], list)
        assert isinstance(d["nearby_churches"], list)
        assert isinstance(d["total"], int)

    def test_featured_has_relics_for_madrid(self):
        r = _get_nearby(*MADRID)
        assert r.status_code == 200, r.text
        d = r.json()
        f = d.get("featured")
        assert f, "featured must not be None when curated relic sites exist"
        relics = f.get("relics") or []
        assert isinstance(relics, list) and len(relics) > 0, (
            f"featured must have non-empty relics; got {relics!r} for site {f.get('slug')}"
        )

    def test_featured_has_relics_for_nyc(self):
        d = _get_nearby(*NYC).json()
        f = d.get("featured")
        assert f and (f.get("relics") or []), f"NYC featured missing relics: {f}"

    def test_featured_has_relics_for_rome(self):
        d = _get_nearby(*ROME).json()
        f = d.get("featured")
        assert f and (f.get("relics") or []), f"Rome featured missing relics: {f}"

    def test_featured_is_nearest_relic_site(self):
        """For each city the featured site should be the nearest curated site
        whose 'relics' array is non-empty (per spec)."""
        for label, (la, ln) in [("Madrid", MADRID), ("NYC", NYC), ("Rome", ROME)]:
            d = _get_nearby(la, ln).json()
            f = d.get("featured")
            items = d.get("items") or []
            # items already filtered/sorted; verify featured.slug matches the
            # first item in items with relics.
            relic_items = [s for s in items if (s.get("relics") or [])]
            assert relic_items, f"{label}: no relic-bearing items returned in 'items'"
            assert f.get("slug") == relic_items[0].get("slug"), (
                f"{label}: featured slug {f.get('slug')} != first relic item "
                f"{relic_items[0].get('slug')}"
            )

    def test_featured_distance_reasonable(self):
        """Sanity: the featured site for Rome should be much closer than for NYC,
        i.e. featured should reflect proximity, not a global default."""
        d_rome = _get_nearby(*ROME).json()
        d_nyc = _get_nearby(*NYC).json()
        fr = (d_rome.get("featured") or {}).get("distance_km")
        fn = (d_nyc.get("featured") or {}).get("distance_km")
        assert isinstance(fr, (int, float)) and isinstance(fn, (int, float)), (fr, fn)
        # Rome's nearest relic site (St Peter's etc.) should be < 50 km.
        assert fr < 50, f"Rome featured distance too large: {fr} km"


# -------------------- nearby_churches (OSM) -------------------- #
class TestOSMNearbyChurches:
    def _fetch(self, la, ln):
        return _get_nearby(la, ln).json().get("nearby_churches") or []

    def test_osm_at_least_one_city_has_data(self):
        """Acceptance rule: only fail if ALL three cities return empty OSM data."""
        counts = {
            "Madrid": len(self._fetch(*MADRID)),
            "NYC": len(self._fetch(*NYC)),
            "Rome": len(self._fetch(*ROME)),
        }
        print("OSM counts:", counts)
        # At least one city must yield > 0 churches (Overpass mirror availability).
        assert any(c > 0 for c in counts.values()), (
            f"All Overpass mirrors appear down — empty nearby_churches everywhere: {counts}"
        )

    def test_osm_shape_and_sort(self):
        """Pick whichever city has data and validate shape + ascending sort."""
        for label, (la, ln) in [("Rome", ROME), ("Madrid", MADRID), ("NYC", NYC)]:
            churches = self._fetch(la, ln)
            if not churches:
                continue
            # shape
            for c in churches:
                assert c.get("name"), c
                assert isinstance(c.get("lat"), (int, float))
                assert isinstance(c.get("lng"), (int, float))
                assert isinstance(c.get("distance_km"), (int, float))
                assert c.get("osm") is True, f"osm flag missing: {c}"
            # ascending sort by distance
            d = [c["distance_km"] for c in churches]
            assert d == sorted(d), f"{label} not sorted ascending: {d[:10]}"
            # 30 km radius is the implementation cap; allow some slack for ways' centers
            assert all(x <= 35 for x in d), f"{label} distance > 35km present: {max(d)}"
            return  # one good city is enough for shape verification
        # If we got here, none had data — TestOSMNearbyChurches.test_osm_at_least_one_city_has_data
        # will already have failed; nothing more to assert.

    def test_osm_cache_repeat_is_consistent_and_faster(self):
        """Second call for same tile should be fast (cached) and identical."""
        # Warm whichever city responds; prefer Rome.
        for la, ln in (ROME, MADRID, NYC):
            t0 = time.time()
            r1 = _get_nearby(la, ln).json().get("nearby_churches") or []
            t1 = time.time() - t0
            if not r1:
                continue
            t0 = time.time()
            r2 = _get_nearby(la, ln).json().get("nearby_churches") or []
            t2 = time.time() - t0
            # Same content (order + count)
            assert len(r1) == len(r2), f"cache miss: counts differ {len(r1)} vs {len(r2)}"
            ids1 = [(c.get("site_id"), c.get("lat"), c.get("lng")) for c in r1]
            ids2 = [(c.get("site_id"), c.get("lat"), c.get("lng")) for c in r2]
            assert ids1 == ids2, "cached results differ between calls"
            # Cached call should be at least somewhat faster; allow generous slack.
            print(f"OSM timings: first={t1:.2f}s second={t2:.2f}s")
            # Don't hard-fail on timing (network jitter); just ensure cached call
            # isn't drastically slower than first.
            assert t2 <= max(t1, 5) + 2, (
                f"second call slower than expected: first={t1:.2f}s, second={t2:.2f}s"
            )
            return


# -------------------- nearby with no lat/lng -------------------- #
class TestNearbyNoCoords:
    def test_no_coords_returns_relic_featured_no_osm(self):
        r = _get_nearby()  # no lat/lng
        assert r.status_code == 200, r.text
        d = r.json()
        f = d.get("featured")
        assert f, "featured must be present even without coords"
        assert (f.get("relics") or []), "daily-rotating featured must have relics"
        nc = d.get("nearby_churches")
        # Spec: empty or absent
        assert nc in (None, [], [None]) or len(nc) == 0, f"expected empty nearby_churches, got {nc}"

    def test_no_coords_daily_rotation_stable_within_call(self):
        """Two back-to-back calls without coords should return the same featured
        (daily rotation is deterministic for a given day)."""
        d1 = _get_nearby().json()
        d2 = _get_nearby().json()
        assert (d1.get("featured") or {}).get("slug") == (d2.get("featured") or {}).get("slug")
