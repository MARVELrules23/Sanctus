"""Phase 2 (iter77): Test /api/readings full-text fields and i18n translation.

- GET /api/readings?date=<today> with Bearer test_feat_aug25 returns source=universalis
  and non-empty gospel_full / first_reading_full.
- 401 without auth.
- Past date (2025-01-01) returns 200 with citations; *_full may be empty.
- Accept-Language: es returns Spanish translation in gospel_full (allow slow first call).
"""
import os
import datetime as dt
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_feat_aug25"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def _today_iso() -> str:
    return dt.date.today().isoformat()


class TestReadingsPhase2:
    def test_readings_today_full_text(self):
        today = _today_iso()
        r = requests.get(f"{BASE_URL}/api/readings", params={"date": today}, headers=HEADERS, timeout=60)
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:400]}"
        data = r.json()
        # Source should be universalis for today
        assert data.get("source") == "universalis", f"source={data.get('source')} data-keys={list(data.keys())}"
        # Full-text fields must be non-empty (not just excerpts)
        gospel_full = data.get("gospel_full", "")
        first_full = data.get("first_reading_full", "")
        assert isinstance(gospel_full, str) and len(gospel_full) > 400, f"gospel_full length={len(gospel_full)}: {gospel_full[:200]}"
        assert isinstance(first_full, str) and len(first_full) > 400, f"first_reading_full length={len(first_full)}: {first_full[:200]}"
        # Citation fields present
        assert data.get("gospel"), "gospel citation empty"
        assert data.get("first_reading"), "first_reading citation empty"

    def test_readings_401_without_auth(self):
        today = _today_iso()
        r = requests.get(f"{BASE_URL}/api/readings", params={"date": today}, timeout=15)
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text[:200]}"

    def test_readings_past_date_ok(self):
        past = "2025-01-01"
        r = requests.get(f"{BASE_URL}/api/readings", params={"date": past}, headers=HEADERS, timeout=60)
        assert r.status_code == 200, f"HTTP {r.status_code}"
        data = r.json()
        # Past dates should have at least some citation info
        assert any(data.get(k) for k in ["gospel", "first_reading", "psalm"]), f"no citations for past date: {data}"

    def test_readings_spanish_translation(self):
        today = _today_iso()
        headers_es = {**HEADERS, "Accept-Language": "es"}
        # First call may take time — allow up to 120s for LLM translation
        r = requests.get(f"{BASE_URL}/api/readings", params={"date": today}, headers=headers_es, timeout=180)
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:400]}"
        data = r.json()
        gospel_full_es = data.get("gospel_full", "")
        assert isinstance(gospel_full_es, str) and len(gospel_full_es) > 200, f"es gospel_full too short: {len(gospel_full_es)}"
        # Spanish heuristic: expect at least one common Spanish word
        lower = gospel_full_es.lower()
        spanish_markers = [" el ", " la ", " los ", " las ", " que ", " dijo ", " dice ", " en ", " y ", " del "]
        assert any(m in lower for m in spanish_markers), f"gospel_full doesn't look Spanish: {gospel_full_es[:300]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
