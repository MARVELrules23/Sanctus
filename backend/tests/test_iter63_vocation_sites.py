"""Iteration 63 — Vocation guide + expanded Catholic World Map.

Covers:
- /api/sites returns 78 sites across 55 countries (idempotent seed).
- /api/vocation/guide: has_vocation true/false, fields, state-tailored traditions, i18n.
- /api/preferences persists vocation_state & companion_saint without wiping
  other preference fields.
"""
from __future__ import annotations

import os
import time

import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_feat_aug25"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def _hdr(lang: str | None = None):
    h = dict(H)
    if lang:
        h["Accept-Language"] = lang
    return h


# --------------------------------------------------------------------- #
# /api/sites — expanded Catholic World Map                              #
# --------------------------------------------------------------------- #
class TestSites:
    def test_sites_count_78_countries_55(self):
        r = requests.get(f"{BASE_URL}/api/sites", headers=H, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        items = body.get("items") or []
        assert body.get("total") == len(items)
        assert len(items) == 78, f"expected 78 sites, got {len(items)}"
        countries = {it.get("country") for it in items}
        assert len(countries) == 55, f"expected 55 countries, got {len(countries)}: {sorted(countries)}"

    def test_sites_schema_fields_present(self):
        r = requests.get(f"{BASE_URL}/api/sites", headers=H, timeout=60)
        assert r.status_code == 200
        items = r.json()["items"]
        # Check all required keys on every item
        required = {"site_id", "name", "lat", "lng", "type", "relics", "saints", "miracles", "history", "source_url"}
        for it in items:
            missing = required - set(it.keys())
            assert not missing, f"missing keys {missing} on {it.get('slug')}"
            assert isinstance(it["lat"], (int, float))
            assert isinstance(it["lng"], (int, float))
            assert isinstance(it["relics"], list)
            assert isinstance(it["saints"], list)
            assert isinstance(it["miracles"], list)

    def test_sites_seed_idempotent(self):
        r1 = requests.get(f"{BASE_URL}/api/sites", headers=H, timeout=60)
        r2 = requests.get(f"{BASE_URL}/api/sites", headers=H, timeout=60)
        assert r1.status_code == r2.status_code == 200
        assert r1.json()["total"] == r2.json()["total"] == 78


# --------------------------------------------------------------------- #
# /api/vocation/guide                                                   #
# --------------------------------------------------------------------- #
class TestVocationGuide:
    def _set_prefs(self, **fields):
        r = requests.put(f"{BASE_URL}/api/preferences", headers=H, json=fields, timeout=30)
        assert r.status_code == 200, r.text
        return r.json()

    def _get_prefs(self):
        r = requests.get(f"{BASE_URL}/api/preferences", headers=H, timeout=30)
        assert r.status_code == 200
        return r.json()

    def test_no_vocation_returns_has_vocation_false(self):
        # snapshot existing prefs to restore later
        before = self._get_prefs()
        try:
            # Wipe vocation, preserve other fields
            payload = {**before, "vocation": ""}
            payload.pop("user_id", None)
            requests.put(f"{BASE_URL}/api/preferences", headers=H, json=payload, timeout=30)
            r = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30)
            assert r.status_code == 200, r.text
            data = r.json()
            assert data.get("has_vocation") is False
        finally:
            # restore
            restore = {**before}
            restore.pop("user_id", None)
            requests.put(f"{BASE_URL}/api/preferences", headers=H, json=restore, timeout=30)

    def test_guide_has_required_fields_living_marriage(self):
        # set vocation=marriage state=living
        before = self._get_prefs()
        merged = {**before, "vocation": "marriage", "vocation_state": "living"}
        merged.pop("user_id", None)
        self._set_prefs(**merged)
        r = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("has_vocation") is True
        assert d.get("label")
        assert d.get("intro")
        mp = d.get("morning_prayer") or {}
        assert mp.get("title") and mp.get("body")
        assert isinstance(d.get("companions"), list) and len(d["companions"]) >= 1
        for c in d["companions"]:
            assert {"slug", "name", "why", "prayer"} <= set(c.keys())
        assert isinstance(d.get("ideas"), list) and len(d["ideas"]) >= 1
        assert isinstance(d.get("traditions"), list) and len(d["traditions"]) >= 1
        assert "companion_saint" in d
        assert d.get("state") == "living"

    def test_traditions_differ_between_discerning_and_living(self):
        # marriage / discerning
        before = self._get_prefs()
        merged_d = {**before, "vocation": "marriage", "vocation_state": "discerning"}
        merged_d.pop("user_id", None)
        self._set_prefs(**merged_d)
        r_d = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30)
        assert r_d.status_code == 200
        trad_d = r_d.json()["traditions"]

        # marriage / living
        merged_l = {**before, "vocation": "marriage", "vocation_state": "living"}
        merged_l.pop("user_id", None)
        self._set_prefs(**merged_l)
        r_l = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30)
        assert r_l.status_code == 200
        trad_l = r_l.json()["traditions"]

        titles_d = {t["title"] for t in trad_d}
        titles_l = {t["title"] for t in trad_l}
        assert titles_d != titles_l, f"traditions did not differ: {titles_d}"

    def test_guide_i18n_es_and_it(self):
        # ensure vocation=marriage, state=living
        before = self._get_prefs()
        merged = {**before, "vocation": "marriage", "vocation_state": "living"}
        merged.pop("user_id", None)
        self._set_prefs(**merged)

        # English baseline
        r_en = requests.get(f"{BASE_URL}/api/vocation/guide", headers=H, timeout=30)
        assert r_en.status_code == 200
        en = r_en.json()
        en_title = en["morning_prayer"]["title"]

        for lang in ("es", "it"):
            # First call may be slow (translation cache cold)
            r = requests.get(f"{BASE_URL}/api/vocation/guide", headers=_hdr(lang), timeout=180)
            assert r.status_code == 200, f"{lang}: {r.text}"
            d = r.json()
            assert d.get("has_vocation") is True
            tr_title = d["morning_prayer"]["title"]
            tr_body = d["morning_prayer"]["body"]
            # Heuristic: translated string should differ from English baseline
            assert tr_title != en_title, f"{lang} title did not translate: {tr_title}"
            assert isinstance(tr_body, str) and len(tr_body) > 10


