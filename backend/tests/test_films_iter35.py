"""Iteration 35 — Films regression verification.

Verifies that all 12 SEED_FILMS in library_seed_data.py:
- Are returned by GET /api/library/films
- Have the exact expected slug + youtube_id + duration_label
- Filter correctly by category (3 saints, 3 doctrine, 3 animated, 3 documentary)
- Each youtube_id resolves on YouTube oEmbed API (200 OK).
- Old slugs (ccc-juan-diego-anim, brother-francis-mass, catholicism-barron-trailer) MUST NOT appear.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://faithful-fitness-3.preview.emergentagent.com").rstrip("/")
ADMIN_TOKEN = "TEST_iter32_admin_tok"

# Expected catalog (slug, youtube_id, duration_label, category)
EXPECTED_FILMS = [
    ("molokai-damien",        "AweoZYsiCu4", "1h 58m", "saints"),
    ("padre-pio-miracle",     "5C27CJyspZc", "3h 22m", "saints"),
    ("bernadette-1943",       "muoFcCkR8NQ", "2h 36m", "saints"),
    ("barron-mass",           "pIGXtDR2GCk", "15m",    "doctrine"),
    ("barron-eucharist",      "UzCPu_lEhe8", "1h 12m", "doctrine"),
    ("scott-hahn-conversion", "XilzGLfgd7A", "56m",    "doctrine"),
    ("st-francis-animated",   "lutB_jV7IyE", "1h 22m", "animated"),
    ("ccc-bernadette-anim",   "zdYxJIsNSqs", "45m",    "animated"),
    ("juan-diego-anim",       "FI_gXWGmBNg", "28m",    "animated"),
    ("guadalupe-doc",         "ym-b05cTZdM", "58m",    "documentary"),
    ("shroud-of-turin-doc",   "io8WUa-wTIk", "1h 25m", "documentary"),
    ("john-paul-ii-papacy",   "2gpvfvhcRGc", "1h 30m", "documentary"),
]

OLD_SLUGS_THAT_MUST_NOT_EXIST = [
    "ccc-juan-diego-anim",
    "brother-francis-mass",
    "catholicism-barron-trailer",
]


@pytest.fixture(scope="module")
def auth_session():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {ADMIN_TOKEN}",
                      "Content-Type": "application/json"})
    return s


class TestFilmsList:
    def test_returns_exactly_12_films(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/library/films")
        assert r.status_code == 200, r.text
        data = r.json()
        # Response could be a list or {"films": [...]}
        items = data if isinstance(data, list) else data.get("films", data.get("items", []))
        assert len(items) == 12, f"Expected 12 films, got {len(items)}: {[i.get('slug') for i in items]}"

    def test_old_slugs_not_present(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/library/films")
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("films", data.get("items", []))
        slugs = {i.get("slug") for i in items}
        for old in OLD_SLUGS_THAT_MUST_NOT_EXIST:
            assert old not in slugs, f"Removed slug '{old}' still present in catalog"

    @pytest.mark.parametrize("slug,yt_id,duration,category", EXPECTED_FILMS)
    def test_each_film_has_expected_fields(self, auth_session, slug, yt_id, duration, category):
        r = auth_session.get(f"{BASE_URL}/api/library/films")
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("films", data.get("items", []))
        match = next((i for i in items if i.get("slug") == slug), None)
        assert match is not None, f"slug '{slug}' missing from catalog"
        assert match.get("youtube_id") == yt_id, (
            f"{slug}: youtube_id mismatch — expected {yt_id}, got {match.get('youtube_id')}"
        )
        assert match.get("duration_label") == duration, (
            f"{slug}: duration_label mismatch — expected '{duration}', got '{match.get('duration_label')}'"
        )
        assert match.get("category") == category, (
            f"{slug}: category mismatch — expected '{category}', got '{match.get('category')}'"
        )


class TestFilmsByCategory:
    @pytest.mark.parametrize("category,expected_count", [
        ("saints", 3),
        ("doctrine", 3),
        ("animated", 3),
        ("documentary", 3),
    ])
    def test_category_filter_count(self, auth_session, category, expected_count):
        r = auth_session.get(f"{BASE_URL}/api/library/films", params={"category": category})
        assert r.status_code == 200, r.text
        data = r.json()
        items = data if isinstance(data, list) else data.get("films", data.get("items", []))
        assert len(items) == expected_count, (
            f"category={category}: expected {expected_count}, got {len(items)} slugs={[i.get('slug') for i in items]}"
        )
        for it in items:
            assert it.get("category") == category


class TestFilmDetail:
    @pytest.mark.parametrize("slug,yt_id", [(s, y) for (s, y, _, _) in EXPECTED_FILMS])
    def test_film_detail_endpoint(self, auth_session, slug, yt_id):
        r = auth_session.get(f"{BASE_URL}/api/library/films/{slug}")
        assert r.status_code == 200, f"{slug}: {r.status_code} {r.text}"
        film = r.json()
        assert film.get("slug") == slug
        assert film.get("youtube_id") == yt_id


class TestYouTubeOEmbed:
    """Independently verify each youtube_id resolves on the YouTube oEmbed API."""

    @pytest.mark.parametrize("slug,yt_id", [(s, y) for (s, y, _, _) in EXPECTED_FILMS])
    def test_youtube_oembed_returns_200(self, slug, yt_id):
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={yt_id}&format=json"
        # Be tolerant: retry once on network blip.
        for attempt in range(2):
            try:
                resp = requests.get(url, timeout=12,
                                    headers={"User-Agent": "Mozilla/5.0 SanctusTester/1.0"})
                if resp.status_code == 200:
                    body = resp.json()
                    assert "title" in body and body["title"], f"{slug}/{yt_id}: oembed missing title"
                    return
                if attempt == 1:
                    pytest.fail(f"{slug}/{yt_id}: oEmbed returned {resp.status_code} -- video unavailable / removed")
            except requests.RequestException as e:
                if attempt == 1:
                    pytest.fail(f"{slug}/{yt_id}: network error {e}")
