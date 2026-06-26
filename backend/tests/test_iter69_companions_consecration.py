"""Iteration 69: Companion saints + 33-Day Consecration to St. Joseph.

Covers:
- GET /api/companions/{slug} for 5 slugs (catherine-siena, francis-assisi,
  st-joseph, monica, therese-lisieux), incl. 404
- GET /api/companions/{slug}/image returns data-url (Gemini cached)
- GET /api/novenas resolves new companion novenas (10 slugs)
- 33-Day consecration: overview, start, day fetch (1 + 33), complete-day,
  stop, out-of-range
"""
from __future__ import annotations

import os
import time
import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_feat_aug25"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

COMPANION_SLUGS = ["francis-assisi", "catherine-siena", "st-joseph", "monica", "therese-lisieux"]
COMPANION_NOVENAS = [
    "st-catherine-siena", "bl-pier-giorgio", "st-john-paul-ii", "st-agnes",
    "st-benedict", "st-francis-assisi", "st-teresa-avila", "sts-louis-zelie",
    "st-gianna", "st-monica",
]


# ---- Companions ----------------------------------------------------------- #
class TestCompanions:
    @pytest.mark.parametrize("slug", COMPANION_SLUGS)
    def test_companion_payload(self, slug):
        r = requests.get(f"{BASE_URL}/api/companions/{slug}", headers=HEADERS, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["slug"] == slug
        assert d["name"]
        assert d["importance"]
        assert isinstance(d["virtues"], list) and len(d["virtues"]) >= 1
        for v in d["virtues"]:
            assert v.get("name") and v.get("how")
        assert d["novena_slug"]
        assert "daily_act" in d
        da = d["daily_act"]
        assert da.get("text") and "index" in da and "total" in da
        assert da["index"] < da["total"]
        assert d["has_consecration"] is True
        assert d["is_joseph"] == (slug == "st-joseph")

    def test_companion_404(self):
        r = requests.get(f"{BASE_URL}/api/companions/does-not-exist", headers=HEADERS, timeout=15)
        assert r.status_code == 404

    @pytest.mark.parametrize("slug", ["francis-assisi", "st-joseph"])
    def test_companion_image(self, slug):
        # First call may take ~8s while Gemini generates; allow retries.
        last = None
        for _ in range(3):
            r = requests.get(f"{BASE_URL}/api/companions/{slug}/image", headers=HEADERS, timeout=60)
            assert r.status_code == 200, r.text
            last = r.json()
            if last.get("image"):
                break
            time.sleep(4)
        assert last and last.get("image"), f"No image returned for {slug}: {last}"
        assert last["image"].startswith("data:image/"), last["image"][:60]


# ---- Novenas list / detail for companion novenas -------------------------- #
class TestCompanionNovenas:
    def test_list_contains_all_new_novenas(self):
        r = requests.get(f"{BASE_URL}/api/novenas", headers=HEADERS, timeout=20)
        assert r.status_code == 200
        data = r.json()
        items = data.get("novenas") or data.get("items") or data
        if isinstance(items, dict):
            items = items.get("novenas", [])
        slugs = {it.get("slug") for it in items if isinstance(it, dict)}
        missing = [s for s in COMPANION_NOVENAS if s not in slugs]
        assert not missing, f"Missing novenas from list endpoint: {missing}"

    @pytest.mark.parametrize("slug", COMPANION_NOVENAS)
    def test_detail_resolves(self, slug):
        r = requests.get(f"{BASE_URL}/api/novenas/{slug}", headers=HEADERS, timeout=20)
        assert r.status_code == 200, f"{slug}: {r.status_code} {r.text[:200]}"
        d = r.json()
        assert d.get("slug") == slug or d.get("name") or d.get("title")


# ---- 33-Day Consecration to St. Joseph ------------------------------------ #
class TestConsecration:
    def test_overview(self):
        r = requests.get(f"{BASE_URL}/api/consecration", headers=HEADERS, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total_days"] == 33
        assert isinstance(d["set_times"], list) and len(d["set_times"]) >= 1
        assert d["daily_prayer"]
        assert d["act_of_consecration"]
        assert isinstance(d["days"], list) and len(d["days"]) == 33

    def test_start_creates_active(self):
        r = requests.post(f"{BASE_URL}/api/consecration/start", json={"start_date": "2026-06-26"},
                          headers=HEADERS, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        act = d.get("active")
        assert act and act["current_day"] == 1
        assert act["total_days"] == 33
        assert act["start_date"] == "2026-06-26"

    def test_day_1_has_meditation_no_act(self):
        r = requests.get(f"{BASE_URL}/api/consecration/day/1", headers=HEADERS, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["day"] == 1
        assert d.get("meditation")
        assert d.get("daily_prayer")
        assert d.get("act_of_consecration") is None

    def test_day_33_has_act(self):
        r = requests.get(f"{BASE_URL}/api/consecration/day/33", headers=HEADERS, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["day"] == 33
        assert d.get("act_of_consecration")

    def test_out_of_range(self):
        for bad in [0, 34, 999]:
            r = requests.get(f"{BASE_URL}/api/consecration/day/{bad}", headers=HEADERS, timeout=15)
            assert r.status_code == 404, f"day {bad}: {r.status_code}"

    def test_complete_then_stop(self):
        # Ensure active first
        requests.post(f"{BASE_URL}/api/consecration/start", json={"start_date": "2026-06-26"},
                      headers=HEADERS, timeout=20)
        r = requests.post(f"{BASE_URL}/api/consecration/complete-day", json={"day": 1},
                          headers=HEADERS, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("status") in ("active", "completed")
        if d.get("active"):
            assert 1 in d["active"]["completed_days"]
        # Stop ends it
        r = requests.post(f"{BASE_URL}/api/consecration/stop", headers=HEADERS, timeout=20)
        assert r.status_code == 200
        # Overview now has active=None
        r2 = requests.get(f"{BASE_URL}/api/consecration", headers=HEADERS, timeout=20)
        assert r2.status_code == 200
        assert r2.json().get("active") is None
