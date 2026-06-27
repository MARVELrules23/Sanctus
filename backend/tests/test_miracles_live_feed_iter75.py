"""Iter75 — Miracles 'Live Feed' upgrade tests.

Covers new public GET /api/miracles capabilities:
- Returns server_time (ISO string).
- Each item includes a `process` object: name, stages (label/done/current),
  current_label, note.
- `q=` accent-insensitive search across title/summary/location.
- `type=` and `verdict=` filters; filters combine with q correctly.
- Process ladder is chosen by type+verdict (apparition vs eucharistic vs
  canonization vs generic) and the current stage corresponds to the verdict.
- Backward compatibility: GET /api/miracles still returns all published items
  with no filters.
"""
from __future__ import annotations

import os
import re

import pytest
import requests

BASE_URL = os.environ.get(
    "EXPO_BACKEND_URL", "https://divine-office.preview.emergentagent.com"
).rstrip("/")
ADMIN_TOKEN = "test_feat_aug25"


def _hdr(lang: str | None = None):
    h = {"Authorization": f"Bearer {ADMIN_TOKEN}", "Content-Type": "application/json",
         "Accept-Language": "en"}
    if lang:
        h["Accept-Language"] = lang
    return h


def _get(path: str, **params):
    return requests.get(f"{BASE_URL}{path}", headers=_hdr(),
                        params={k: v for k, v in params.items() if v is not None},
                        timeout=30)


# --------------------------- Shape & server_time ---------------------------

class TestShape:
    def test_returns_server_time_iso(self):
        r = _get("/api/miracles")
        assert r.status_code == 200, r.text
        body = r.json()
        st = body.get("server_time")
        assert isinstance(st, str) and len(st) >= 19, f"server_time missing/invalid: {st}"
        # Loose ISO-8601 check (YYYY-MM-DDTHH:MM:SS...)
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", st), st

    def test_items_have_process_object(self):
        r = _get("/api/miracles")
        items = r.json()["items"]
        assert items, "expected at least one published item"
        for it in items:
            proc = it.get("process")
            assert isinstance(proc, dict), f"missing process on {it.get('claim_id')}"
            assert isinstance(proc.get("name"), str) and proc["name"]
            stages = proc.get("stages")
            assert isinstance(stages, list) and len(stages) >= 3
            cur_count = 0
            for s in stages:
                assert {"label", "done", "current"}.issubset(s.keys())
                assert isinstance(s["label"], str) and s["label"]
                assert isinstance(s["done"], bool)
                assert isinstance(s["current"], bool)
                cur_count += 1 if s["current"] else 0
            assert cur_count <= 1, "more than one stage marked current"
            assert isinstance(proc.get("current_label"), str) and proc["current_label"]
            # note may be empty for some, but key present
            assert "note" in proc


# --------------------------- Ladders by type+verdict -----------------------

class TestLadderSelection:
    def _by_slug(self, items, hint):
        for it in items:
            if hint in (it.get("title") or "").lower() or hint in (it.get("slug") or "").lower():
                return it
        return None

    def test_eucharistic_lanciano_uses_eucharistic_ladder(self):
        r = _get("/api/miracles", q="lanciano")
        assert r.status_code == 200
        items = r.json()["items"]
        assert items, "lanciano search returned no items"
        it = items[0]
        assert it["type"] == "eucharistic"
        proc = it["process"]
        labels = [s["label"] for s in proc["stages"]]
        assert "Scientific examination" in labels, labels
        # approved → final stage is current
        assert proc["stages"][-1]["current"] is True
        assert proc["current_label"] == "Church judgment"

    def test_marian_uses_apparition_ladder(self):
        r = _get("/api/miracles", type="marian")
        items = r.json()["items"]
        assert items, "type=marian returned no items"
        for it in items:
            labels = [s["label"] for s in it["process"]["stages"]]
            assert "Diocesan investigation" in labels, labels
            # 2024 DDF Norms phrase in name
            assert "DDF" in it["process"]["name"]

    def test_investigating_filter_has_current_in_middle(self):
        r = _get("/api/miracles", verdict="investigating")
        body = r.json()
        items = body["items"]
        # Smoke note said 3 investigating items
        assert len(items) >= 3, f"expected >=3 investigating items, got {len(items)}"
        for it in items:
            assert it["verdict"] == "investigating"
            stages = it["process"]["stages"]
            # current must not be the last (final conclusion not reached)
            assert stages[-1]["current"] is False, \
                f"investigating item has final stage current: {it['claim_id']}"
            assert any(s["current"] for s in stages), "no current stage marked"


# --------------------------- Search filter --------------------------------

class TestSearch:
    def test_search_lanciano_match(self):
        r = _get("/api/miracles", q="lanciano")
        items = r.json()["items"]
        assert items, "q=lanciano returned no items"
        titles = " ".join((it["title"] or "").lower() for it in items)
        assert "lanciano" in titles

    def test_search_accent_insensitive_fatima(self):
        """q=fatima (no accent) should match 'Fátima' (with accent)."""
        r = _get("/api/miracles", q="fatima")
        items = r.json()["items"]
        assert items, "q=fatima returned no items (accent-insensitive search broken)"
        joined = " ".join(
            f"{it.get('title','')} {it.get('location','')}" for it in items
        ).lower()
        assert "f" in joined  # smoke
        # At least one item references Fátima
        assert any("fatima" in (it.get("title") or "").lower() or
                   "fátima" in (it.get("title") or "").lower() or
                   "fatima" in (it.get("location") or "").lower() or
                   "fátima" in (it.get("location") or "").lower()
                   for it in items)

    def test_search_no_match(self):
        r = _get("/api/miracles", q="zzzz_no_such_miracle_xyz")
        body = r.json()
        assert body["items"] == []
        assert body["total"] == 0


# --------------------------- Combined filters -----------------------------

class TestCombined:
    def test_combine_verdict_and_type(self):
        # Eucharistic + investigating → Buenos Aires 1996 expected
        r = _get("/api/miracles", verdict="investigating", type="eucharistic")
        items = r.json()["items"]
        assert items, "no items for eucharistic+investigating"
        for it in items:
            assert it["verdict"] == "investigating"
            assert it["type"] == "eucharistic"

    def test_combine_search_and_verdict(self):
        # q=Buenos + verdict=investigating
        r = _get("/api/miracles", q="buenos", verdict="investigating")
        items = r.json()["items"]
        assert items, "no items for q=buenos & investigating"
        for it in items:
            assert it["verdict"] == "investigating"
            assert "buenos" in (it["title"] or "").lower() or \
                   "buenos" in (it["location"] or "").lower()

    def test_invalid_filter_ignored(self):
        # invalid verdict should be ignored, not error
        baseline = len(_get("/api/miracles").json()["items"])
        r = _get("/api/miracles", verdict="not-a-verdict")
        assert r.status_code == 200
        assert len(r.json()["items"]) == baseline

    def test_no_filters_returns_all_published(self):
        r = _get("/api/miracles")
        body = r.json()
        items = body["items"]
        assert body["total"] == len(items)
        # all published
        for it in items:
            assert it.get("state", "published") == "published"
        # seed-floor
        assert len(items) >= 6, f"expected >=6 published seeded items, got {len(items)}"
