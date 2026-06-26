"""Iteration 64 — Expanded Catholic World Map (99/59) with 'churches under
persecution' flag + expanded vocation traditions per (vocation, state).

Covers:
- GET /api/sites returns 99 sites across 59 countries; seed idempotent.
- Exactly 6 items have persecuted=True with non-empty persecution_note.
- GET /api/sites/divine-office (per persecuted/normal site) — actually
  GET /api/sites/{slug} surfaces persecuted + persecution_note correctly.
- i18n (es/it) localizes persecution_note + name/history via translation cache.
- GET /api/vocation/guide returns 11 traditions for marriage/living and
  a different (smaller) list for marriage/discerning. religious life and
  singleness both return non-empty distinct lists per state.
- i18n on vocation traditions (es/it).
- RESET test account to vocation=marriage state=living at end.
"""
from __future__ import annotations

import os

import pytest
import requests

BASE_URL = os.environ.get(
    "EXPO_PUBLIC_BACKEND_URL", "https://divine-office.preview.emergentagent.com"
).rstrip("/")
TOKEN = "test_feat_aug25"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

PERSECUTED_SLUGS = {
    "our-lady-salvation-baghdad",
    "al-tahira-qaraqosh",
    "st-thecla-maaloula",
    "owo-nigeria",
    "managua-cathedral",
    "sacred-heart-lahore",
}


def _hdr(lang=None):
    h = dict(H)
    if lang:
        h["Accept-Language"] = lang
    return h