# --------------------------------------------------------------------- #
# /api/preferences persistence: vocation_state + companion_saint        #
# --------------------------------------------------------------------- #
class TestPreferencesPersistence:
    def test_companion_saint_does_not_wipe_other_fields(self):
        # Read current state
        r0 = requests.get(f"{BASE_URL}/api/preferences", headers=H, timeout=30)
        assert r0.status_code == 200
        base = r0.json()

        # Force a known set of preferences
        target = {
            **base,
            "marital_status": "single",
            "vocation": "marriage",
            "vocation_state": "living",
            "dietary": "none",
            "companion_saint": "",
        }
        target.pop("user_id", None)
        r1 = requests.put(f"{BASE_URL}/api/preferences", headers=H, json=target, timeout=30)
        assert r1.status_code == 200, r1.text

        # Now read prefs, merge in companion_saint, PUT — mirrors frontend behaviour
        r_mid = requests.get(f"{BASE_URL}/api/preferences", headers=H, timeout=30)
        mid = r_mid.json()
        merged = {**mid, "companion_saint": "st-joseph"}
        merged.pop("user_id", None)
        r2 = requests.put(f"{BASE_URL}/api/preferences", headers=H, json=merged, timeout=30)
        assert r2.status_code == 200

        # Verify all fields persisted
        r3 = requests.get(f"{BASE_URL}/api/preferences", headers=H, timeout=30)
        assert r3.status_code == 200
        final = r3.json()
        assert final.get("companion_saint") == "st-joseph"
        assert final.get("marital_status") == "single"
        assert final.get("vocation") == "marriage"
        assert final.get("vocation_state") == "living"
        assert final.get("dietary") == "none"

    def test_vocation_state_toggle_persists(self):
        # set discerning
        r0 = requests.get(f"{BASE_URL}/api/preferences", headers=H, timeout=30)
        base = r0.json()
        merged = {**base, "vocation": "marriage", "vocation_state": "discerning"}
        merged.pop("user_id", None)
        r1 = requests.put(f"{BASE_URL}/api/preferences", headers=H, json=merged, timeout=30)
        assert r1.status_code == 200
        rg = requests.get(f"{BASE_URL}/api/preferences", headers=H, timeout=30)
        assert rg.json().get("vocation_state") == "discerning"

        # flip back to living
        merged2 = {**rg.json(), "vocation_state": "living"}
        merged2.pop("user_id", None)
        r2 = requests.put(f"{BASE_URL}/api/preferences", headers=H, json=merged2, timeout=30)
        assert r2.status_code == 200
        rg2 = requests.get(f"{BASE_URL}/api/preferences", headers=H, timeout=30)
        assert rg2.json().get("vocation_state") == "living"


# --------------------------------------------------------------------- #
# Cleanup: reset account to vocation=marriage state=living (per request)#
# --------------------------------------------------------------------- #
def test_zz_reset_test_account():
    r0 = requests.get(f"{BASE_URL}/api/preferences", headers=H, timeout=30)
    assert r0.status_code == 200
    base = r0.json()
    target = {**base, "vocation": "marriage", "vocation_state": "living"}
    target.pop("user_id", None)
    r1 = requests.put(f"{BASE_URL}/api/preferences", headers=H, json=target, timeout=30)
    assert r1.status_code == 200
    final = requests.get(f"{BASE_URL}/api/preferences", headers=H, timeout=30).json()
    assert final.get("vocation") == "marriage"
    assert final.get("vocation_state") == "living"
