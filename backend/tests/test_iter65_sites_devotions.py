"""Iteration 65 — Expanded Catholic World Map (133 sites/62 countries) +
companion devotions on every vocation companion (with i18n).

Covers:
- GET /api/sites returns 133 items across 62 countries, idempotent.
- 6 sites carry persecuted=true (unchanged from iter64).
- New slugs resolve via GET /api/sites/{slug}: st-nicholas-bari, turin-cathedral,
  divine-mercy-krakow, medjugorje, santo-nino-cebu — each returns non-empty
  name and detail fields.
- GET /api/vocation/guide returns companions[] where every companion has a
  non-empty devotions[] of {title, body}, for vocation in
  (marriage, religious life, singleness).
- Accept-Language: es localizes companion devotions; same for it; EN unchanged.
"""
from __future__ import annotations

import os

import requests

BASE_URL = os.environ.get(
    "EXPO_PUBLIC_BACKEND_URL", "https://divine-office.preview.emergentagent.com"
).rstrip("/")
TOKEN = "test_feat_aug25"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def _hdr(lang: str | None = None):
    h = dict(H)
    if lang:
        h["Accept-Language"] = lang
    return h


# --------------------------------------------------------------------- #
# /api/sites — 133 sites / 62 countries / idempotent / 6 persecuted     #
# --------------------------------------------------------------------- #
class TestSitesExpansion:
    def test_sites_count_133_countries_62(self):
        r = requests.get(f"{BASE_URL}/api/sites", headers=H, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        items = body.get("items") or []
        assert body.get("total") == len(items)
        assert len(items) == 133, f"expected 133 sites, got {len(items)}"
        countries = {it.get("country") for it in items}
        assert len(countries) == 62, (
            f"expected 62 countries, got {len(countries)}: {sorted(countries)}"
        )

    def test_sites_seed_idempotent_twice(self):
        r1 = requests.get(f"{BASE_URL}/api/sites", headers=H, timeout=60)
        r2 = requests.get(f"{BASE_URL}/api/sites", headers=H, timeout=60)
        assert r1.status_code == r2.status_code == 200
        assert r1.json()["total"] == r2.json()["total"] == 133
        # No duplicate slugs/site_ids
        slugs1 = [it.get("site_id") for it in r1.json()["items"]]
        assert len(slugs1) == len(set(slugs1)), "duplicate site_ids returned"

    def test_persecuted_count_six(self):
        r = requests.get(f"{BASE_URL}/api/sites", headers=H, timeout=60)
        items = r.json()["items"]
        persecuted = [it for it in items if it.get("persecuted") is True]
        assert len(persecuted) == 6, f"expected 6 persecuted, got {len(persecuted)}"
        for it in persecuted:
            assert (it.get("persecution_note") or "").strip(), (
                f"empty persecution_note on {it.get('site_id')}"
            )


# --------------------------------------------------------------------- #
# New site slugs resolve via GET /api/sites/{slug}                      #
# --------------------------------------------------------------------- #
class TestNewSitesBySlug:
    NEW_SLUGS = [
        "st-nicholas-bari",
        "turin-cathedral",
        "divine-mercy-krakow",
        "medjugorje",
        "santo-nino-cebu",
    ]

    def test_each_new_slug_resolves_with_name_and_fields(self):
        for slug in self.NEW_SLUGS:
            r = requests.get(f"{BASE_URL}/api/sites/{slug}", headers=H, timeout=60)
            assert r.status_code == 200, f"{slug}: {r.status_code} {r.text}"
            d = r.json()
            assert (d.get("name") or "").strip(), f"empty name for {slug}"
            assert (d.get("country") or "").strip(), f"empty country for {slug}"
            assert (d.get("city") or "").strip(), f"empty city for {slug}"
            assert (d.get("history") or "").strip(), f"empty history for {slug}"
            assert isinstance(d.get("lat"), (int, float))
            assert isinstance(d.get("lng"), (int, float))


# --------------------------------------------------------------------- #
# /api/vocation/guide — devotions on every companion                    #
# --------------------------------------------------------------------- #
class TestCompanionDevotions:
    def _set_vocation(self, vocation: str, state: str = "living"):
        r0 = requests.get(f"{BASE_URL}/api/preferences", headers=H, timeout=30)
        assert r0.status_code == 200
        base = r0.json()
        merged = {**base, "vocation": vocation, "vocation_state": state}
        merged.pop("user_id", None)
        r = requests.put(f"{BASE_URL}/api/preferences", headers=H, json=merged, timeout=30)
        assert r.status_code == 200, r.text

    def _assert_devotions_for_vocation(self, vocation: str):
        self._set_vocation(vocation, "living")
        r = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("has_vocation") is True
        comps = d.get("companions") or []
        assert len(comps) >= 1, f"no companions for {vocation}"
        for c in comps:
            slug = c.get("slug")
            devs = c.get("devotions")
            assert isinstance(devs, list) and len(devs) >= 1, (
                f"{vocation}/{slug}: devotions missing/empty"
            )
            for dv in devs:
                assert (dv.get("title") or "").strip(), (
                    f"{vocation}/{slug}: devotion has empty title"
                )
                assert (dv.get("body") or "").strip(), (
                    f"{vocation}/{slug}: devotion has empty body"
                )

    def test_marriage_companions_have_devotions(self):
        self._assert_devotions_for_vocation("marriage")
        # specifically st-joseph (default)
        r = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30)
        comps = r.json()["companions"]
        joseph = next((c for c in comps if c.get("slug") == "st-joseph"), None)
        assert joseph is not None, "St Joseph companion missing for marriage"
        assert len(joseph.get("devotions") or []) >= 2

    def test_religious_life_companions_have_devotions(self):
        self._assert_devotions_for_vocation("religious life")

    def test_singleness_companions_have_devotions(self):
        self._assert_devotions_for_vocation("singleness")