def _get_prefs():
    r = requests.get(f"{BASE_URL}/api/preferences", headers=H, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _put_prefs(**fields):
    base = _get_prefs()
    merged = {**base, **fields}
    merged.pop("user_id", None)
    r = requests.put(f"{BASE_URL}/api/preferences", headers=H, json=merged, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# --------------------------------------------------------------------- #
# Sites — count, persecuted flag, idempotent seed                       #
# --------------------------------------------------------------------- #
class TestSitesExpansion:
    def test_count_99_countries_59(self):
        r = requests.get(f"{BASE_URL}/api/sites", headers=H, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        items = body["items"]
        assert body.get("total") == len(items) == 99, f"expected 99, got {len(items)}"
        countries = {i["country"] for i in items}
        assert len(countries) == 59, f"expected 59 countries, got {len(countries)}"

    def test_persecuted_flag_exactly_6(self):
        r = requests.get(f"{BASE_URL}/api/sites", headers=H, timeout=60)
        items = r.json()["items"]
        # All items should include persecuted (bool) and persecution_note (str)
        for it in items:
            assert "persecuted" in it, f"missing persecuted on {it.get('slug')}"
            assert isinstance(it["persecuted"], bool), f"persecuted not bool on {it.get('slug')}"
            assert "persecution_note" in it, f"missing persecution_note on {it.get('slug')}"
            assert isinstance(it["persecution_note"], str)
        flagged = [i for i in items if i["persecuted"]]
        assert len(flagged) == 6, f"expected 6 persecuted, got {len(flagged)}"
        slugs = {i["slug"] for i in flagged}
        assert slugs == PERSECUTED_SLUGS, f"unexpected slugs: {slugs}"
        # Each persecuted site has a non-empty persecution_note
        for it in flagged:
            assert it["persecution_note"].strip(), f"empty persecution_note on {it['slug']}"

    def test_seed_idempotent(self):
        r1 = requests.get(f"{BASE_URL}/api/sites", headers=H, timeout=60)
        r2 = requests.get(f"{BASE_URL}/api/sites", headers=H, timeout=60)
        assert r1.status_code == r2.status_code == 200
        assert r1.json()["total"] == r2.json()["total"] == 99

    def test_persecuted_site_detail(self):
        # Pick one persecuted site and one normal
        r = requests.get(
            f"{BASE_URL}/api/sites/our-lady-salvation-baghdad", headers=H, timeout=30
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("persecuted") is True
        assert isinstance(data.get("persecution_note"), str) and data["persecution_note"].strip()

        r2 = requests.get(f"{BASE_URL}/api/sites/lourdes", headers=H, timeout=30)
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2.get("persecuted") is False


# --------------------------------------------------------------------- #
# Sites — i18n on persecution_note + name/history                        #
# --------------------------------------------------------------------- #
class TestSitesI18n:
    @pytest.mark.parametrize("lang", ["es", "it"])
    def test_persecution_note_localized(self, lang):
        # English baseline
        r_en = requests.get(f"{BASE_URL}/api/sites", headers=H, timeout=60)
        en_items = {i["slug"]: i for i in r_en.json()["items"]}
        en_baghdad = en_items["our-lady-salvation-baghdad"]

        # Translated (first call may be cold via LLM)
        r = requests.get(f"{BASE_URL}/api/sites", headers=_hdr(lang), timeout=240)
        assert r.status_code == 200, r.text
        tr_items = {i["slug"]: i for i in r.json()["items"]}
        tr_baghdad = tr_items["our-lady-salvation-baghdad"]
        assert tr_baghdad["persecuted"] is True
        # persecution_note translated
        assert tr_baghdad["persecution_note"], f"empty note in {lang}"
        assert tr_baghdad["persecution_note"] != en_baghdad["persecution_note"], (
            f"persecution_note not translated for {lang}"
        )
        # name or history translated (at least one differs)
        assert (
            tr_baghdad["name"] != en_baghdad["name"]
            or tr_baghdad["history"] != en_baghdad["history"]
        )


# --------------------------------------------------------------------- #
# Vocation traditions — expanded, state-tailored                         #
# --------------------------------------------------------------------- #
class TestVocationTraditions:
    def test_marriage_living_has_11_traditions(self):
        _put_prefs(vocation="marriage", vocation_state="living")
        r = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["has_vocation"] is True
        traditions = data["traditions"]
        assert len(traditions) == 11, f"expected 11 marriage/living traditions, got {len(traditions)}"
        # ideas + companions still present
        assert isinstance(data["ideas"], list) and len(data["ideas"]) >= 1
        assert isinstance(data["companions"], list) and len(data["companions"]) >= 1

    def test_marriage_discerning_smaller_and_different(self):
        _put_prefs(vocation="marriage", vocation_state="living")
        r_l = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30).json()
        _put_prefs(vocation="marriage", vocation_state="discerning")
        r_d = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30).json()
        titles_l = {t["title"] for t in r_l["traditions"]}
        titles_d = {t["title"] for t in r_d["traditions"]}
        assert titles_l != titles_d, "marriage traditions did not differ between living and discerning"
        assert len(r_d["traditions"]) < len(r_l["traditions"]), (
            f"discerning ({len(r_d['traditions'])}) not smaller than living ({len(r_l['traditions'])})"
        )

    @pytest.mark.parametrize("vocation", ["religious life", "singleness"])
    def test_other_vocations_states_distinct(self, vocation):
        _put_prefs(vocation=vocation, vocation_state="discerning")
        r_d = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30).json()
        _put_prefs(vocation=vocation, vocation_state="living")
        r_l = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30).json()
        assert r_d["has_vocation"] and r_l["has_vocation"]
        assert len(r_d["traditions"]) >= 1 and len(r_l["traditions"]) >= 1
        titles_d = {t["title"] for t in r_d["traditions"]}
        titles_l = {t["title"] for t in r_l["traditions"]}
        assert titles_d != titles_l, f"{vocation} traditions did not differ between states"

    @pytest.mark.parametrize("lang", ["es", "it"])
    def test_guide_traditions_localized(self, lang):
        _put_prefs(vocation="marriage", vocation_state="living")
        r_en = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30).json()
        en_titles = {t["title"] for t in r_en["traditions"]}
        r = requests.get(f"{BASE_URL}/api/vocation/guide", headers=_hdr(lang), timeout=240)
        assert r.status_code == 200, r.text
        d = r.json()
        tr_titles = {t["title"] for t in d["traditions"]}
        # At least 1 title should differ from EN baseline
        assert tr_titles != en_titles, f"{lang} traditions did not translate"
        # state preserved
        assert d.get("state") == "living"


# --------------------------------------------------------------------- #
# Cleanup: reset account to vocation=marriage state=living              #
# --------------------------------------------------------------------- #
def test_zz_reset_account():
    _put_prefs(vocation="marriage", vocation_state="living")
    p = _get_prefs()
    assert p.get("vocation") == "marriage"
    assert p.get("vocation_state") == "living"
