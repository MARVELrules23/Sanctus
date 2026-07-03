"""Iter 88 — Family tab, Coloring pages, and Library children book covers."""
import os
import re

import pytest
import requests

BASE_URL = "https://divine-office.preview.emergentagent.com"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# ------------------ /api/family/today ------------------
class TestFamilyToday:
    def test_family_today_en_schema(self, s):
        r = s.get(f"{BASE_URL}/api/family/today", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # top-level keys
        for k in ("morning_prayer", "night_prayer", "devotional", "question", "saint"):
            assert k in data, f"missing key: {k}"

        for pk in ("morning_prayer", "night_prayer"):
            p = data[pk]
            assert isinstance(p.get("title"), str) and p["title"], f"{pk}.title"
            lines = p.get("lines")
            assert isinstance(lines, list) and len(lines) >= 3, f"{pk}.lines"
            for ln in lines:
                assert "who" in ln and "text" in ln
                assert isinstance(ln["who"], str) and isinstance(ln["text"], str)

        dv = data["devotional"]
        assert isinstance(dv.get("title"), str) and dv["title"]
        assert isinstance(dv.get("body"), str) and dv["body"]
        assert "route" in dv  # may be None

        assert isinstance(data["question"], str) and len(data["question"]) > 5

        sa = data["saint"]
        for f in ("name", "feast", "patronage", "bio", "icon", "color"):
            assert f in sa and sa[f], f"saint.{f}"

    def test_family_today_spanish(self, s):
        r = s.get(
            f"{BASE_URL}/api/family/today",
            headers={"Accept-Language": "es"},
            timeout=45,
        )
        assert r.status_code == 200
        data = r.json()
        # At least ONE localized field should differ from typical English tokens.
        combined = " ".join(
            [
                data["morning_prayer"]["title"],
                data["night_prayer"]["title"],
                data["devotional"]["title"],
                data["question"],
                data["saint"]["bio"],
            ]
        ).lower()
        english_tokens = ["morning prayer together", "night prayer together"]
        # Translation is best-effort; if both English titles are still there, fail loudly.
        english_hits = sum(1 for t in english_tokens if t in combined)
        assert english_hits < 2, f"Spanish translation not applied (english_hits={english_hits})"


# ------------------ /api/coloring-pages ------------------
EXPECTED_SLUGS = {
    "cross", "chalice-host", "nativity",
    "guardian-angel", "holy-spirit-dove", "sacred-heart",
}


class TestColoringPages:
    def test_coloring_list(self, s):
        r = s.get(f"{BASE_URL}/api/coloring-pages", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        items = data.get("items")
        assert isinstance(items, list) and len(items) >= 6, f"got {len(items) if items else 0} items"
        slugs = {it.get("slug") for it in items}
        missing = EXPECTED_SLUGS - slugs
        assert not missing, f"missing coloring slugs: {missing}"
        # Order attribute present and sortable
        orders = [it.get("order") for it in items]
        assert all(isinstance(o, int) for o in orders), f"orders not ints: {orders}"

        for it in items:
            assert isinstance(it.get("title"), str) and it["title"]
            img = it.get("image") or it.get("image_url") or it.get("data")
            assert isinstance(img, str) and img.startswith("data:image/"), (
                f"page {it.get('slug')} has no data URL image (got prefix: {str(img)[:40]})"
            )
            # base64 payload non-empty (more than a few hundred chars for real line-art)
            b64 = img.split(",", 1)[-1]
            assert len(b64) > 500, f"{it.get('slug')} image too small ({len(b64)} chars)"


# ------------------ /api/library/books ------------------
class TestLibraryChildrenCovers:
    def test_children_books_have_cover_image(self, s):
        r = s.get(
            f"{BASE_URL}/api/library/books",
            headers={"Authorization": "Bearer test_feat_aug25"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        items = r.json().get("items", [])
        children = [b for b in items if (b.get("tradition") or "").lower() == "children"]
        assert len(children) >= 3, f"expected >=3 children books, got {len(children)}"
        for b in children:
            cover = b.get("cover_image")
            assert isinstance(cover, str) and cover.startswith("data:image/"), (
                f"book {b.get('slug')} missing/invalid cover_image (got prefix: {str(cover)[:40]})"
            )
            b64 = cover.split(",", 1)[-1]
            assert len(b64) > 500, f"{b.get('slug')} cover too small"
