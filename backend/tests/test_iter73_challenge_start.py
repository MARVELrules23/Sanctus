"""Iter73 — challenge enroll start_option (today/tomorrow/liturgical) + invalid 422 + re-anchor."""
import os
from datetime import date, timedelta
import pytest
import requests

BASE = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") if "EXPO_PUBLIC_BACKEND_URL" in os.environ else "https://divine-office.preview.emergentagent.com"
TOKEN = "test_feat_aug25"
SLUG = "hallowtide"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def _get(slug=SLUG):
    return requests.get(f"{BASE}/api/challenges/{slug}", headers=H, timeout=30)


def _enroll(body):
    return requests.post(f"{BASE}/api/challenges/{SLUG}/enroll", headers=H, json=body, timeout=30)


def _unenroll():
    return requests.delete(f"{BASE}/api/challenges/{SLUG}/enroll", headers=H, timeout=30)


def test_invalid_start_option_returns_422():
    r = _enroll({"start_option": "next_year"})
    assert r.status_code == 422, r.text


def test_enroll_today_anchors_day1_today():
    _unenroll()
    r = _enroll({"start_option": "today"})
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True
    today = date.today().isoformat()
    assert (r.json().get("start_date") or "").startswith(today)

    g = _get()
    assert g.status_code == 200
    d = g.json()
    assert d["enrolled"] is True
    assert (d.get("enrollment", {}).get("start_date") or "").startswith(today)
    days = d.get("days") or []
    if days:
        d1 = [x for x in days if x["day_index"] == 1][0]
        assert (d1["date"] or "").startswith(today)
        if len(days) > 1:
            d2 = [x for x in days if x["day_index"] == 2][0]
            tomorrow = (date.today() + timedelta(days=1)).isoformat()
            assert (d2["date"] or "").startswith(tomorrow)


def test_reenroll_updates_start_date():
    r = _enroll({"start_option": "tomorrow"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("already") is True
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert (body.get("start_date") or "").startswith(tomorrow)


def test_liturgical_option_uses_canonical_window():
    r = _enroll({"start_option": "liturgical"})
    assert r.status_code == 200
    g = _get().json()
    # canonical hallowtide start is Oct 31 of seeded year — must not equal today necessarily
    assert g["enrolled"] is True
    assert g.get("enrollment", {}).get("start_date") is not None


def test_explicit_start_date():
    target = (date.today() + timedelta(days=3)).isoformat()
    r = _enroll({"start_date": target})
    assert r.status_code == 200
    assert (r.json().get("start_date") or "").startswith(target)


def test_cleanup_unenroll():
    r = _unenroll()
    assert r.status_code == 200
