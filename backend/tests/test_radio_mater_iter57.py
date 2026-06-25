"""
Iter 57 — Verify Italian radio swap:
  - 'Vatican News — Italiano' (slug 'vatican-news-italian') removed
  - 'Radio Mater' (slug 'radio-mater') present with expected stream URL
  - Italian set now: Radio Mater, Radio Maria Italia, Radio Maria USA & Canada (Italiano)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_feat_aug25"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def stations(api):
    r = api.get(f"{BASE_URL}/api/library/radio", timeout=30)
    assert r.status_code == 200, f"radio list status {r.status_code}: {r.text[:300]}"
    data = r.json()
    # accept either {stations:[...]} or [...]
    if isinstance(data, dict):
        for k in ("stations", "items", "results", "data"):
            if k in data and isinstance(data[k], list):
                return data[k]
        # fallback: a single list-like value
        for v in data.values():
            if isinstance(v, list):
                return v
        raise AssertionError(f"Unexpected radio payload keys: {list(data.keys())}")
    assert isinstance(data, list)
    return data


def _by_slug(stations, slug):
    for s in stations:
        if s.get("slug") == slug:
            return s
    return None


# -- Verify Radio Mater present with correct fields --------------------------
class TestRadioMaterPresent:
    def test_radio_mater_listed(self, stations):
        rm = _by_slug(stations, "radio-mater")
        assert rm is not None, "Radio Mater (slug=radio-mater) not found in /api/library/radio"
        assert rm.get("name") == "Radio Mater", f"name mismatch: {rm.get('name')}"
        assert rm.get("language") == "Italian", f"language mismatch: {rm.get('language')}"
        assert rm.get("stream_url") == "https://s2.shoutitaly.com/listen/radiomater/radio.mp3", \
            f"stream_url mismatch: {rm.get('stream_url')}"

    def test_radio_mater_detail_endpoint(self, api):
        r = api.get(f"{BASE_URL}/api/library/radio/radio-mater", timeout=20)
        assert r.status_code == 200, f"detail status {r.status_code}: {r.text[:200]}"
        data = r.json()
        assert data.get("slug") == "radio-mater"
        assert data.get("stream_url") == "https://s2.shoutitaly.com/listen/radiomater/radio.mp3"


# -- Verify Vatican News Italiano removed -----------------------------------
class TestVaticanItalianGone:
    def test_no_vatican_news_italian_slug(self, stations):
        bad = _by_slug(stations, "vatican-news-italian")
        assert bad is None, f"Removed station still present: {bad}"

    def test_no_station_named_vatican_news_italiano(self, stations):
        names = [s.get("name", "") for s in stations]
        offending = [n for n in names if "Vatican News" in n and ("Italian" in n or "Italiano" in n)]
        assert not offending, f"Vatican Italian station still listed: {offending}"

    def test_no_italian_stream_pointing_to_vaticannews(self, stations):
        # Defensive: no Italian station should have a vatican stream URL
        for s in stations:
            if s.get("language") == "Italian":
                url = (s.get("stream_url") or "")
                assert "radio.vaticannews.va" not in url, \
                    f"Italian station {s.get('slug')} still uses vaticannews stream: {url}"


# -- Verify Italian set composition -----------------------------------------
class TestItalianSet:
    def test_italian_stations_are_exactly_expected(self, stations):
        italians = sorted(s.get("slug") for s in stations if s.get("language") == "Italian")
        expected = sorted(["radio-mater", "radio-maria-italia", "radio-maria-canada"])
        assert italians == expected, f"Italian slugs unexpected. Got {italians}, expected {expected}"


# -- Regression: existing English / Spanish stations still present ----------
class TestRegression:
    def test_english_stations_still_present(self, stations):
        for slug in ("ewtn-radio", "relevant-radio", "vatican-news-english"):
            assert _by_slug(stations, slug) is not None, f"Missing English station: {slug}"

    def test_spanish_station_still_present(self, stations):
        # vatican-news-spanish is at line ~628 in seed
        spanish = [s for s in stations if s.get("language") == "Spanish"]
        assert len(spanish) >= 1, "Expected at least one Spanish radio station"

    def test_all_stream_urls_https(self, stations):
        for s in stations:
            url = s.get("stream_url") or ""
            assert url.startswith("https://"), f"Non-HTTPS stream for {s.get('slug')}: {url}"
