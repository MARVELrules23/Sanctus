"""Iteration 34 — Sanctus Library Radio: post-fix regression for stream_url seed.

Verifies:
  1. GET /api/library/radio returns exactly 8 stations with the NEW slugs.
  2. Old (dead) slugs are absent from the response.
  3. Each station has a non-empty `stream_url` that starts with https://.
  4. GET /api/library/radio/{slug} returns 200 for every new slug, and the
     stream_url field is the expected one.
  5. (sanity) The stream_url hosts match what the fix claims (no regression
     back to the dead playerservices/dreamsiteradiocp4/oldvatican mounts).
"""
import os
import pytest
import requests
from urllib.parse import urlparse

BASE_URL = os.environ["EXPO_BACKEND_URL"].rstrip("/") if os.environ.get(
    "EXPO_BACKEND_URL") else "https://faithful-fitness-3.preview.emergentagent.com"

ADMIN_TOKEN = "TEST_iter32_admin_tok"

# ---------- Expected new state (from the fix) ----------
EXPECTED = {
    "ewtn-radio":            "https://ewtn-ice.streamguys1.com/english-aac",
    "relevant-radio":        "https://playerservices.streamtheworld.com/api/livestream-redirect/RR_MAIN.mp3",
    "iowa-catholic-radio":   "https://streaming.live365.com/a39922?n=15e4d1f6f58efdde0d65",
    "real-presence-radio":   "https://ssl-1.stream.miriamtech.net/realpresence/kwtl",
    "guadalupe-radio":       "https://ssl-2.stream.miriamtech.net/grn/secal.mp3",
    "irosary-radio":         "https://stream.radio.co/sbc212800b/low",
    "vatican-news-english":  "https://radio.vaticannews.va/stream-en",
    "ewtn-espanol":          "https://ewtn-ice.streamguys1.com/spanish-aac",
}

OLD_SLUGS_THAT_MUST_BE_GONE = {
    "ave-maria-radio",
    "sacred-heart-radio",
    "veritas-radio-uk",
    "vatican-radio-english",
    "radio-maria-usa",
}


@pytest.fixture(scope="module")
def auth_client():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {ADMIN_TOKEN}",
                      "Content-Type": "application/json"})
    return s


# ---------------- list endpoint ----------------
class TestRadioListSeed:
    def test_list_returns_8_stations(self, auth_client):
        r = auth_client.get(f"{BASE_URL}/api/library/radio")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("total") == 8, f"expected 8, got {body.get('total')}"
        assert isinstance(body.get("items"), list)
        assert len(body["items"]) == 8

    def test_list_contains_all_new_slugs_only(self, auth_client):
        r = auth_client.get(f"{BASE_URL}/api/library/radio")
        assert r.status_code == 200
        slugs = {it["slug"] for it in r.json()["items"]}
        assert slugs == set(EXPECTED.keys()), (
            f"slug set mismatch.\nexpected={sorted(EXPECTED.keys())}\n"
            f"got     ={sorted(slugs)}")

    def test_no_old_dead_slugs_present(self, auth_client):
        r = auth_client.get(f"{BASE_URL}/api/library/radio")
        slugs = {it["slug"] for it in r.json()["items"]}
        leaked = slugs & OLD_SLUGS_THAT_MUST_BE_GONE
        assert not leaked, f"dead/old slugs still present: {leaked}"

    def test_all_stream_urls_are_https(self, auth_client):
        r = auth_client.get(f"{BASE_URL}/api/library/radio")
        for it in r.json()["items"]:
            assert it.get("stream_url"), f"empty stream_url for {it['slug']}"
            assert it["stream_url"].startswith("https://"), (
                f"non-https stream_url for {it['slug']}: {it['stream_url']}")

    def test_stream_urls_exactly_match_fix(self, auth_client):
        r = auth_client.get(f"{BASE_URL}/api/library/radio")
        actual = {it["slug"]: it["stream_url"] for it in r.json()["items"]}
        for slug, expected_url in EXPECTED.items():
            assert actual.get(slug) == expected_url, (
                f"stream_url mismatch for {slug}.\n"
                f"  expected: {expected_url}\n"
                f"  got:      {actual.get(slug)}")


# ---------------- per-slug detail endpoint ----------------
@pytest.mark.parametrize("slug,expected_url", sorted(EXPECTED.items()))
def test_detail_endpoint_for_each_new_slug(auth_client, slug, expected_url):
    r = auth_client.get(f"{BASE_URL}/api/library/radio/{slug}")
    assert r.status_code == 200, (
        f"detail for slug={slug} returned {r.status_code}: {r.text}")
    body = r.json()
    assert body["slug"] == slug
    assert body.get("stream_url"), f"empty stream_url for {slug}"
    assert body["stream_url"].startswith("https://"), (
        f"non-https for {slug}: {body['stream_url']}")
    assert body["stream_url"] == expected_url, (
        f"stream_url drift for {slug}: got {body['stream_url']}")


# ---------------- defensive: old dead hosts must not appear anywhere ----------------
DEAD_HOST_FRAGMENTS = [
    # known-dead from the original 7 broken seeds
    "dreamsiteradiocp4.com",
]


def test_no_known_dead_hosts_in_stream_urls(auth_client):
    r = auth_client.get(f"{BASE_URL}/api/library/radio")
    items = r.json()["items"]
    leaks = []
    for it in items:
        host = urlparse(it["stream_url"]).netloc.lower()
        for dead in DEAD_HOST_FRAGMENTS:
            if dead in host:
                leaks.append((it["slug"], it["stream_url"]))
    assert not leaks, f"stream_urls still pointing at dead hosts: {leaks}"


# ---------------- 404 sanity for old slugs ----------------
@pytest.mark.parametrize("dead_slug", sorted(OLD_SLUGS_THAT_MUST_BE_GONE))
def test_old_slug_detail_returns_404(auth_client, dead_slug):
    r = auth_client.get(f"{BASE_URL}/api/library/radio/{dead_slug}")
    assert r.status_code == 404, (
        f"old slug {dead_slug} should be gone but returned {r.status_code}")
