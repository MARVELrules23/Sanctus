"""Phase 2 — Douay-Rheims Bible endpoints test suite.

Covers:
- GET /api/bible/books
- GET /api/bible/chapter/{book}/{chapter}
- POST /api/bible/highlight
- DELETE /api/bible/highlight/{book}/{chapter}/{verse}
- GET /api/bible/highlights
- Regression sanity for: /auth/me, /wellness/profile, /meals/generate, /churches/nearby
"""
import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
TOKEN = "ui_test_token_xyz"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    yield s


@pytest.fixture(scope="module", autouse=True)
def cleanup_before(client):
    """Wipe any pre-existing highlights on test verses to ensure deterministic runs."""
    for slug, ch, v in [("john", 3, 16), ("matthew", 5, 3), ("luke", 1, 1)]:
        client.delete(f"{BASE_URL}/api/bible/highlight/{slug}/{ch}/{v}", headers=AUTH)
    yield
    for slug, ch, v in [("john", 3, 16), ("matthew", 5, 3), ("luke", 1, 1)]:
        client.delete(f"{BASE_URL}/api/bible/highlight/{slug}/{ch}/{v}", headers=AUTH)


# ---------- /api/bible/books ----------
class TestBooksCatalog:
    def test_books_returns_73(self, client):
        r = client.get(f"{BASE_URL}/api/bible/books")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data
        assert len(data["items"]) == 73

    def test_books_section_distribution(self, client):
        items = client.get(f"{BASE_URL}/api/bible/books").json()["items"]
        sections = {}
        for b in items:
            sections[b["section"]] = sections.get(b["section"], 0) + 1
        # 39 protocanonical OT + 7 deuterocanonical + 27 NT = 73 (Catholic canon).
        # Note: review_request said "46 OT" which counted ot+deutero together; the
        # backend correctly separates them into 3 distinct sections.
        assert sections.get("ot") == 39, f"expected 39 protocanon OT, got {sections}"
        assert sections.get("deutero") == 7, f"expected 7 deutero, got {sections}"
        assert sections.get("nt") == 27, f"expected 27 NT, got {sections}"
        assert sections.get("ot", 0) + sections.get("deutero", 0) == 46  # full OT

    def test_books_deutero_set(self, client):
        items = client.get(f"{BASE_URL}/api/bible/books").json()["items"]
        deuteros = {b["name"] for b in items if b["section"] == "deutero"}
        expected = {"Tobit", "Judith", "Wisdom", "Sirach", "Baruch",
                    "1 Maccabees", "2 Maccabees"}
        assert deuteros == expected

    def test_books_orders_unique_and_sequential(self, client):
        items = client.get(f"{BASE_URL}/api/bible/books").json()["items"]
        orders = sorted(b["order"] for b in items)
        assert orders == list(range(1, 74))

    def test_books_required_fields(self, client):
        items = client.get(f"{BASE_URL}/api/bible/books").json()["items"]
        for b in items:
            for key in ("slug", "name", "dr_name", "abbr", "section", "order", "chapters"):
                assert key in b, f"book {b.get('slug')} missing {key}"
            assert b["section"] in {"ot", "deutero", "nt"}

    def test_psalms_150_chapters(self, client):
        items = client.get(f"{BASE_URL}/api/bible/books").json()["items"]
        ps = next(b for b in items if b["slug"] == "psalms")
        assert ps["chapters"] == 150

    def test_john_chapters_and_abbr(self, client):
        items = client.get(f"{BASE_URL}/api/bible/books").json()["items"]
        j = next(b for b in items if b["slug"] == "john")
        assert j["chapters"] == 21
        assert j["abbr"] == "Jn"

    def test_2macc_dr_name(self, client):
        items = client.get(f"{BASE_URL}/api/bible/books").json()["items"]
        mc = next(b for b in items if b["slug"] == "2-maccabees")
        assert mc["dr_name"] == "2 Machabees"


