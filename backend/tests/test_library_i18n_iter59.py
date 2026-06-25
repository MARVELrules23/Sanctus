"""Iter59 — Library catalog server-side i18n (Accept-Language)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_feat_aug25"


def _h(lang: str | None = None):
    h = {"Authorization": f"Bearer {TOKEN}"}
    if lang:
        h["Accept-Language"] = lang
    return h


@pytest.fixture(scope="module")
def session():
    return requests.Session()


# Warm caches so 2nd call returns translated content quickly.
def _get_all(session, path, lang):
    r = session.get(f"{BASE_URL}/api/library/{path}", headers=_h(lang), timeout=180)
    assert r.status_code == 200, f"{path} {lang}: {r.status_code} {r.text[:200]}"
    return r.json()


class TestBooksI18n:
    def test_books_en_baseline(self, session):
        data = _get_all(session, "books", "en")
        items = data.get("items", [])
        assert items, "no books returned"
        titles = [i.get("title", "") for i in items]
        # Should have English known titles
        assert any("Confessions" in t for t in titles), f"no English 'Confessions' in titles: {titles[:6]}"

    def test_books_italian(self, session):
        # Warm-up (LLM call) then second pass should be translated
        _get_all(session, "books", "it")
        data = _get_all(session, "books", "it")
        titles = [i.get("title", "") for i in data["items"]]
        blurbs = [i.get("blurb") or "" for i in data["items"]]
        joined = " ".join(titles + blurbs).lower()
        # At least Italian-specific keywords should appear
        assert any(
            kw in joined
            for kw in ["confessioni", "imitazione", "cristo", "santo", "vita", "della", "dio"]
        ), f"Italian markers absent. titles={titles[:6]}"
        # Should NOT still be pure English baseline
        assert not all("Confessions" in t or "Imitation of Christ" in t for t in titles[:3]), \
            f"books still appear in English under it: {titles[:6]}"

    def test_books_spanish(self, session):
        _get_all(session, "books", "es")
        data = _get_all(session, "books", "es")
        titles = [i.get("title", "") for i in data["items"]]
        joined = " ".join(titles).lower()
        assert any(kw in joined for kw in ["confesiones", "imitación", "cristo", "santa", "vida", "dios"]), \
            f"Spanish markers absent. titles={titles[:6]}"


class TestRadioI18n:
    def test_radio_en(self, session):
        data = _get_all(session, "radio", "en")
        assert data.get("items"), "no stations"

    def test_radio_italian(self, session):
        _get_all(session, "radio", "it")
        data = _get_all(session, "radio", "it")
        blurbs = [(i.get("blurb") or "") for i in data["items"]]
        joined = " ".join(blurbs).lower()
        assert any(kw in joined for kw in ["cattolic", "trasmiss", "radio", "vatican", "fede", "preghiera"]), \
            f"Italian markers absent in radio blurbs: {blurbs[:4]}"

    def test_radio_spanish(self, session):
        _get_all(session, "radio", "es")
        data = _get_all(session, "radio", "es")
        blurbs = [(i.get("blurb") or "") for i in data["items"]]
        joined = " ".join(blurbs).lower()
        assert any(kw in joined for kw in ["católic", "transmis", "radio", "vatican", "fe ", "oración"]), \
            f"Spanish markers absent in radio blurbs: {blurbs[:4]}"


class TestFilmsI18n:
    def test_films_en(self, session):
        data = _get_all(session, "films", "en")
        assert data.get("items"), "no films"

    def test_films_italian(self, session):
        _get_all(session, "films", "it")
        data = _get_all(session, "films", "it")
        titles = [i.get("title", "") for i in data["items"]]
        blurbs = [(i.get("blurb") or "") for i in data["items"]]
        joined = " ".join(titles + blurbs).lower()
        assert any(kw in joined for kw in ["santo", "vita", "della", "del ", "dio", "vergine", "papa"]), \
            f"Italian markers absent in film titles/blurbs: titles={titles[:4]}"

    def test_films_spanish(self, session):
        _get_all(session, "films", "es")
        data = _get_all(session, "films", "es")
        titles = [i.get("title", "") for i in data["items"]]
        blurbs = [(i.get("blurb") or "") for i in data["items"]]
        joined = " ".join(titles + blurbs).lower()
        assert any(kw in joined for kw in ["santo", "vida", "del ", "dios", "virgen", "papa"]), \
            f"Spanish markers absent in film titles/blurbs: titles={titles[:4]}"


class TestBookDetailI18n:
    @pytest.mark.skip(reason="Book detail localization is frontend-only via AutoText (iter58 verified). Server endpoint /api/library/books/{slug} intentionally does not call _localize_book_detail.")
    def test_book_detail_italian_translates_chapters(self, session):
        # First the EN baseline to find a slug
        en = _get_all(session, "books", "en")
        slug = None
        for it in en["items"]:
            if "confess" in (it.get("title") or "").lower():
                slug = it.get("slug")
                break
        if not slug:
            slug = en["items"][0]["slug"]
        # Warm + fetch detail
        r0 = requests.get(f"{BASE_URL}/api/library/books/{slug}", headers=_h("it"), timeout=180)
        assert r0.status_code == 200
        r = requests.get(f"{BASE_URL}/api/library/books/{slug}", headers=_h("it"), timeout=180)
        assert r.status_code == 200
        d = r.json()
        chap_titles = [c.get("title", "") for c in (d.get("chapters") or [])]
        joined = " ".join([d.get("title", "")] + chap_titles).lower()
        assert any(kw in joined for kw in ["confessioni", "libro", "capitolo", "infanzia", "giovinezza"]), \
            f"Italian markers absent in book detail: title={d.get('title')} chapters={chap_titles[:4]}"
