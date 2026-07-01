"""Iteration 80 feature batch tests:
- Vocation guide: morning/afternoon/night prayers
- Library: 5 embedded papal encyclicals with chapter content
- Library: 7 external devotional books with source_url
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_feat_aug25"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    return s


# ---------- Vocation Guide (time-of-day prayers) ----------
class TestVocationGuide:
    def test_guide_returns_three_time_prayers(self, api):
        r = api.get(f"{BASE_URL}/api/vocation/guide", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("has_vocation") is True
        assert d.get("label") == "Holy Marriage"
        for key in ("morning_prayer", "afternoon_prayer", "night_prayer"):
            p = d.get(key)
            assert p and isinstance(p, dict), f"{key} missing/invalid"
            assert p.get("title"), f"{key}.title empty"
            assert p.get("body") and len(p["body"]) > 20, f"{key}.body too short"

    def test_time_prayers_distinct_or_meaningful(self, api):
        d = api.get(f"{BASE_URL}/api/vocation/guide", timeout=20).json()
        titles = {d["morning_prayer"]["title"], d["afternoon_prayer"]["title"], d["night_prayer"]["title"]}
        # Should have at least 2 distinct titles across the day
        assert len(titles) >= 2


# ---------- Library: Papal encyclicals (embedded, papal, with chapters) ----------
ENCYCLICAL_SLUGS = [
    "redemptoris-mater",
    "marialis-cultus",
    "rosarium-virginis-mariae",
    "redemptoris-custos",
    "patris-corde",
]

EXTERNAL_SLUGS = [
    "treatise-on-the-angels",
    "the-guardian-angel",
    "devotion-to-the-guardian-angels",
    "the-glories-of-mary",
    "true-devotion-to-mary",
    "life-and-glories-of-st-joseph",
    "story-of-a-soul",
]


class TestLibraryEncyclicals:
    def test_books_list_includes_all_encyclicals(self, api):
        r = api.get(f"{BASE_URL}/api/library/books", timeout=20)
        assert r.status_code == 200, r.text
        payload = r.json()
        books = payload if isinstance(payload, list) else (payload.get("books") or payload.get("items") or [])
        by_slug = {b["slug"]: b for b in books}
        for slug in ENCYCLICAL_SLUGS:
            assert slug in by_slug, f"missing encyclical {slug}"
            assert by_slug[slug].get("type") == "embedded", f"{slug} not embedded"
            assert by_slug[slug].get("tradition") == "papal", f"{slug} tradition not papal"

    @pytest.mark.parametrize("slug", ENCYCLICAL_SLUGS)
    def test_encyclical_detail_has_chapters(self, api, slug):
        r = api.get(f"{BASE_URL}/api/library/books/{slug}", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["slug"] == slug
        assert d.get("type") == "embedded"
        chapters = d.get("chapters") or []
        assert len(chapters) >= 1, f"{slug} has no chapters"

    @pytest.mark.parametrize("slug", ENCYCLICAL_SLUGS)
    def test_encyclical_chapter_body_readable(self, api, slug):
        # verify at least the first chapter is readable via /chapters/{i}
        r = api.get(f"{BASE_URL}/api/library/books/{slug}/chapters/0", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        body = d.get("body_md") or d.get("body") or ""
        assert len(body) > 100, f"{slug} chapter 0 body too short (len={len(body)})"


# ---------- Library: External devotional books ----------
class TestLibraryExternalBooks:
    def test_books_list_includes_all_externals(self, api):
        r = api.get(f"{BASE_URL}/api/library/books", timeout=20)
        assert r.status_code == 200
        payload = r.json()
        books = payload if isinstance(payload, list) else (payload.get("books") or payload.get("items") or [])
        by_slug = {b["slug"]: b for b in books}
        for slug in EXTERNAL_SLUGS:
            assert slug in by_slug, f"missing external book {slug}"
            b = by_slug[slug]
            assert b.get("type") == "external", f"{slug} type != external"
            assert b.get("source_url", "").startswith("http"), f"{slug} missing source_url"

    @pytest.mark.parametrize("slug", EXTERNAL_SLUGS)
    def test_external_book_detail(self, api, slug):
        r = api.get(f"{BASE_URL}/api/library/books/{slug}", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d.get("type") == "external"
        assert d.get("source_url", "").startswith("http")
