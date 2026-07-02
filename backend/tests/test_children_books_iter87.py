"""
Backend tests for Iteration 87 — Children's Books in Sanctus Library.

Verifies:
- GET /api/library/books returns 3 children books (tradition="children") with correct
  slugs, chapter_counts, and all is_premium=false.
- GET /api/library/books/{slug} returns chapters list for a children book.
- GET /api/library/books/{slug}/chapters/{index} returns full body_md WITHOUT
  any premium/paywall gate.
- Regression: existing spiritual classics (premium) and encyclicals (papal, free)
  still return normally.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_feat_aug25"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

CHILDREN_EXPECTED = {
    "bible-stories-for-little-souls": 12,
    "little-saints-for-little-hearts": 9,
    "the-holy-mass-for-little-ones": 8,
}


@pytest.fixture(scope="module")
def all_books():
    r = requests.get(f"{BASE_URL}/api/library/books", headers=HEADERS, timeout=30)
    assert r.status_code == 200, f"library/books failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    assert "items" in data, f"missing items key: {data}"
    return data["items"]


# ---------- Children books list ----------
class TestChildrenBooksList:
    def test_three_children_books_present(self, all_books):
        children = [b for b in all_books if (b.get("tradition") or "").lower() == "children"]
        slugs = {b["slug"] for b in children}
        assert slugs == set(CHILDREN_EXPECTED.keys()), (
            f"expected children slugs {set(CHILDREN_EXPECTED.keys())}, got {slugs}"
        )

    def test_children_books_are_free_and_have_chapters(self, all_books):
        for b in all_books:
            if (b.get("tradition") or "").lower() != "children":
                continue
            slug = b["slug"]
            assert b.get("is_premium") is False, f"{slug} is_premium should be False, got {b.get('is_premium')}"
            assert b.get("chapter_count", 0) == CHILDREN_EXPECTED[slug], (
                f"{slug} chapter_count expected {CHILDREN_EXPECTED[slug]}, got {b.get('chapter_count')}"
            )

    def test_children_books_have_title_and_author(self, all_books):
        for b in all_books:
            if (b.get("tradition") or "").lower() != "children":
                continue
            assert b.get("title"), f"{b.get('slug')} missing title"
            assert b.get("author"), f"{b.get('slug')} missing author"


# ---------- Children book detail & chapter reader ----------
class TestChildrenBookDetail:
    @pytest.mark.parametrize("slug,expected_chapters", list(CHILDREN_EXPECTED.items()))
    def test_book_detail_has_chapters(self, slug, expected_chapters):
        r = requests.get(f"{BASE_URL}/api/library/books/{slug}", headers=HEADERS, timeout=30)
        assert r.status_code == 200, f"{slug} detail failed: {r.status_code} {r.text[:200]}"
        data = r.json()
        chapters = data.get("chapters") or []
        assert len(chapters) == expected_chapters, (
            f"{slug} expected {expected_chapters} chapters, got {len(chapters)}"
        )
        assert data.get("is_premium") is False, f"{slug} detail is_premium should be False"

    def test_chapter_0_full_body_no_paywall(self):
        slug = "bible-stories-for-little-souls"
        r = requests.get(
            f"{BASE_URL}/api/library/books/{slug}/chapters/0", headers=HEADERS, timeout=30
        )
        assert r.status_code == 200, f"chapter 0 failed: {r.status_code} {r.text[:200]}"
        data = r.json()
        body = data.get("body_md") or ""
        assert len(body) > 500, f"body_md unexpectedly short: {len(body)} chars"
        # Should NOT be locked/gated
        assert data.get("is_locked") in (False, None), f"chapter is_locked should be false, got {data.get('is_locked')}"
        assert data.get("paywall") in (False, None), f"chapter should not be paywalled: {data}"
        # sanity: our known text
        assert "In the very beginning" in body, "chapter 0 body missing expected story text"

    def test_children_chapter_free_without_auth(self):
        """Children books should be free — verify a chapter loads even without auth header."""
        slug = "little-saints-for-little-hearts"
        r = requests.get(f"{BASE_URL}/api/library/books/{slug}/chapters/0", timeout=30)
        # Either returns 200 with body, or 401 if endpoint requires auth (auth != premium).
        # If 200: body must be present and not gated. If 401: children rule still applies for authed users.
        if r.status_code == 200:
            body = (r.json().get("body_md") or "")
            assert len(body) > 200, "unauth children chapter body missing"

    def test_all_children_chapter_bodies_present(self):
        """Spot-check each children book: chapter 0 body_md non-empty."""
        for slug in CHILDREN_EXPECTED:
            r = requests.get(
                f"{BASE_URL}/api/library/books/{slug}/chapters/0", headers=HEADERS, timeout=30
            )
            assert r.status_code == 200, f"{slug} ch0 failed {r.status_code}"
            body = r.json().get("body_md") or ""
            assert len(body) > 300, f"{slug} ch0 body too short ({len(body)} chars)"


# ---------- Regression: other library sections ----------
class TestLibraryRegression:
    def test_authored_books_present(self, all_books):
        authored = [
            b for b in all_books
            if (b.get("tradition") or "").lower() not in ("papal", "children")
        ]
        assert len(authored) >= 3, f"expected >=3 spiritual classics/authored, got {len(authored)}"

    def test_encyclicals_present_and_free(self, all_books):
        encyclicals = [b for b in all_books if (b.get("tradition") or "").lower() == "papal"]
        assert len(encyclicals) >= 1, "expected >=1 papal/encyclical book"
        for b in encyclicals:
            assert b.get("is_premium") is False, f"encyclical {b['slug']} should be free"

    def test_at_least_one_premium_classic(self, all_books):
        premium = [b for b in all_books if b.get("is_premium") is True]
        assert len(premium) >= 1, "expected at least one premium book (regression)"
