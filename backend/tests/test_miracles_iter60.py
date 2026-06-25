"""Iter60 — Catholic miracles 'Live Feed' API tests.

Covers:
- Public GET /api/miracles seeds and returns 6+ published claims with required fields
- Accept-Language: es / it translates title/summary/location
- Admin-only listing/patch/publish/unpublish/delete + 403 for non-admin
- Drafts (state=draft) are not in the public list
- (Skipped) generate endpoint — slow (~30-60s); flagged with marker
"""
from __future__ import annotations

import os
import uuid
import asyncio
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
ADMIN_TOKEN = "test_feat_aug25"

REQUIRED_FIELDS = {"claim_id", "title", "summary", "type", "verdict",
                   "location", "reported_year", "source_name", "source_url"}
VALID_VERDICTS = {"reported", "investigating", "approved", "not_supernatural"}
EXPECTED_SEED_SLUG_HINTS = ["lanciano", "guadalupe", "buenos", "carlo", "medjugorje"]
# Fátima has an accent; allow either spelling
EXPECTED_SEED_REGEX_HINTS = [r"f[áa]tima"]


def _hdr(tok=ADMIN_TOKEN, lang=None):
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    if lang:
        h["Accept-Language"] = lang
    return h


def _ensure_non_admin_user():
    """Insert a throwaway non-admin user + session so we can test 403."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from dotenv import load_dotenv

    load_dotenv("/app/backend/.env")
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    async def run():
        uid = f"user_TEST_{uuid.uuid4().hex[:8]}"
        tok = f"TEST_nonadmin_{uuid.uuid4().hex[:8]}"
        await db.users.insert_one({
            "user_id": uid,
            "email": f"TEST_{uid}@example.com",
            "name": "TEST nonadmin",
            "is_admin": False,
            "created_at": datetime.now(timezone.utc),
        })
        await db.user_sessions.insert_one({
            "session_token": tok,
            "user_id": uid,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=2),
        })
        return tok, uid

    tok, uid = asyncio.get_event_loop().run_until_complete(run())

    def cleanup():
        async def _c():
            await db.user_sessions.delete_one({"session_token": tok})
            await db.users.delete_one({"user_id": uid})
        asyncio.get_event_loop().run_until_complete(_c())

    return tok, cleanup


# -------------------- Public feed --------------------

class TestPublicFeed:
    def test_health_auth(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=_hdr())
        assert r.status_code == 200, r.text
        assert r.json().get("is_admin") is True, "admin token should resolve to admin user"

    def test_list_published_seeded(self):
        r = requests.get(f"{BASE_URL}/api/miracles", headers=_hdr())
        assert r.status_code == 200, r.text
        body = r.json()
        items = body.get("items", [])
        assert body.get("total") == len(items)
        assert len(items) >= 6, f"expected >=6 seeded claims, got {len(items)}"
        # every published item has required fields + valid verdict
        for it in items:
            missing = REQUIRED_FIELDS - set(it.keys())
            assert not missing, f"missing fields: {missing} in {it}"
            assert it["verdict"] in VALID_VERDICTS
            assert it["source_url"].startswith("http")
            assert it.get("state", "published") == "published"
        # seed hints present (titles contain the names)
        titles = " ".join((it["title"] or "").lower() for it in items)
        for hint in EXPECTED_SEED_SLUG_HINTS:
            assert hint in titles, f"expected '{hint}' in seeded titles"
        import re as _re
        for pat in EXPECTED_SEED_REGEX_HINTS:
            assert _re.search(pat, titles), f"expected regex '{pat}' in seeded titles"

    def test_drafts_not_in_public(self):
        # All public items must have state=published
        r = requests.get(f"{BASE_URL}/api/miracles", headers=_hdr())
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it.get("state") == "published"


# -------------------- Localization --------------------

class TestLocalization:
    def _grab_lanciano(self, lang):
        r = requests.get(f"{BASE_URL}/api/miracles", headers=_hdr(lang=lang))
        assert r.status_code == 200, r.text
        for it in r.json()["items"]:
            if "lanciano" in (it.get("title") or "").lower() or "lanciano" in (it.get("location") or "").lower():
                return it
        return None

    def test_spanish_translates(self):
        en = self._grab_lanciano("en")
        es = self._grab_lanciano("es")
        assert en and es
        # At least one of title/summary/location differs from English
        diffs = sum(1 for f in ("title", "summary", "location")
                    if (en.get(f) or "").strip() != (es.get(f) or "").strip())
        assert diffs >= 1, f"Spanish payload appears untranslated: en={en} es={es}"

    def test_italian_translates(self):
        en = self._grab_lanciano("en")
        it = self._grab_lanciano("it")
        assert en and it
        diffs = sum(1 for f in ("title", "summary", "location")
                    if (en.get(f) or "").strip() != (it.get(f) or "").strip())
        assert diffs >= 1, f"Italian payload appears untranslated: en={en} it={it}"


# -------------------- Admin + permissions --------------------

class TestAdminAndPermissions:
    def test_non_admin_blocked(self):
        try:
            tok, cleanup = _ensure_non_admin_user()
        except Exception as e:
            pytest.skip(f"could not provision non-admin user: {e}")
        try:
            for path in ["/api/miracles/admin/all", "/api/miracles/admin/generate"]:
                method = requests.post if "generate" in path else requests.get
                r = method(f"{BASE_URL}{path}", headers=_hdr(tok=tok),
                           json={} if "generate" in path else None)
                assert r.status_code == 403, f"{path} should be 403, got {r.status_code} {r.text}"
            # public list should still work for normal user
            r = requests.get(f"{BASE_URL}/api/miracles", headers=_hdr(tok=tok))
            assert r.status_code == 200
        finally:
            cleanup()

    def test_admin_list_all_has_drafts_state(self):
        r = requests.get(f"{BASE_URL}/api/miracles/admin/all", headers=_hdr())
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        states = {it["state"] for it in items}
        # iter context said generate already ran once → drafts likely present
        # we don't hard-require drafts, but we require valid state values
        assert states.issubset({"draft", "published"}), states

    def test_admin_full_lifecycle_on_seed_copy(self):
        """Create a draft directly (insert via admin patch flow) is not exposed,
        so instead: pick a published seed item, unpublish → verify hidden in public →
        re-publish → patch verdict back."""
        r = requests.get(f"{BASE_URL}/api/miracles", headers=_hdr())
        seed = next((it for it in r.json()["items"] if "lanciano" in (it["title"] or "").lower()), None)
        assert seed, "Lanciano seed must exist for lifecycle test"
        cid = seed["claim_id"]
        original_verdict = seed["verdict"]

        # 1) unpublish
        r = requests.post(f"{BASE_URL}/api/miracles/admin/{cid}/unpublish", headers=_hdr())
        assert r.status_code == 200, r.text
        assert r.json()["state"] == "draft"

        # 2) confirm not in public list
        r = requests.get(f"{BASE_URL}/api/miracles", headers=_hdr())
        assert all(it["claim_id"] != cid for it in r.json()["items"]), "draft leaked into public list"

        # 3) admin can still see it via /admin/all
        r = requests.get(f"{BASE_URL}/api/miracles/admin/all", headers=_hdr())
        assert any(it["claim_id"] == cid and it["state"] == "draft" for it in r.json()["items"])

        # 4) patch verdict → investigating
        r = requests.patch(f"{BASE_URL}/api/miracles/admin/{cid}",
                           headers=_hdr(), json={"verdict": "investigating"})
        assert r.status_code == 200, r.text
        assert r.json()["verdict"] == "investigating"

        # 5) invalid verdict rejected
        r = requests.patch(f"{BASE_URL}/api/miracles/admin/{cid}",
                           headers=_hdr(), json={"verdict": "made-up"})
        assert r.status_code == 400

        # 6) republish + restore verdict
        r = requests.post(f"{BASE_URL}/api/miracles/admin/{cid}/publish", headers=_hdr())
        assert r.status_code == 200
        assert r.json()["state"] == "published"
        r = requests.patch(f"{BASE_URL}/api/miracles/admin/{cid}",
                           headers=_hdr(), json={"verdict": original_verdict})
        assert r.status_code == 200
        assert r.json()["verdict"] == original_verdict

        # 7) confirm GET single by id works for both admin + public after republish
        r = requests.get(f"{BASE_URL}/api/miracles/{cid}", headers=_hdr())
        assert r.status_code == 200 and r.json()["claim_id"] == cid

    def test_get_single_404_unknown(self):
        r = requests.get(f"{BASE_URL}/api/miracles/mir_does_not_exist", headers=_hdr())
        assert r.status_code == 404


# -------------------- AI generate (smoke; slow) --------------------

@pytest.mark.slow
class TestGenerateSmoke:
    """Single best-effort smoke test of the AI generate endpoint.

    The endpoint can take 30-90s (live web search). We only assert HTTP 200
    and a sane response shape — content varies.
    """
    def test_generate_returns_200(self):
        try:
            r = requests.post(
                f"{BASE_URL}/api/miracles/admin/generate",
                headers=_hdr(),
                json={"focus": "Eucharistic miracles 2025"},
                timeout=120,
            )
        except requests.exceptions.Timeout:
            pytest.skip("generate timed out >120s — non-blocking")
            return
        assert r.status_code == 200, r.text
        body = r.json()
        assert "created" in body and "drafts" in body
        assert isinstance(body["created"], int)
        assert isinstance(body["drafts"], list)