# ---------- /api/bible/chapter ----------
class TestChapterEndpoint:
    def test_john_3_structure(self, client):
        r = client.get(f"{BASE_URL}/api/bible/chapter/john/3", headers=AUTH)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["book_slug"] == "john"
        assert d["book_name"] == "John"
        assert d["dr_name"] == "John"
        assert d["chapter"] == 3
        assert d["chapters_total"] == 21
        assert isinstance(d["verses"], list) and len(d["verses"]) > 0
        for v in d["verses"]:
            assert isinstance(v["n"], int)
            assert isinstance(v["text"], str) and v["text"].strip()
        assert isinstance(d["highlights"], list)

    def test_john_3_16_dr_phrase(self, client):
        d = client.get(f"{BASE_URL}/api/bible/chapter/john/3", headers=AUTH).json()
        v16 = next((v for v in d["verses"] if v["n"] == 16), None)
        assert v16 is not None, "verse 16 missing"
        text = v16["text"].lower()
        assert "may not perish" in text and "life everlasting" in text, \
            f"expected DR phrasing 'may not perish ... life everlasting', got: {v16['text']}"

    def test_genesis_1_min_30_verses(self, client):
        r = client.get(f"{BASE_URL}/api/bible/chapter/genesis/1", headers=AUTH)
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["verses"]) >= 30

    def test_tobit_3_deutero(self, client):
        r = client.get(f"{BASE_URL}/api/bible/chapter/tobit/3", headers=AUTH)
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["verses"]) > 0

    def test_2macc_7_deutero(self, client):
        r = client.get(f"{BASE_URL}/api/bible/chapter/2-maccabees/7", headers=AUTH)
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["verses"]) > 0

    def test_chapter_out_of_range_high(self, client):
        r = client.get(f"{BASE_URL}/api/bible/chapter/john/22", headers=AUTH)
        assert r.status_code == 400

    def test_chapter_unknown_book(self, client):
        r = client.get(f"{BASE_URL}/api/bible/chapter/fakebook/1", headers=AUTH)
        assert r.status_code == 404

    def test_chapter_zero(self, client):
        r = client.get(f"{BASE_URL}/api/bible/chapter/john/0", headers=AUTH)
        assert r.status_code == 400

    def test_chapter_requires_auth(self, client):
        r = client.get(f"{BASE_URL}/api/bible/chapter/john/3")
        assert r.status_code == 401


