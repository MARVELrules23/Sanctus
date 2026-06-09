"""Backend tests for the 'Catechism in 90 seconds' feature.

Covers:
- GET /api/catechism/today (idempotency, different dates → different teachings,
  liturgical season affinity for Advent / Lent / Easter)
- GET /api/catechism/teaching/{id} (success + 404)
- POST /api/catechism/reflect (Claude Sonnet 4.5 via Emergent LLM key)
- POST /api/catechism/save-to-journal (writes to db.journal, marks assignment)
- GET /api/journal?kind=catechism (filter correctness)
- GET /api/catechism/history
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Load EXPO_PUBLIC_BACKEND_URL from frontend/.env if present
load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or "http://localhost:8001"
).rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

# Dedicated test identity to avoid stepping on the shared TEST_USER_ID fixture
TEST_USER_ID = "test_catechism_user"
TEST_EMAIL = "TEST_catechism@sanctus.app"
TEST_TOKEN = "TEST_catechism_token_xyz"

# Theme sets per season — straight from /app/backend/catechism.py THEME_SEASONS
THEMES_ADVENT = {
    "Hope", "Last Things", "Mary", "Prayer", "Scripture",
}
THEMES_LENT = {
    "Sin", "Confession", "Suffering", "Humility", "Virtue",
    "Forgiveness", "Prayer", "Mercy", "Scripture",
}
THEMES_EASTER = {
    "Hope", "Mary", "Christ", "Forgiveness", "Eucharist", "Grace",
    "Prayer", "Love", "Mercy", "Scripture",
}


@pytest.fixture(scope="module")
def mongo_db():
    cli = MongoClient(MONGO_URL)
    db = cli[DB_NAME]
    # Clean any prior test data
    db.catechism_assignments.delete_many({"user_id": TEST_USER_ID})
    db.journal.delete_many({"user_id": TEST_USER_ID})
    yield db
    # Teardown
    db.catechism_assignments.delete_many({"user_id": TEST_USER_ID})
    db.journal.delete_many({"user_id": TEST_USER_ID})
    db.user_sessions.delete_many({"user_id": TEST_USER_ID})
    db.users.delete_many({"user_id": TEST_USER_ID})
    cli.close()


@pytest.fixture(scope="module")
def seeded_user(mongo_db):
    mongo_db.users.update_one(
        {"user_id": TEST_USER_ID},
        {"$set": {
            "user_id": TEST_USER_ID,
            "email": TEST_EMAIL,
            "name": "TEST Catechism User",
            "picture": None,
            "created_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    mongo_db.user_sessions.update_one(
        {"session_token": TEST_TOKEN},
        {"$set": {
            "session_token": TEST_TOKEN,
            "user_id": TEST_USER_ID,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
        }},
        upsert=True,
    )
    return {"user_id": TEST_USER_ID, "token": TEST_TOKEN}


@pytest.fixture(scope="module")
def auth(seeded_user):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {seeded_user['token']}",
    })
    return s


@pytest.fixture(scope="module")
def anon():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- /today ----------

class TestCatechismToday:
    def test_today_requires_auth(self, anon):
        r = anon.get(f"{BASE_URL}/api/catechism/today", params={"date": "2026-01-15"})
        assert r.status_code in (401, 403), r.text

    def test_today_returns_shape(self, auth):
        r = auth.get(f"{BASE_URL}/api/catechism/today", params={"date": "2026-01-15"})
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("id", "ccc_ref", "theme", "title", "quote", "expansion",
                  "reflection_prompt", "date", "saved_to_journal", "reflection"):
            assert k in d, f"missing key {k} in {d}"
        assert d["date"] == "2026-01-15"
        assert d["saved_to_journal"] is False
        assert isinstance(d["id"], str) and d["id"]
        assert isinstance(d["quote"], str) and len(d["quote"]) > 10

    def test_today_is_idempotent(self, auth):
        r1 = auth.get(f"{BASE_URL}/api/catechism/today", params={"date": "2026-03-12"})
        r2 = auth.get(f"{BASE_URL}/api/catechism/today", params={"date": "2026-03-12"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"]

    def test_distinct_dates_yield_distinct_teachings(self, auth, mongo_db):
        # Clean assignments for this user so we sample fresh
        mongo_db.catechism_assignments.delete_many({"user_id": TEST_USER_ID})
        ids = set()
        # 10 dates spread across the year
        dates = ["2026-05-01", "2026-05-08", "2026-06-15", "2026-07-04",
                 "2026-07-22", "2026-08-15", "2026-09-10", "2026-10-04",
                 "2026-11-01", "2026-11-21"]
        for ds in dates:
            r = auth.get(f"{BASE_URL}/api/catechism/today", params={"date": ds})
            assert r.status_code == 200, r.text
            ids.add(r.json()["id"])
        assert len(ids) >= 2, f"expected at least 2 distinct teachings across 10 dates, got {ids}"

    def test_advent_returns_advent_themed_teaching(self, auth, mongo_db):
        mongo_db.catechism_assignments.delete_many({"user_id": TEST_USER_ID, "date": "2026-12-01"})
        r = auth.get(f"{BASE_URL}/api/catechism/today", params={"date": "2026-12-01"})
        assert r.status_code == 200, r.text
        theme = r.json()["theme"]
        assert theme in THEMES_ADVENT, f"Advent date returned theme '{theme}' not in {THEMES_ADVENT}"

    def test_lent_returns_lent_themed_teaching(self, auth, mongo_db):
        mongo_db.catechism_assignments.delete_many({"user_id": TEST_USER_ID, "date": "2026-02-25"})
        r = auth.get(f"{BASE_URL}/api/catechism/today", params={"date": "2026-02-25"})
        assert r.status_code == 200, r.text
        theme = r.json()["theme"]
        assert theme in THEMES_LENT, f"Lent date returned theme '{theme}' not in {THEMES_LENT}"

    def test_easter_returns_easter_themed_teaching(self, auth, mongo_db):
        mongo_db.catechism_assignments.delete_many({"user_id": TEST_USER_ID, "date": "2026-04-10"})
        r = auth.get(f"{BASE_URL}/api/catechism/today", params={"date": "2026-04-10"})
        assert r.status_code == 200, r.text
        theme = r.json()["theme"]
        assert theme in THEMES_EASTER, f"Easter date returned theme '{theme}' not in {THEMES_EASTER}"


# ---------- /teaching/{id} ----------

class TestCatechismTeachingById:
    def test_get_known_teaching(self, auth):
        r = auth.get(f"{BASE_URL}/api/catechism/teaching/ccc_2559")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["id"] == "ccc_2559"
        assert d["ccc_ref"] == "CCC 2559"

    def test_get_unknown_teaching_404(self, auth):
        r = auth.get(f"{BASE_URL}/api/catechism/teaching/ccc_does_not_exist")
        assert r.status_code == 404


# ---------- /reflect ----------

class TestCatechismReflect:
    def test_reflect_returns_nonempty_text(self, auth):
        body = {
            "teaching_id": "ccc_2559",
            "note": "I keep getting distracted at the start of prayer."
        }
        r = auth.post(f"{BASE_URL}/api/catechism/reflect", json=body, timeout=60)
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        data = r.json()
        assert data.get("teaching_id") == "ccc_2559"
        assert isinstance(data.get("reflection"), str)
        # 80-120 word target; allow some slack
        wc = len(data["reflection"].split())
        assert wc >= 30, f"reflection too short ({wc} words): {data['reflection']!r}"

    def test_reflect_unknown_teaching_404(self, auth):
        r = auth.post(
            f"{BASE_URL}/api/catechism/reflect",
            json={"teaching_id": "ccc_unknown_xyz"},
            timeout=30,
        )
        assert r.status_code == 404


# ---------- /save-to-journal ----------

class TestCatechismSaveToJournal:
    DATE = "2026-01-20"
    TEACHING_ID = "ccc_2710"

    def test_save_writes_to_journal_collection(self, auth, mongo_db):
        # Ensure /today first creates assignment
        r0 = auth.get(f"{BASE_URL}/api/catechism/today", params={"date": self.DATE})
        assert r0.status_code == 200

        # Save explicit teaching
        payload = {
            "date": self.DATE,
            "teaching_id": self.TEACHING_ID,
            "reflection": "TEST reflection body — keeping silence before God today.",
            "user_note": "TEST user note",
        }
        r = auth.post(f"{BASE_URL}/api/catechism/save-to-journal", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        eid = data.get("entry_id")
        assert isinstance(eid, str) and eid.startswith("jrn_")

        # Verify db.journal has the entry
        doc = mongo_db.journal.find_one({"entry_id": eid, "user_id": TEST_USER_ID})
        assert doc is not None, "entry not present in db.journal"
        assert doc.get("kind") == "catechism"
        assert (doc.get("title") or "").startswith("CCC Reflection —")
        struct = doc.get("structured") or {}
        for k in ("teaching_id", "ccc_ref", "theme", "quote", "reflection"):
            assert k in struct, f"structured missing {k}: {struct}"
        assert struct["teaching_id"] == self.TEACHING_ID

        # Verify db.journal_entries was NOT used
        legacy = mongo_db.journal_entries.find_one({"entry_id": eid}) if "journal_entries" in mongo_db.list_collection_names() else None
        assert legacy is None, "entry incorrectly written to legacy db.journal_entries"

    def test_assignment_marked_saved(self, auth):
        r = auth.get(f"{BASE_URL}/api/catechism/today", params={"date": self.DATE})
        assert r.status_code == 200, r.text
        assert r.json().get("saved_to_journal") is True

    def test_save_unknown_teaching_404(self, auth):
        r = auth.post(
            f"{BASE_URL}/api/catechism/save-to-journal",
            json={"date": "2026-01-22", "teaching_id": "ccc_bogus"},
            timeout=15,
        )
        assert r.status_code == 404


# ---------- /api/journal?kind filter ----------

class TestJournalFilter:
    def test_catechism_filter_includes_saved(self, auth):
        r = auth.get(f"{BASE_URL}/api/journal", params={"kind": "catechism"})
        assert r.status_code == 200, r.text
        items = r.json().get("items", [])
        assert len(items) >= 1
        assert all(it.get("kind") == "catechism" for it in items), \
            "kind=catechism returned non-catechism entries"
        titles = [it.get("title", "") for it in items]
        assert any(t.startswith("CCC Reflection —") for t in titles), \
            f"no CCC Reflection title in {titles}"

    def test_free_filter_excludes_catechism(self, auth):
        r = auth.get(f"{BASE_URL}/api/journal", params={"kind": "free"})
        assert r.status_code == 200, r.text
        items = r.json().get("items", [])
        for it in items:
            assert it.get("kind") != "catechism", \
                f"free filter leaked a catechism entry: {it.get('entry_id')}"


# ---------- /history ----------

class TestCatechismHistory:
    def test_history_lists_assignments(self, auth):
        r = auth.get(f"{BASE_URL}/api/catechism/history", params={"limit": 50})
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data.get("items"), list)
        assert data.get("total_pool") and data["total_pool"] >= 20
        # We've called /today many times above — expect ≥1 row
        assert len(data["items"]) >= 1
