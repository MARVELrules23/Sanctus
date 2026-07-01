"""Phase 4 — App-wide Bookmarks CRUD tests (iteration 79)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL") or "https://divine-office.preview.emergentagent.com"
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"
TOKEN = "test_feat_aug25"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update(HEADERS)
    return sess


# ---- cleanup helper ----
def _wipe(sess, kind, ref_id):
    try:
        sess.delete(f"{API}/bookmarks", params={"kind": kind, "ref_id": ref_id})
    except Exception:
        pass


@pytest.fixture(scope="module", autouse=True)
def cleanup_test_bookmarks(s):
    # cleanup upfront
    refs = [
        ("prayer", "rosary"),
        ("prayer", "TEST_iter79_prayer"),
        ("bible", "genesis:1"),
        ("catechism", "TEST_iter79_cat"),
        ("book", "TEST_iter79_book"),
        ("encyclical", "TEST_iter79_enc"),
    ]
    for k, r in refs:
        _wipe(s, k, r)
    yield
    for k, r in refs:
        _wipe(s, k, r)


# ---- Auth ----
def test_list_bookmarks_requires_auth():
    r = requests.get(f"{API}/bookmarks")
    assert r.status_code in (401, 403), r.text


def test_add_bookmarks_requires_auth():
    r = requests.post(
        f"{API}/bookmarks",
        json={"kind": "prayer", "ref_id": "rosary", "title": "T", "route": "/prayer/rosary"},
    )
    assert r.status_code in (401, 403), r.text


# ---- Validation ----
def test_add_bookmark_invalid_kind(s):
    r = s.post(
        f"{API}/bookmarks",
        json={"kind": "bogus", "ref_id": "x", "title": "t", "route": "/x"},
    )
    assert r.status_code == 400, r.text
    assert "invalid" in r.text.lower()


def test_add_bookmark_missing_ref_id(s):
    r = s.post(
        f"{API}/bookmarks",
        json={"kind": "prayer", "ref_id": "", "title": "t", "route": "/x"},
    )
    assert r.status_code == 400, r.text


def test_add_bookmark_missing_title(s):
    r = s.post(
        f"{API}/bookmarks",
        json={"kind": "prayer", "ref_id": "rosary", "title": "", "route": "/prayer/rosary"},
    )
    assert r.status_code == 400, r.text


def test_add_bookmark_missing_route(s):
    r = s.post(
        f"{API}/bookmarks",
        json={"kind": "prayer", "ref_id": "rosary", "title": "Rosary", "route": ""},
    )
    assert r.status_code == 400, r.text


# ---- CRUD + idempotency ----
def test_create_list_delete_prayer_bookmark(s):
    payload = {
        "kind": "prayer",
        "ref_id": "TEST_iter79_prayer",
        "title": "TEST_iter79 prayer",
        "subtitle": "unit-test",
        "route": "/prayer/TEST_iter79_prayer",
        "params": {"foo": "bar"},
    }
    r = s.post(f"{API}/bookmarks", json=payload)
    assert r.status_code == 200, r.text
    created = r.json()
    assert created["kind"] == "prayer"
    assert created["ref_id"] == "TEST_iter79_prayer"
    assert created["title"] == "TEST_iter79 prayer"
    assert created["route"] == "/prayer/TEST_iter79_prayer"
    assert created["params"] == {"foo": "bar"}
    assert created["bookmark_id"].startswith("bmk_")

    # verify persistence via list
    lst = s.get(f"{API}/bookmarks").json()["items"]
    matches = [b for b in lst if b["kind"] == "prayer" and b["ref_id"] == "TEST_iter79_prayer"]
    assert len(matches) == 1, matches

    # DELETE
    d = s.delete(f"{API}/bookmarks", params={"kind": "prayer", "ref_id": "TEST_iter79_prayer"})
    assert d.status_code == 200, d.text
    assert d.json()["deleted"] == 1

    # verify gone
    lst2 = s.get(f"{API}/bookmarks").json()["items"]
    assert not any(b["kind"] == "prayer" and b["ref_id"] == "TEST_iter79_prayer" for b in lst2)


def test_idempotent_upsert(s):
    payload = {
        "kind": "bible",
        "ref_id": "genesis:1",
        "title": "Genesis 1",
        "route": "/bible/genesis/1",
    }
    r1 = s.post(f"{API}/bookmarks", json=payload)
    assert r1.status_code == 200, r1.text
    id1 = r1.json()["bookmark_id"]

    # POST same kind+ref_id again → same bookmark_id, no duplicate
    r2 = s.post(f"{API}/bookmarks", json={**payload, "title": "Genesis 1 (updated)"})
    assert r2.status_code == 200, r2.text
    id2 = r2.json()["bookmark_id"]
    assert id1 == id2
    assert r2.json()["title"] == "Genesis 1 (updated)"

    lst = s.get(f"{API}/bookmarks", params={"kind": "bible"}).json()["items"]
    matches = [b for b in lst if b["ref_id"] == "genesis:1"]
    assert len(matches) == 1

    s.delete(f"{API}/bookmarks", params={"kind": "bible", "ref_id": "genesis:1"})


def test_list_filter_by_kind(s):
    # seed one of each kind
    to_seed = [
        {"kind": "catechism", "ref_id": "TEST_iter79_cat", "title": "cat", "route": "/"},
        {"kind": "book", "ref_id": "TEST_iter79_book", "title": "bk", "route": "/library/books/x"},
        {"kind": "encyclical", "ref_id": "TEST_iter79_enc", "title": "enc", "route": "/library/books/y"},
    ]
    for p in to_seed:
        r = s.post(f"{API}/bookmarks", json=p)
        assert r.status_code == 200

    for p in to_seed:
        lst = s.get(f"{API}/bookmarks", params={"kind": p["kind"]}).json()["items"]
        assert all(b["kind"] == p["kind"] for b in lst)
        assert any(b["ref_id"] == p["ref_id"] for b in lst)

    for p in to_seed:
        s.delete(f"{API}/bookmarks", params={"kind": p["kind"], "ref_id": p["ref_id"]})


def test_delete_nonexistent_returns_ok_zero(s):
    r = s.delete(f"{API}/bookmarks", params={"kind": "prayer", "ref_id": "does_not_exist_xyz"})
    assert r.status_code == 200
    assert r.json()["deleted"] == 0
