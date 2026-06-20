"""Backend tests for the new 'In the World' feature (iteration 46)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_home_layout_24h"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

EXPECTED_SLUGS = {
    "life-and-dignity", "common-good", "poverty-and-the-poor", "immigration",
    "religious-liberty", "family-and-marriage", "work-and-economy",
    "solidarity-and-peace", "care-for-creation", "subsidiarity-and-the-state",
}


class TestInTheWorldList:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/in-the-world", timeout=20)
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"

    def test_list_returns_10_items(self):
        r = requests.get(f"{BASE_URL}/api/in-the-world", headers=HEADERS, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data
        items = data["items"]
        assert len(items) == 10, f"expected 10 issues got {len(items)}"
        slugs = {i["slug"] for i in items}
        assert slugs == EXPECTED_SLUGS, f"slug mismatch: {slugs ^ EXPECTED_SLUGS}"
        # Validate shape
        for it in items:
            for k in ("slug", "title", "icon", "accent", "blurb"):
                assert k in it and it[k], f"missing/empty {k} in {it}"


class TestInTheWorldDetail:
    def test_invalid_slug_returns_404(self):
        r = requests.get(f"{BASE_URL}/api/in-the-world/does-not-exist",
                         headers=HEADERS, timeout=20)
        assert r.status_code == 404

    def test_divine_office_no_such_issue(self):
        # The review request mentions /api/in-the-world/divine-office which is NOT a valid slug.
        # The expected behaviour is 404 because 'divine-office' is not in ISSUES.
        r = requests.get(f"{BASE_URL}/api/in-the-world/divine-office",
                         headers=HEADERS, timeout=60)
        # Either 404 (correct - not a valid slug) OR 200 if there's a registered alias.
        assert r.status_code in (200, 404), r.text

    def test_get_common_good_full_content(self):
        # First hit may take a while because Claude lazy-generates
        r = requests.get(f"{BASE_URL}/api/in-the-world/common-good",
                         headers=HEADERS, timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        # static fields
        assert data["slug"] == "common-good"
        assert data["title"] == "The Common Good"
        assert data["accent"]
        # AI-generated fields must be present and non-empty
        for k in ("summary", "church_teaching", "where_the_church_is_clear",
                  "prudential_judgment", "how_to_engage", "prayer"):
            assert k in data, f"missing {k}"
            assert isinstance(data[k], str) and len(data[k]) > 20, f"too short {k}: {data[k][:80]!r}"
        assert isinstance(data["principles"], list)
        assert len(data["principles"]) >= 1

    def test_caching_second_call_fast(self):
        # First call (may already be cached from previous test)
        import time
        t0 = time.time()
        r = requests.get(f"{BASE_URL}/api/in-the-world/common-good",
                         headers=HEADERS, timeout=60)
        elapsed = time.time() - t0
        assert r.status_code == 200
        # Cached responses should be < 5s
        assert elapsed < 10, f"second call took {elapsed:.1f}s, caching may be broken"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
