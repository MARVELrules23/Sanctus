"""Tests for the full Catechism of the Catholic Church (CCC) library ingest.

Covers:
 - Library listing includes the CCC as an embedded, free (is_premium=False),
   reference-tradition book with 374 chapters.
 - Book detail returns 374 chapter entries (index + title, no body).
 - Chapter 0 title is 'PROLOGUE'.
 - Reading chapter 60 returns readable body_md and a subtitle breadcrumb.
 - Out-of-range chapter returns 404.
 - Regression: patris-corde still opens & has multi-chapter TOC.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/") or \
           "https://divine-office.preview.emergentagent.com"
TOKEN = "test_feat_aug25"
SLUG = "catechism-of-the-catholic-church"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    })
    return s


# ---------------- Library listing ----------------
class TestCCCListing:
    def test_ccc_present_in_library_books_listing(self, api):
        r = api.get(f"{BASE_URL}/api/library/books", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data
        item = next((b for b in data["items"] if b.get("slug") == SLUG), None)
        assert item is not None, "CCC book not present in /library/books"
        # Field verifications
        assert item.get("is_premium") is False, f"CCC must be free; got is_premium={item.get('is_premium')}"
        assert item.get("type") == "embedded"
        assert item.get("chapter_count") == 374, f"expected 374 chapters got {item.get('chapter_count')}"
        assert (item.get("tradition") or "").lower() == "reference"


# ---------------- Book detail + chapters ----------------
class TestCCCBookDetail:
    def test_book_detail_returns_374_chapter_metas(self, api):
        r = api.get(f"{BASE_URL}/api/library/books/{SLUG}", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        chapters = data.get("chapters") or []
        assert len(chapters) == 374, f"expected 374 chapters, got {len(chapters)}"
        # No bodies in listing form
        for c in chapters[:5]:
            assert "index" in c
            assert "title" in c
            assert "body_md" not in c, "list response should not include chapter bodies"
        # Chapter 0 title
        assert chapters[0]["title"].strip().upper() == "PROLOGUE", \
            f"Chapter 0 title expected 'PROLOGUE', got {chapters[0]['title']!r}"

    def test_get_chapter_60_has_body_and_subtitle(self, api):
        r = api.get(f"{BASE_URL}/api/library/books/{SLUG}/chapters/60", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("chapter_index") == 60
        body = data.get("body_md") or ""
        assert len(body) > 100, f"body_md too short: {len(body)} chars"
        # Ensure it looks like real CCC content (contains at least some letters/paragraphs)
        assert any(ch.isalpha() for ch in body)
        subtitle = data.get("subtitle")
        # Subtitle breadcrumb should be present (may be empty string per API contract but
        # per problem statement should carry a breadcrumb for CCC).
        assert subtitle is not None
        assert isinstance(subtitle, str)
        assert len(subtitle.strip()) > 0, "expected a non-empty subtitle breadcrumb for CCC chapter 60"

    def test_out_of_range_chapter_returns_404(self, api):
        r = api.get(f"{BASE_URL}/api/library/books/{SLUG}/chapters/999", timeout=30)
        assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text}"

    def test_chapter_0_prologue_body(self, api):
        r = api.get(f"{BASE_URL}/api/library/books/{SLUG}/chapters/0", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["title"].strip().upper() == "PROLOGUE"
        assert len((d.get("body_md") or "").strip()) > 0


# ---------------- Regression: patris-corde ----------------
class TestPatrisCordeRegression:
    def test_patris_corde_opens_with_multiple_chapters(self, api):
        r = api.get(f"{BASE_URL}/api/library/books/patris-corde", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        chapters = d.get("chapters") or []
        assert len(chapters) > 1, f"patris-corde expected multi-chapter, got {len(chapters)}"

    def test_patris_corde_chapter_0_readable(self, api):
        r = api.get(f"{BASE_URL}/api/library/books/patris-corde/chapters/0", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert len((d.get("body_md") or "").strip()) > 0
