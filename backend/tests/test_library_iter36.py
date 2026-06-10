"""Iteration 36 — Library/Bernadette regression tests.

Tests the iter-36 delta:
  - films/ccc-bernadette-anim → new youtube_id ACBWU4ug-rc, title 'Bernadette — Princess of Lourdes', category 'saints'
  - books/orthodoxy-chesterton → type='embedded', 10 chapters, first chapter 'Preface'
  - chapter endpoint exposes new optional `subtitle` field
  - confessions-augustine ch.0 is full-text (>10K chars)
  - existing books still have correct chapter counts
"""
import os
import pytest
import requests

BASE = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
ADMIN_TOKEN = "TEST_iter32_admin_tok"
HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}", "Content-Type": "application/json"}


# ---------- P0: Bernadette film ----------
class TestBernadetteFilm:
    def test_film_detail(self):
        r = requests.get(f"{BASE}/api/library/films/ccc-bernadette-anim", headers=HEADERS, timeout=20)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        data = r.json()
        assert data["youtube_id"] == "ACBWU4ug-rc", f"got youtube_id={data.get('youtube_id')!r}"
        assert "Bernadette" in data["title"] and "Lourdes" in data["title"], f"title={data.get('title')!r}"
        assert data["category"] == "saints", f"category={data.get('category')!r}"

    def test_film_in_list(self):
        r = requests.get(f"{BASE}/api/library/films", headers=HEADERS, timeout=20)
        assert r.status_code == 200
        items = r.json().get("items") or r.json()
        if isinstance(items, dict):
            items = items.get("items") or []
        slugs = [f["slug"] for f in items]
        assert "ccc-bernadette-anim" in slugs

    def test_film_list_size_regression(self):
        r = requests.get(f"{BASE}/api/library/films", headers=HEADERS, timeout=20)
        assert r.status_code == 200
        body = r.json()
        items = body if isinstance(body, list) else body.get("items", [])
        assert len(items) >= 12, f"only {len(items)} films returned"


# ---------- P0: Orthodoxy book ----------
class TestOrthodoxy:
    def test_book_detail(self):
        r = requests.get(f"{BASE}/api/library/books/orthodoxy-chesterton", headers=HEADERS, timeout=20)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        b = r.json()
        assert b["type"] == "embedded", f"type={b.get('type')!r}"
        chapters = b.get("chapters", [])
        assert len(chapters) == 10, f"expected 10 chapters, got {len(chapters)}"
        assert chapters[0]["title"] == "Preface", f"first chapter title={chapters[0].get('title')!r}"

    def test_chapter_0_preface_and_subtitle(self):
        # NOTE: ch0 is the Preface (genuinely short ~1.5K chars per Gutenberg #130).
        # We assert it's a real, populated body and has the `subtitle` key,
        # then in the next test verify a real chapter is full-text.
        r = requests.get(f"{BASE}/api/library/books/orthodoxy-chesterton/chapters/0", headers=HEADERS, timeout=20)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        c = r.json()
        body = c.get("body_md", "")
        assert len(body) > 1000, f"Preface body_md len={len(body)} (<1000) — looks truncated"
        assert "subtitle" in c, f"subtitle key missing; keys={list(c.keys())}"

    def test_chapter_1_full_text(self):
        # Chapter I should be a real chapter, >5K chars from Gutenberg full text.
        r = requests.get(f"{BASE}/api/library/books/orthodoxy-chesterton/chapters/1", headers=HEADERS, timeout=20)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        c = r.json()
        body = c.get("body_md", "")
        assert len(body) > 5000, f"Chapter I body_md len={len(body)} (<5000)"
        assert "subtitle" in c, f"subtitle key missing; keys={list(c.keys())}"


# ---------- P0: Confessions full-text ----------
class TestConfessionsFullText:
    def test_chapter_0_full_text_and_subtitle(self):
        r = requests.get(f"{BASE}/api/library/books/confessions-augustine/chapters/0", headers=HEADERS, timeout=20)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        c = r.json()
        body = c.get("body_md", "")
        assert len(body) > 10000, f"body_md len={len(body)} (<10000)"
        assert "subtitle" in c, f"subtitle key missing; keys={list(c.keys())}"


# ---------- P1: regression on existing books ----------
EXPECTED_CHAPTER_COUNTS = {
    "imitation-of-christ": 114,
    "story-of-a-soul": 11,
    "abandonment-divine-providence": 4,
    "practice-presence-of-god": 19,
}


@pytest.mark.parametrize("slug,expected", list(EXPECTED_CHAPTER_COUNTS.items()))
def test_existing_book_chapter_counts(slug, expected):
    r = requests.get(f"{BASE}/api/library/books/{slug}", headers=HEADERS, timeout=20)
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
    b = r.json()
    assert len(b.get("chapters", [])) == expected, f"{slug}: expected {expected}, got {len(b.get('chapters', []))}"


# ---------- P1: regression listings ----------
def test_films_list_regression():
    r = requests.get(f"{BASE}/api/library/films", headers=HEADERS, timeout=20)
    assert r.status_code == 200
    body = r.json()
    items = body if isinstance(body, list) else body.get("items", [])
    assert len(items) >= 12


def test_radio_list_regression():
    r = requests.get(f"{BASE}/api/library/radio", headers=HEADERS, timeout=20)
    assert r.status_code == 200
    body = r.json()
    items = body if isinstance(body, list) else body.get("items", [])
    assert len(items) >= 1


def test_books_list_regression():
    r = requests.get(f"{BASE}/api/library/books", headers=HEADERS, timeout=20)
    assert r.status_code == 200
    body = r.json()
    items = body if isinstance(body, list) else body.get("items", [])
    assert len(items) >= 5
    slugs = [b["slug"] for b in items]
    for must in ("orthodoxy-chesterton", "confessions-augustine", "imitation-of-christ"):
        assert must in slugs, f"missing slug {must} in books list"


# ---------- Auth gating (sanity) ----------
def test_films_auth_required():
    r = requests.get(f"{BASE}/api/library/films/ccc-bernadette-anim", timeout=10)
    assert r.status_code in (401, 403), f"expected auth gate, got {r.status_code}"