# ---------- POST /api/bible/highlight ----------
class TestHighlightCreate:
    def test_set_highlight_rose(self, client):
        r = client.post(f"{BASE_URL}/api/bible/highlight", headers=AUTH,
                        json={"book": "john", "chapter": 3, "verse": 16, "color": "rose"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d == {"book": "john", "chapter": 3, "verse": 16, "color": "rose"}

    def test_update_highlight_gold_reflects_in_chapter(self, client):
        r = client.post(f"{BASE_URL}/api/bible/highlight", headers=AUTH,
                        json={"book": "john", "chapter": 3, "verse": 16, "color": "gold"})
        assert r.status_code == 200
        assert r.json()["color"] == "gold"
        chap = client.get(f"{BASE_URL}/api/bible/chapter/john/3", headers=AUTH).json()
        hl = [h for h in chap["highlights"] if h["verse"] == 16]
        assert len(hl) == 1
        assert hl[0]["color"] == "gold"

    def test_invalid_color(self, client):
        r = client.post(f"{BASE_URL}/api/bible/highlight", headers=AUTH,
                        json={"book": "john", "chapter": 3, "verse": 16, "color": "purple"})
        assert r.status_code == 400

    def test_unknown_book(self, client):
        r = client.post(f"{BASE_URL}/api/bible/highlight", headers=AUTH,
                        json={"book": "fakebook", "chapter": 1, "verse": 1, "color": "rose"})
        assert r.status_code == 404

    def test_chapter_out_of_range(self, client):
        r = client.post(f"{BASE_URL}/api/bible/highlight", headers=AUTH,
                        json={"book": "john", "chapter": 99, "verse": 1, "color": "rose"})
        assert r.status_code == 400

    def test_requires_auth(self, client):
        r = client.post(f"{BASE_URL}/api/bible/highlight",
                        json={"book": "john", "chapter": 3, "verse": 16, "color": "rose"})
        assert r.status_code == 401


# ---------- DELETE /api/bible/highlight ----------
class TestHighlightDelete:
    def test_delete_existing(self, client):
        # Ensure exists
        client.post(f"{BASE_URL}/api/bible/highlight", headers=AUTH,
                    json={"book": "luke", "chapter": 1, "verse": 1, "color": "sage"})
        r = client.delete(f"{BASE_URL}/api/bible/highlight/luke/1/1", headers=AUTH)
        assert r.status_code == 200
        assert r.json() == {"deleted": 1}
        # Should no longer appear in chapter highlights
        chap = client.get(f"{BASE_URL}/api/bible/chapter/luke/1", headers=AUTH).json()
        assert all(h["verse"] != 1 for h in chap["highlights"])

    def test_delete_nonexistent(self, client):
        # Ensure absent
        client.delete(f"{BASE_URL}/api/bible/highlight/luke/1/1", headers=AUTH)
        r = client.delete(f"{BASE_URL}/api/bible/highlight/luke/1/1", headers=AUTH)
        assert r.status_code == 200
        assert r.json() == {"deleted": 0}


# ---------- GET /api/bible/highlights ----------
class TestHighlightsList:
    def test_list_after_two_sets(self, client):
        # Ensure clean & deterministic
        client.delete(f"{BASE_URL}/api/bible/highlight/john/3/16", headers=AUTH)
        client.delete(f"{BASE_URL}/api/bible/highlight/matthew/5/3", headers=AUTH)
        client.post(f"{BASE_URL}/api/bible/highlight", headers=AUTH,
                    json={"book": "john", "chapter": 3, "verse": 16, "color": "gold"})
        client.post(f"{BASE_URL}/api/bible/highlight", headers=AUTH,
                    json={"book": "matthew", "chapter": 5, "verse": 3, "color": "sage"})
        r = client.get(f"{BASE_URL}/api/bible/highlights", headers=AUTH)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "count" in d
        assert d["count"] >= 2
        for it in d["items"]:
            for key in ("book_slug", "chapter", "verse", "color", "citation"):
                assert key in it
        citations = {it["citation"] for it in d["items"]}
        assert "John 3:16" in citations
        assert "Matthew 5:3" in citations

    def test_list_filter_by_book(self, client):
        r = client.get(f"{BASE_URL}/api/bible/highlights?book=john", headers=AUTH)
        assert r.status_code == 200
        d = r.json()
        for it in d["items"]:
            assert it["book_slug"] == "john"

    def test_list_requires_auth(self, client):
        r = client.get(f"{BASE_URL}/api/bible/highlights")
        assert r.status_code == 401


# ---------- Regression sanity ----------
class TestRegression:
    def test_auth_me(self, client):
        r = client.get(f"{BASE_URL}/api/auth/me", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["user_id"] == "ui_test_user_1"

    def test_wellness_profile(self, client):
        r = client.get(f"{BASE_URL}/api/wellness/profile", headers=AUTH)
        assert r.status_code == 200

    def test_churches_nearby(self, client):
        # Vatican City coords
        r = client.get(
            f"{BASE_URL}/api/churches/nearby?lat=41.9029&lng=12.4534&radius_m=5000&enrich=false",
            headers=AUTH,
        )
        assert r.status_code == 200
        assert "items" in r.json()

    @pytest.mark.slow
    def test_meals_generate_goal_mode(self, client):
        # AI call — give it a long timeout
        r = client.post(
            f"{BASE_URL}/api/meals/generate",
            headers=AUTH,
            json={"date": "2026-01-16", "goal_mode": "liturgical"},
            timeout=90,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert "plan" in d
        assert d.get("goal_mode") == "liturgical"
