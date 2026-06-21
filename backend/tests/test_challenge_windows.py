"""Tests for GET /api/challenges/windows?year=YYYY (iteration 49).

Verifies that every liturgical challenge (the 6 seeded slugs) is returned
with the correct date window computed for the requested calendar year,
including movable feasts (Lent / Sacred Heart) which recompute per year.
"""
import os

import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
ADMIN_TOKEN = "test_home_layout_24h"

EXPECTED_SLUGS = {
    "hallowtide",
    "advent",
    "lent",
    "st-joseph-consecration",
    "marian-consecration",
    "sacred-heart-consecration",
}

REQUIRED_FIELDS = ("slug", "name", "color", "start_date", "end_date", "total_days", "status")


@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json",
    })
    return s


def _get_windows(api_client, year: int):
    r = api_client.get(f"{BASE_URL}/api/challenges/windows", params={"year": year}, timeout=30)
    assert r.status_code == 200, f"status={r.status_code} body={r.text[:300]}"
    body = r.json()
    assert body.get("year") == year
    items = body.get("items") or []
    return items


def test_windows_2026_returns_six(api_client):
    items = _get_windows(api_client, 2026)
    assert len(items) == 6, f"expected 6 items, got {len(items)}: {[i.get('slug') for i in items]}"
    slugs = {i["slug"] for i in items}
    assert slugs == EXPECTED_SLUGS, f"missing/unexpected slugs: {slugs}"


def test_windows_2026_required_fields(api_client):
    items = _get_windows(api_client, 2026)
    for it in items:
        for f in REQUIRED_FIELDS:
            assert f in it, f"item {it.get('slug')} missing field {f}"
        # date format YYYY-MM-DD (10 chars)
        assert len(it["start_date"]) == 10 and it["start_date"][4] == "-"
        assert len(it["end_date"]) == 10 and it["end_date"][4] == "-"
        assert it["total_days"] > 0


def test_windows_2026_consecration_dates(api_client):
    items = {i["slug"]: i for i in _get_windows(api_client, 2026)}
    # St Joseph: Feb 15 -> Mar 19
    assert items["st-joseph-consecration"]["start_date"] == "2026-02-15"
    assert items["st-joseph-consecration"]["end_date"] == "2026-03-19"
    assert items["st-joseph-consecration"]["total_days"] == 33
    # Marian: Apr 29 -> May 31
    assert items["marian-consecration"]["start_date"] == "2026-04-29"
    assert items["marian-consecration"]["end_date"] == "2026-05-31"
    assert items["marian-consecration"]["total_days"] == 33
    # Sacred Heart 2026: Easter 2026 = Apr 5; +68 = Jun 12. start = Jun 12-32 = May 11.
    assert items["sacred-heart-consecration"]["start_date"] == "2026-05-11"
    assert items["sacred-heart-consecration"]["end_date"] == "2026-06-12"
    assert items["sacred-heart-consecration"]["total_days"] == 33


def test_windows_2026_advent_lent_hallowtide(api_client):
    items = {i["slug"]: i for i in _get_windows(api_client, 2026)}
    # Hallowtide: Oct 31 - Nov 8
    assert items["hallowtide"]["start_date"] == "2026-10-31"
    assert items["hallowtide"]["end_date"] == "2026-11-08"
    # Lent 2026: Easter Apr 5 -> Ash Wed Feb 18 -> Holy Sat Apr 4
    assert items["lent"]["start_date"] == "2026-02-18"
    assert items["lent"]["end_date"] == "2026-04-04"
    # Advent 2026: 4th Sunday before Christmas (Dec 25 Fri 2026). First Sunday = Nov 29.
    assert items["advent"]["start_date"] == "2026-11-29"
    assert items["advent"]["end_date"] == "2026-12-24"


def test_windows_2027_recomputes_movable(api_client):
    items = {i["slug"]: i for i in _get_windows(api_client, 2027)}
    assert set(items.keys()) == EXPECTED_SLUGS
    # Lent 2027: Easter Mar 28 -> Ash Wed Feb 10 -> Holy Sat Mar 27
    assert items["lent"]["start_date"] == "2027-02-10"
    assert items["lent"]["end_date"] == "2027-03-27"
    # Sacred Heart 2027: Easter Mar 28 + 68 days = Jun 4. Start = May 3.
    assert items["sacred-heart-consecration"]["start_date"] == "2027-05-03"
    assert items["sacred-heart-consecration"]["end_date"] == "2027-06-04"
    # Fixed: St Joseph & Marian still 02-15/03-19 and 04-29/05-31
    assert items["st-joseph-consecration"]["start_date"] == "2027-02-15"
    assert items["st-joseph-consecration"]["end_date"] == "2027-03-19"
    assert items["marian-consecration"]["start_date"] == "2027-04-29"
    assert items["marian-consecration"]["end_date"] == "2027-05-31"


def test_windows_requires_year_param(api_client):
    r = api_client.get(f"{BASE_URL}/api/challenges/windows", timeout=15)
    # FastAPI returns 422 for missing required query param
    assert r.status_code in (400, 422)


def test_windows_requires_auth():
    r = requests.get(f"{BASE_URL}/api/challenges/windows", params={"year": 2026}, timeout=15)
    assert r.status_code in (401, 403)
