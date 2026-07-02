"""Iter85 - Tests for new saint devotionals + vocation daily verse."""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or "https://divine-office.preview.emergentagent.com"
BASE_URL = BASE_URL.rstrip("/")
TOKEN = "test_feat_aug25"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


# -------- Companions with new novena_slug ----------
COMPANION_EXPECTATIONS = [
    ("augustine", "st-augustine", "Novena to St. Augustine"),
    ("thomas-aquinas", "st-thomas-aquinas", "Novena to St. Thomas Aquinas"),
    ("john-the-baptist", "st-john-baptist", "Novena to St. John the Baptist"),
    ("james-the-less", "st-james-less", "Novena to St. James the Less"),
]


@pytest.mark.parametrize("slug,expected_nov,expected_title", COMPANION_EXPECTATIONS)
def test_companion_has_novena_slug_and_devotion(api_client, slug, expected_nov, expected_title):
    r = api_client.get(f"{BASE_URL}/api/companions/{slug}")
    assert r.status_code == 200, f"{slug} -> {r.status_code} {r.text[:200]}"
    data = r.json()
    assert data.get("novena_slug") == expected_nov, f"{slug} novena_slug = {data.get('novena_slug')}"

    sds = data.get("saint_devotions") or []
    match = [d for d in sds if (d.get("title") or "").strip() == expected_title]
    assert match, f"{slug}: no saint_devotions entry titled '{expected_title}'. Got: {[d.get('title') for d in sds]}"
    d = match[0]
    assert d.get("route") == f"/novenas/{expected_nov}", f"{slug}: route was {d.get('route')}"


# -------- Novena detail endpoints ----------
NOVENA_SLUGS = ["st-augustine", "st-thomas-aquinas", "st-john-baptist", "st-james-less"]


@pytest.mark.parametrize("slug", NOVENA_SLUGS)
def test_novena_detail_ok(api_client, slug):
    r = api_client.get(f"{BASE_URL}/api/novenas/{slug}")
    assert r.status_code == 200, f"{slug}: {r.status_code} {r.text[:200]}"
    d = r.json()
    assert d.get("name"), f"{slug}: missing name"
    mp = (d.get("main_prayer") or "").strip()
    assert len(mp) > 40, f"{slug}: main_prayer empty/short: {mp[:60]}"


# -------- Vocation guide daily_verse ----------
def test_vocation_guide_has_daily_verse(api_client):
    r = api_client.get(f"{BASE_URL}/api/vocation/guide")
    assert r.status_code == 200, f"guide status {r.status_code} - {r.text[:200]}"
    g = r.json()
    assert g.get("has_vocation") is True, f"user has_vocation false: {g}"
    dv = g.get("daily_verse")
    assert dv, "daily_verse missing from vocation guide"
    assert dv.get("reference"), f"daily_verse.reference missing: {dv}"
    assert (dv.get("text") or "").strip(), f"daily_verse.text empty: {dv}"


def test_vocation_guide_still_has_readings_and_devrecs(api_client):
    r = api_client.get(f"{BASE_URL}/api/vocation/guide")
    assert r.status_code == 200
    g = r.json()
    # Regression: readings + devotional_recs still present
    assert isinstance(g.get("readings"), list) and len(g["readings"]) > 0, "readings regressed"
    assert isinstance(g.get("devotional_recs"), list) and len(g["devotional_recs"]) > 0, "devotional_recs regressed"
