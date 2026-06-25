"""Iter 51 — Verify the 4 changes:
1) Calendar challenges windows (St. Joseph 33-day window 2026/2027).
2) Community post photo (existing post_79c1582cf83e40).
3) Public user profile shows denomination/tradition_path/age.
4) (no backend for prayer text)
"""
import os
import requests
import pytest

BASE = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
TOKEN = "test_feat_aug25"
ADMIN_ID = "user_ade7a898e281"
HDR = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


# ---------- Calendar challenge windows (St. Joseph + DST) ----------
class TestChallengeWindows:
    def test_windows_2026_st_joseph_33_days(self):
        r = requests.get(f"{API}/challenges/windows?year=2026", headers=HDR, timeout=15)
        assert r.status_code == 200, r.text
        wins = {w["slug"]: w for w in r.json().get("items", [])}
        sj = wins.get("st-joseph-consecration")
        assert sj is not None, f"missing st-joseph-consecration; got {list(wins)}"
        # Expect Feb 15 → Mar 19
        assert sj["start_date"][:10] == "2026-02-15"
        assert sj["end_date"][:10] == "2026-03-19"
        assert sj["total_days"] == 33

    def test_windows_2027_st_joseph_33_days(self):
        r = requests.get(f"{API}/challenges/windows?year=2027", headers=HDR, timeout=15)
        assert r.status_code == 200, r.text
        wins = {w["slug"]: w for w in r.json().get("items", [])}
        sj = wins.get("st-joseph-consecration")
        assert sj is not None
        assert sj["start_date"][:10] == "2027-02-15"
        assert sj["end_date"][:10] == "2027-03-19"
        assert sj["total_days"] == 33


# ---------- Community photo post ----------
class TestCommunityPhoto:
    def test_existing_photo_post_visible(self):
        # /api/community/feed returns items[]
        r = requests.get(f"{API}/community/feed", headers=HDR, timeout=15)
        assert r.status_code == 200, r.text
        items = r.json().get("items", [])
        found = next((p for p in items if p.get("post_id") == "post_79c1582cf83e40"), None)
        assert found is not None, "post_79c1582cf83e40 not on feed"
        # backend returns full image data URL on the 'image' field
        assert found.get("image"), f"post missing image field: keys={list(found.keys())}"
        assert (found.get("image") or "").startswith("data:image/"), "image is not a data URI"
        assert "Photo from our parish pilgrimage" in (found.get("body") or "")

    def test_create_post_with_image_round_trip(self):
        png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgAAIAAAUAAeImBZsAAAAASUVORK5CYII="
        body = {"body": "TEST_iter51 photo post.", "image": png}
        r = requests.post(f"{API}/community/posts", json=body, headers=HDR, timeout=15)
        assert r.status_code in (200, 201), r.text
        post = r.json()
        assert post.get("image"), f"image missing in create response: {list(post.keys())}"
        pid = post.get("post_id") or post.get("id")
        assert pid
        # Cleanup
        requests.delete(f"{API}/community/posts/{pid}", headers=HDR, timeout=15)


# ---------- Public bio on community profile ----------
class TestCommunityProfileBio:
    def test_admin_profile_returns_bio_fields(self):
        r = requests.get(f"{API}/community/users/{ADMIN_ID}", headers=HDR, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        u = data.get("user") or data
        assert u.get("denomination") == "catholic", f"denomination={u.get('denomination')}"
        assert u.get("tradition_path") == "convert", f"tradition_path={u.get('tradition_path')}"
        # Age is editable by the user via PUT /api/auth/me; just assert it's exposed as an int.
        assert isinstance(u.get("age"), int), f"age={u.get('age')!r} (expected int)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
