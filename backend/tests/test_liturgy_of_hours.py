"""Liturgy of the Hours — backend endpoint tests.

Covers:
- /api/liturgy index (auth required)
- /api/liturgy/{hour} detail (404 unknown hour)
- /api/liturgy/{hour}/{day} per-day sections (404 unknown day)
- Lauds & Vespers psalmody DIFFERS between weekdays
- Compline psalmody is IDENTICAL across days (psalms_vary_by_day=false)
- Free + admin users both get 200 (NOT premium gated)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
ADMIN_TOKEN = "test_liturgy_admin_001"
FREE_TOKEN = "test_liturgy_free_001"


@pytest.fixture(scope="module")
def admin_client():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {ADMIN_TOKEN}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def free_client():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {FREE_TOKEN}", "Content-Type": "application/json"})
    return s


# -------- Auth --------
class TestAuth:
    def test_index_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/liturgy")
        assert r.status_code == 401, r.text

    def test_hour_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/liturgy/lauds")
        assert r.status_code == 401, r.text

    def test_day_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/liturgy/lauds/monday")
        assert r.status_code == 401, r.text


# -------- Index --------
class TestIndex:
    def test_index_200_shape(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/liturgy")
        assert r.status_code == 200, r.text
        data = r.json()
        assert set(data.keys()) >= {"hours", "days", "today", "external_link"}
        slugs = [h["slug"] for h in data["hours"]]
        assert slugs == ["lauds", "vespers", "compline"], slugs
        day_keys = [d["key"] for d in data["days"]]
        assert day_keys == ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"], day_keys
        # external link is iBreviary/Universalis style
        ext = data["external_link"]
        assert "url" in ext and ext["url"].startswith("http")
        # today belongs to the days list
        assert data["today"] in day_keys

    def test_free_user_can_access(self, free_client):
        # Feature is NOT premium gated
        r = free_client.get(f"{BASE_URL}/api/liturgy")
        assert r.status_code == 200, r.text

    def test_hour_summary_metadata(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/liturgy").json()
        for h in r["hours"]:
            # critical fields used by reader UI
            for k in ("slug", "name", "latin_name", "subtitle", "time_of_day", "duration",
                      "icon", "accent_color", "psalms_vary_by_day"):
                assert k in h, f"missing {k} in {h}"
        # Lauds & Vespers should vary; Compline should NOT
        by_slug = {h["slug"]: h for h in r["hours"]}
        assert by_slug["lauds"]["psalms_vary_by_day"] is True
        assert by_slug["vespers"]["psalms_vary_by_day"] is True
        assert by_slug["compline"]["psalms_vary_by_day"] is False


# -------- Hour detail --------
class TestHourDetail:
    @pytest.mark.parametrize("slug", ["lauds", "vespers", "compline"])
    def test_hour_detail_ok(self, admin_client, slug):
        r = admin_client.get(f"{BASE_URL}/api/liturgy/{slug}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["slug"] == slug
        assert "intro" in data and len(data["intro"]) > 20
        assert "days" in data and len(data["days"]) == 7
        assert "section_count_per_day" in data and data["section_count_per_day"] >= 1

    def test_unknown_hour_404(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/liturgy/matins")
        assert r.status_code == 404, r.text

    def test_unknown_hour_random_404(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/liturgy/foobar")
        assert r.status_code == 404, r.text


# -------- Day detail --------
class TestDayDetail:
    @pytest.mark.parametrize("slug,day", [
        ("lauds", "monday"),
        ("lauds", "sunday"),
        ("vespers", "wednesday"),
        ("compline", "saturday"),
    ])
    def test_day_ok(self, admin_client, slug, day):
        r = admin_client.get(f"{BASE_URL}/api/liturgy/{slug}/{day}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["hour"]["slug"] == slug
        assert data["day"]["key"] == day
        assert "today" in data
        sections = data["sections"]
        assert isinstance(sections, list) and len(sections) >= 5
        for sec in sections:
            for k in ("index", "title", "english"):
                assert k in sec, f"section missing {k}: {sec.keys()}"
            # latin/latin_title/rubric/note may be None but the keys should be returned
            assert "latin" in sec
            assert "latin_title" in sec
            assert "rubric" in sec
            assert "note" in sec
        # Section indices are monotonic from 0
        idxs = [s["index"] for s in sections]
        assert idxs == sorted(idxs)

    def test_unknown_day_404(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/liturgy/lauds/funday")
        assert r.status_code == 404, r.text

    def test_unknown_hour_then_day_404(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/liturgy/matins/monday")
        assert r.status_code == 404, r.text


def _psalmody_section(sections):
    """Find the 'Antiphons & Psalms' section (the one that should vary)."""
    for sec in sections:
        if "Psalms" in (sec.get("title") or "") or "Antiphons" in (sec.get("title") or ""):
            return sec
    return None


# -------- Psalmody variation --------
class TestPsalmodyVariation:
    def test_lauds_varies_between_days(self, admin_client):
        mon = admin_client.get(f"{BASE_URL}/api/liturgy/lauds/monday").json()["sections"]
        sun = admin_client.get(f"{BASE_URL}/api/liturgy/lauds/sunday").json()["sections"]
        tue = admin_client.get(f"{BASE_URL}/api/liturgy/lauds/tuesday").json()["sections"]

        mon_p = _psalmody_section(mon)
        sun_p = _psalmody_section(sun)
        tue_p = _psalmody_section(tue)
        assert mon_p and sun_p and tue_p
        assert mon_p["english"] != sun_p["english"], "Lauds Monday == Sunday psalmody (should differ)"
        assert mon_p["english"] != tue_p["english"], "Lauds Monday == Tuesday psalmody (should differ)"
        assert mon_p["latin"] != sun_p["latin"], "Latin Lauds Mon == Sun (should differ)"

    def test_vespers_varies_between_days(self, admin_client):
        mon = admin_client.get(f"{BASE_URL}/api/liturgy/vespers/monday").json()["sections"]
        sun = admin_client.get(f"{BASE_URL}/api/liturgy/vespers/sunday").json()["sections"]
        mon_p = _psalmody_section(mon)
        sun_p = _psalmody_section(sun)
        assert mon_p and sun_p
        assert mon_p["english"] != sun_p["english"], "Vespers Mon == Sun (should differ)"

    def test_compline_identical_across_days(self, admin_client):
        days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
        payloads = []
        for d in days:
            r = admin_client.get(f"{BASE_URL}/api/liturgy/compline/{d}")
            assert r.status_code == 200
            payloads.append(r.json()["sections"])
        # All identical (psalms_vary_by_day = False)
        first = payloads[0]
        for i, p in enumerate(payloads[1:], 1):
            assert p == first, f"Compline differs on {days[i]} vs {days[0]}"

    def test_compline_hour_meta_says_no_vary(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/liturgy/compline").json()
        assert r["psalms_vary_by_day"] is False


# -------- Bible hub integration: liturgy slot exposed via dailyHomeFeed?  --------
# Not a hub endpoint; bible hub link is FE-only. Skipping here.
