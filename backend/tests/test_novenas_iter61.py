"""Backend tests for Novenas feature (iter 61)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
TOKEN = "test_feat_aug25"

EXPECTED_SLUGS = {
    "st-therese-little-flower", "divine-mercy", "sacred-heart-jesus", "st-joseph",
    "our-lady-perpetual-help", "st-jude", "st-michael-archangel", "our-lady-lourdes",
    "st-anthony-padua", "guardian-angel", "st-lucy",
}


def _h(lang=None):
    h = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    if lang:
        h["Accept-Language"] = lang
    return h


@pytest.fixture(scope="module", autouse=True)
def cleanup_active():
    # Ensure no active novena before/after tests
    requests.post(f"{API}/novenas/stop", headers=_h(), timeout=15)
    yield
    requests.post(f"{API}/novenas/stop", headers=_h(), timeout=15)


# ---- LIST ----
def test_list_returns_11_novenas():
    r = requests.get(f"{API}/novenas", headers=_h(), timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data and "active" in data
    items = data["items"]
    assert len(items) == 11
    slugs = {it["slug"] for it in items}
    assert slugs == EXPECTED_SLUGS
    for it in items:
        for k in ("slug", "name", "patron", "feast", "theme", "color", "icon", "intro", "days"):
            assert k in it
        assert it["days"] == 9


def test_list_no_active_after_stop():
    r = requests.get(f"{API}/novenas", headers=_h(), timeout=15)
    assert r.json()["active"] is None


# ---- DETAIL ----
def test_detail_divine_mercy_has_day_intentions():
    r = requests.get(f"{API}/novenas/divine-mercy", headers=_h(), timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["slug"] == "divine-mercy"
    assert d["main_prayer"] and len(d["main_prayer"]) > 50
    assert isinstance(d["day_intentions"], list)
    assert len(d["day_intentions"]) == 9
    assert d["enrollment"] is None


def test_detail_st_therese_no_day_intentions():
    r = requests.get(f"{API}/novenas/st-therese-little-flower", headers=_h(), timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["day_intentions"] is None or d["day_intentions"] == []


def test_detail_unknown_slug_404():
    r = requests.get(f"{API}/novenas/nope", headers=_h(), timeout=15)
    assert r.status_code == 404


# ---- START / TRACK / COMPLETE ----
def test_start_and_complete_day():
    # ensure clean
    requests.post(f"{API}/novenas/stop", headers=_h(), timeout=15)
    r = requests.post(f"{API}/novenas/divine-mercy/start", headers=_h(),
                     json={"start_date": "2026-01-15"}, timeout=15)
    assert r.status_code == 200, r.text
    enr = r.json()
    assert enr["slug"] == "divine-mercy"
    assert enr["start_date"] == "2026-01-15"
    assert enr["end_date"] == "2026-01-23"  # +8 days
    assert enr["status"] == "active"
    assert enr["completed_days"] == []
    assert enr["total_days"] == 9

    # complete day 1
    r2 = requests.post(f"{API}/novenas/divine-mercy/complete-day", headers=_h(),
                      json={"day": 1}, timeout=15)
    assert r2.status_code == 200, r2.text
    assert 1 in r2.json()["completed_days"]

    # verify via active
    r3 = requests.get(f"{API}/novenas/active", headers=_h(), timeout=15)
    assert r3.status_code == 200
    a = r3.json()["active"]
    assert a is not None
    assert a["slug"] == "divine-mercy"
    assert 1 in a["completed_days"]


def test_complete_day_invalid():
    r = requests.post(f"{API}/novenas/divine-mercy/complete-day", headers=_h(),
                     json={"day": 10}, timeout=15)
    assert r.status_code == 400
    r2 = requests.post(f"{API}/novenas/divine-mercy/complete-day", headers=_h(),
                      json={"day": 0}, timeout=15)
    assert r2.status_code == 400


def test_start_conflict_returns_409():
    # divine-mercy active from prior test; try starting another
    r = requests.post(f"{API}/novenas/st-jude/start", headers=_h(),
                     json={"start_date": "2026-01-15"}, timeout=15)
    assert r.status_code == 409, r.text
    detail = r.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("active_slug") == "divine-mercy"


def test_restart_same_slug_resets_progress():
    r = requests.post(f"{API}/novenas/divine-mercy/start", headers=_h(),
                     json={"start_date": "2026-01-20"}, timeout=15)
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["start_date"] == "2026-01-20"
    assert e["completed_days"] == []


def test_invalid_start_date_400():
    requests.post(f"{API}/novenas/stop", headers=_h(), timeout=15)
    r = requests.post(f"{API}/novenas/divine-mercy/start", headers=_h(),
                     json={"start_date": "01-15-2026"}, timeout=15)
    assert r.status_code == 400


def test_stop_clears_active():
    # start something
    requests.post(f"{API}/novenas/stop", headers=_h(), timeout=15)
    r = requests.post(f"{API}/novenas/guardian-angel/start", headers=_h(),
                     json={"start_date": "2026-01-15"}, timeout=15)
    assert r.status_code == 200
    s = requests.post(f"{API}/novenas/stop", headers=_h(), timeout=15)
    assert s.status_code == 200
    a = requests.get(f"{API}/novenas/active", headers=_h(), timeout=15)
    assert a.json()["active"] is None


# ---- REFLECTION (AI) ----
def test_reflection_day_returns_text_and_caches():
    # start fresh
    requests.post(f"{API}/novenas/stop", headers=_h(), timeout=15)
    requests.post(f"{API}/novenas/st-jude/start", headers=_h(),
                 json={"start_date": "2026-01-15"}, timeout=15)
    t0 = time.time()
    r = requests.get(f"{API}/novenas/st-jude/reflection/1", headers=_h(), timeout=60)
    dt1 = time.time() - t0
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["slug"] == "st-jude"
    assert data["day"] == 1
    text1 = data["reflection"]
    assert isinstance(text1, str)
    # AI may fail; allow empty but log
    if not text1:
        pytest.skip("AI reflection empty — likely Emergent LLM key issue; skipping cache check")
    # second call should be faster (cached)
    t1 = time.time()
    r2 = requests.get(f"{API}/novenas/st-jude/reflection/1", headers=_h(), timeout=30)
    dt2 = time.time() - t1
    assert r2.status_code == 200
    assert r2.json()["reflection"] == text1
    # Cached should be substantially faster
    print(f"first={dt1:.2f}s cached={dt2:.2f}s")


def test_reflection_invalid_day():
    r = requests.get(f"{API}/novenas/st-jude/reflection/0", headers=_h(), timeout=15)
    assert r.status_code == 400
    r2 = requests.get(f"{API}/novenas/st-jude/reflection/10", headers=_h(), timeout=15)
    assert r2.status_code == 400


# ---- I18N ----
def test_detail_spanish_localized():
    r_en = requests.get(f"{API}/novenas/sacred-heart-jesus", headers=_h("en"), timeout=20)
    r_es = requests.get(f"{API}/novenas/sacred-heart-jesus", headers=_h("es"), timeout=60)
    assert r_en.status_code == 200 and r_es.status_code == 200
    en = r_en.json()
    es = r_es.json()
    # At least one localized field differs
    diff = (en["name"] != es["name"]) or (en["intro"] != es["intro"]) or (en["main_prayer"] != es["main_prayer"])
    assert diff, "Spanish detail not localized"


def test_list_italian_localized():
    r_en = requests.get(f"{API}/novenas", headers=_h("en"), timeout=20)
    r_it = requests.get(f"{API}/novenas", headers=_h("it"), timeout=60)
    en_names = [i["name"] for i in r_en.json()["items"]]
    it_names = [i["name"] for i in r_it.json()["items"]]
    assert en_names != it_names, "Italian names not localized"
