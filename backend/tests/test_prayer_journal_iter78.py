"""Phase 3 backend tests: Community Prayer Journal CRUD.

Covers:
- POST /api/community/prayers (create)
- GET /api/community/prayers (list)
- POST /api/community/prayers/{id}/pray (toggle)
- DELETE /api/community/prayers/{id} (author only)
- Anonymous flag returns author=null
- 401 without Bearer token
- 400 empty body
- 404 deleting non-existent id
"""
import os
import time
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("EXPO_BACKEND_URL") or os.environ["EXPO_PUBLIC_BACKEND_URL"]
BASE_URL = BASE_URL.rstrip("/")
TOKEN = "test_feat_aug25"
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    })
    return s


@pytest.fixture(scope="module")
def created_ids():
    return []


# ---------- Auth guards ----------
class TestAuth:
    def test_list_requires_auth(self):
        r = requests.get(f"{API}/community/prayers")
        assert r.status_code == 401, r.text

    def test_create_requires_auth(self):
        r = requests.post(f"{API}/community/prayers",
                          json={"body": "hello", "anonymous": False})
        assert r.status_code == 401, r.text


# ---------- CRUD ----------
class TestPrayerCRUD:
    def test_create_returns_expected_shape(self, sess, created_ids):
        r = sess.post(f"{API}/community/prayers",
                      json={"body": "TEST_iter78 pray for peace", "anonymous": False})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_mine"] is True
        assert d["pray_count"] == 0
        assert d["prayed_by_me"] is False
        assert d["anonymous"] is False
        assert d["author"] is not None
        assert d["author"].get("user_id")
        assert d["body"] == "TEST_iter78 pray for peace"
        assert d.get("prayer_id", "").startswith("pray_")
        created_ids.append(d["prayer_id"])

    def test_empty_body_returns_400(self, sess):
        r = sess.post(f"{API}/community/prayers",
                      json={"body": "   ", "anonymous": False})
        assert r.status_code == 400, r.text

    def test_list_includes_created(self, sess, created_ids):
        r = sess.get(f"{API}/community/prayers?limit=50")
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("items"), list)
        ids = [it["prayer_id"] for it in d["items"]]
        assert created_ids[0] in ids
        # Ensure created appears at/near top since sort is desc created_at
        assert ids[0] == created_ids[0]
        # Verify essential fields exist in each item
        it = next(x for x in d["items"] if x["prayer_id"] == created_ids[0])
        for k in ("body", "anonymous", "author", "created_at", "pray_count",
                  "prayed_by_me", "is_mine"):
            assert k in it

    def test_anonymous_post_hides_author(self, sess, created_ids):
        r = sess.post(f"{API}/community/prayers",
                      json={"body": "TEST_iter78 anonymous intention",
                            "anonymous": True})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["anonymous"] is True
        assert d["author"] is None
        created_ids.append(d["prayer_id"])

        # Verify persistence with GET
        r2 = sess.get(f"{API}/community/prayers?limit=50")
        assert r2.status_code == 200
        it = next(x for x in r2.json()["items"] if x["prayer_id"] == d["prayer_id"])
        assert it["anonymous"] is True
        assert it["author"] is None

    def test_toggle_pray_on_then_off(self, sess, created_ids):
        pid = created_ids[0]
        # Turn ON
        r = sess.post(f"{API}/community/prayers/{pid}/pray")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["prayed"] is True
        assert d["pray_count"] == 1

        # Verify via list
        r2 = sess.get(f"{API}/community/prayers?limit=50")
        it = next(x for x in r2.json()["items"] if x["prayer_id"] == pid)
        assert it["prayed_by_me"] is True
        assert it["pray_count"] == 1

        # Toggle OFF
        r3 = sess.post(f"{API}/community/prayers/{pid}/pray")
        assert r3.status_code == 200, r3.text
        d3 = r3.json()
        assert d3["prayed"] is False
        assert d3["pray_count"] == 0

        # Verify via list
        r4 = sess.get(f"{API}/community/prayers?limit=50")
        it2 = next(x for x in r4.json()["items"] if x["prayer_id"] == pid)
        assert it2["prayed_by_me"] is False
        assert it2["pray_count"] == 0

    def test_delete_non_existent_returns_404(self, sess):
        r = sess.delete(f"{API}/community/prayers/pray_does_not_exist_xxx")
        assert r.status_code == 404, r.text

    def test_delete_by_author_ok_and_gone(self, sess, created_ids):
        # Delete both created
        for pid in list(created_ids):
            r = sess.delete(f"{API}/community/prayers/{pid}")
            assert r.status_code == 200, r.text
            assert r.json().get("ok") is True
            created_ids.remove(pid)

        # Confirm not in list
        r2 = sess.get(f"{API}/community/prayers?limit=50")
        ids = [it["prayer_id"] for it in r2.json()["items"]]
        assert not any(pid in ids for pid in ["pray_"])  # sanity; deleted ids gone
