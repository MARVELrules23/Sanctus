"""Iteration 32 — Sanctus Library Phase 1 (Books) backend tests.

Pre-req: run /app/test_reports/iter32_setup.py setup (mints admin + non-admin tokens).
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://faithful-fitness-3.preview.emergentagent.com").rstrip("/")
ADMIN_TOK = "TEST_iter32_admin_tok"
USER_TOK = "TEST_iter32_user_tok"


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ------------------------------- Public --------------------------------------


def test_list_books_unauthed():
    r = requests.get(f"{BASE_URL}/api/library/books", timeout=15)
    assert r.status_code == 401, r.text


def test_list_books_invalid_token():
    r = requests.get(f"{BASE_URL}/api/library/books", headers=_h("garbage"), timeout=15)
    assert r.status_code == 401, r.text


def test_list_books_published_15():
    r = requests.get(f"{BASE_URL}/api/library/books", headers=_h(USER_TOK), timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data
    items = data["items"]
    assert len(items) >= 15, f"expected >=15 published books, got {len(items)}"
    # Schema check on first book
    sample = items[0]
    expected_fields = {"book_id", "slug", "title", "author", "year", "blurb",
                       "tradition", "cover_color", "cover_icon", "type", "status",
                       "chapter_count", "chapters"}
    missing = expected_fields - set(sample.keys())
    assert not missing, f"missing fields: {missing}"
    # Chapter bodies must NOT leak in list view
    for ch in sample.get("chapters", []):
        assert "body_md" not in ch, "list view leaking chapter body_md"


def test_get_book_practice_presence_progress_null():
    # Clean any prior progress to ensure null
    from pymongo import MongoClient
    cli = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = cli[os.environ.get("DB_NAME", "sanctus_db")]
    book = db.library_books.find_one({"slug": "practice-presence-of-god"})
    assert book is not None, "seed missing practice-presence-of-god"
    db.library_reading_progress.delete_many({"user_id": "TEST_iter32_user", "book_id": book["book_id"]})

    r = requests.get(f"{BASE_URL}/api/library/books/practice-presence-of-god", headers=_h(USER_TOK), timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["slug"] == "practice-presence-of-god"
    assert data["progress"] is None, f"expected null progress, got {data['progress']}"
    assert data["type"] == "embedded"
    assert data["chapter_count"] > 0


def test_get_chapter_0_has_body():
    r = requests.get(
        f"{BASE_URL}/api/library/books/practice-presence-of-god/chapters/0",
        headers=_h(USER_TOK), timeout=15,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "body_md" in data
    assert len(data["body_md"]) > 50, f"chapter body too short: {data['body_md']!r}"
    assert "title" in data


def test_save_progress_and_echo_in_get_book():
    payload = {"chapter_index": 1, "scroll_pct": 0.42}
    r = requests.post(
        f"{BASE_URL}/api/library/books/practice-presence-of-god/progress",
        headers=_h(USER_TOK), json=payload, timeout=15,
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    # GET book echoes progress
    r2 = requests.get(f"{BASE_URL}/api/library/books/practice-presence-of-god", headers=_h(USER_TOK), timeout=15)
    assert r2.status_code == 200, r2.text
    p = r2.json()["progress"]
    assert p is not None
    assert p["chapter_index"] == 1
    assert abs(p["scroll_pct"] - 0.42) < 1e-6

    # GET progress endpoint
    r3 = requests.get(f"{BASE_URL}/api/library/books/practice-presence-of-god/progress", headers=_h(USER_TOK), timeout=15)
    assert r3.status_code == 200
    g = r3.json()
    assert g["exists"] is True
    assert g["chapter_index"] == 1


def test_external_book_catechism():
    r = requests.get(f"{BASE_URL}/api/library/books/catechism-catholic-church", headers=_h(USER_TOK), timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["type"] == "external"
    assert data["source_url"], "external book must have source_url"
    assert data["source_url"].startswith("http")
    assert data["chapters"] == [], f"external should have empty chapters, got {len(data['chapters'])}"


def test_chapter_out_of_range_404():
    r = requests.get(
        f"{BASE_URL}/api/library/books/practice-presence-of-god/chapters/999",
        headers=_h(USER_TOK), timeout=15,
    )
    assert r.status_code == 404


def test_book_not_found_404():
    r = requests.get(f"{BASE_URL}/api/library/books/does-not-exist-zzz", headers=_h(USER_TOK), timeout=15)
    assert r.status_code == 404


# ----------------------------- Admin guard -----------------------------------


def test_admin_list_403_for_regular_user():
    r = requests.get(f"{BASE_URL}/api/library/admin/books", headers=_h(USER_TOK), timeout=15)
    assert r.status_code == 403, r.text


def test_admin_create_403_for_regular_user():
    r = requests.post(
        f"{BASE_URL}/api/library/admin/books", headers=_h(USER_TOK),
        json={"slug": "TEST_blocked", "title": "X", "author": "Y", "type": "embedded"}, timeout=15,
    )
    assert r.status_code == 403, r.text


def test_admin_endpoints_401_no_token():
    r = requests.get(f"{BASE_URL}/api/library/admin/books", timeout=15)
    assert r.status_code == 401


# ----------------------------- Admin CRUD ------------------------------------


def test_admin_full_crud_flow():
    # 1) admin list returns >= 15 (incl. drafts if any)
    r = requests.get(f"{BASE_URL}/api/library/admin/books", headers=_h(ADMIN_TOK), timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["total"] >= 15

    # 2) Create test-classic
    create = {"slug": "test-classic", "title": "Test", "author": "X", "type": "embedded"}
    r = requests.post(f"{BASE_URL}/api/library/admin/books", headers=_h(ADMIN_TOK), json=create, timeout=15)
    assert r.status_code == 200, r.text
    created = r.json()
    assert created["slug"] == "test-classic"
    assert created["status"] == "published"
    assert created["chapter_count"] == 0

    # 3) Add chapter
    r = requests.post(
        f"{BASE_URL}/api/library/admin/books/test-classic/chapters",
        headers=_h(ADMIN_TOK),
        json={"title": "Ch 1", "body_md": "hello"}, timeout=15,
    )
    assert r.status_code == 200, r.text
    assert r.json()["chapter_count"] == 1

    # 3.5) Public list as regular user contains test-classic (published)
    r = requests.get(f"{BASE_URL}/api/library/books", headers=_h(USER_TOK), timeout=15)
    slugs_pub = [b["slug"] for b in r.json()["items"]]
    assert "test-classic" in slugs_pub

    # 4) Patch status to draft
    r = requests.patch(
        f"{BASE_URL}/api/library/admin/books/test-classic",
        headers=_h(ADMIN_TOK),
        json={"status": "draft"}, timeout=15,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "draft"

    # Public list no longer contains it
    r = requests.get(f"{BASE_URL}/api/library/books", headers=_h(USER_TOK), timeout=15)
    slugs_pub = [b["slug"] for b in r.json()["items"]]
    assert "test-classic" not in slugs_pub, "draft should not appear in public list"

    # And GET as regular user → 404
    r = requests.get(f"{BASE_URL}/api/library/books/test-classic", headers=_h(USER_TOK), timeout=15)
    assert r.status_code == 404

    # Admin can still see it via admin list
    r = requests.get(f"{BASE_URL}/api/library/admin/books", headers=_h(ADMIN_TOK), timeout=15)
    slugs_adm = [b["slug"] for b in r.json()["items"]]
    assert "test-classic" in slugs_adm

    # 5) Delete chapter
    r = requests.delete(
        f"{BASE_URL}/api/library/admin/books/test-classic/chapters/0",
        headers=_h(ADMIN_TOK), timeout=15,
    )
    assert r.status_code == 200, r.text
    assert r.json()["chapter_count"] == 0

    # 6) Delete book
    r = requests.delete(f"{BASE_URL}/api/library/admin/books/test-classic", headers=_h(ADMIN_TOK), timeout=15)
    assert r.status_code == 200, r.text

    # Subsequent GET → 404
    r = requests.get(f"{BASE_URL}/api/library/books/test-classic", headers=_h(USER_TOK), timeout=15)
    assert r.status_code == 404
    # Admin too
    r = requests.get(f"{BASE_URL}/api/library/admin/books", headers=_h(ADMIN_TOK), timeout=15)
    slugs_adm = [b["slug"] for b in r.json()["items"]]
    assert "test-classic" not in slugs_adm


def test_admin_create_duplicate_slug_409():
    # Use an existing slug
    r = requests.post(
        f"{BASE_URL}/api/library/admin/books", headers=_h(ADMIN_TOK),
        json={"slug": "practice-presence-of-god", "title": "x", "author": "y", "type": "embedded"},
        timeout=15,
    )
    assert r.status_code == 409, r.text


def test_progress_validation_rejects_bad_scroll_pct():
    r = requests.post(
        f"{BASE_URL}/api/library/books/practice-presence-of-god/progress",
        headers=_h(USER_TOK),
        json={"chapter_index": 0, "scroll_pct": 1.5}, timeout=15,
    )
    assert r.status_code in (400, 422), r.text


# ------------------------------ Cleanup --------------------------------------


def teardown_module(module):
    """Clean up TEST progress rows created by these tests."""
    try:
        from pymongo import MongoClient
        cli = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        db = cli[os.environ.get("DB_NAME", "sanctus_db")]
        db.library_reading_progress.delete_many({"user_id": "TEST_iter32_user"})
        # Make sure test-classic is gone
        b = db.library_books.find_one({"slug": "test-classic"})
        if b:
            db.library_books.delete_one({"slug": "test-classic"})
            db.library_reading_progress.delete_many({"book_id": b["book_id"]})
    except Exception as e:
        print(f"teardown cleanup warning: {e}")