# --------------------------------------------------------------------- #
# I18n: companion devotions localized for es and it (EN unchanged)      #
# --------------------------------------------------------------------- #
class TestCompanionDevotionsI18n:
    def _set_marriage_living(self):
        r0 = requests.get(f"{BASE_URL}/api/preferences", headers=H, timeout=30)
        base = r0.json()
        merged = {**base, "vocation": "marriage", "vocation_state": "living"}
        merged.pop("user_id", None)
        requests.put(f"{BASE_URL}/api/preferences", headers=H, json=merged, timeout=30)

    def _devotions_of(self, comps, slug):
        c = next((x for x in comps if x.get("slug") == slug), None)
        return c.get("devotions") if c else None

    def test_es_and_it_localize_companion_devotions(self):
        self._set_marriage_living()
        # English baseline
        r_en = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30)
        assert r_en.status_code == 200
        en_devs = self._devotions_of(r_en.json()["companions"], "st-joseph")
        assert en_devs and len(en_devs) >= 2
        en_titles = [d["title"] for d in en_devs]
        en_bodies = [d["body"] for d in en_devs]

        for lang in ("es", "it"):
            # Cold path may need longer
            r = requests.get(
                f"{BASE_URL}/api/vocation/guide", headers=_hdr(lang), timeout=180
            )
            assert r.status_code == 200, f"{lang}: {r.text}"
            d = r.json()
            assert d.get("has_vocation") is True
            tr_devs = self._devotions_of(d["companions"], "st-joseph")
            assert tr_devs and len(tr_devs) == len(en_devs), (
                f"{lang}: devotion count mismatch"
            )
            tr_titles = [x["title"] for x in tr_devs]
            tr_bodies = [x["body"] for x in tr_devs]
            # Heuristic: at least one translation field differs from EN
            assert any(a != b for a, b in zip(tr_titles, en_titles)) or any(
                a != b for a, b in zip(tr_bodies, en_bodies)
            ), f"{lang}: companion devotions did not localize"
            # No empties
            for x in tr_devs:
                assert x.get("title") and x.get("body"), (
                    f"{lang}: empty translated devotion"
                )

        # EN unchanged after the localized calls (no mutation of module CONTENT)
        r_en2 = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30)
        en_devs2 = self._devotions_of(r_en2.json()["companions"], "st-joseph")
        en_titles2 = [d["title"] for d in en_devs2]
        en_bodies2 = [d["body"] for d in en_devs2]
        assert en_titles2 == en_titles, "EN companion devotion titles mutated"
        assert en_bodies2 == en_bodies, "EN companion devotion bodies mutated"


# --------------------------------------------------------------------- #
# Cleanup: reset account to vocation=marriage / living / st-joseph      #
# --------------------------------------------------------------------- #
def test_zz_reset_test_account():
    r0 = requests.get(f"{BASE_URL}/api/preferences", headers=H, timeout=30)
    assert r0.status_code == 200
    base = r0.json()
    target = {
        **base,
        "vocation": "marriage",
        "vocation_state": "living",
        "companion_saint": "st-joseph",
    }
    target.pop("user_id", None)
    r1 = requests.put(f"{BASE_URL}/api/preferences", headers=H, json=target, timeout=30)
    assert r1.status_code == 200
    final = requests.get(f"{BASE_URL}/api/preferences", headers=H, timeout=30).json()
    assert final.get("vocation") == "marriage"
    assert final.get("vocation_state") == "living"
    assert final.get("companion_saint") == "st-joseph"
