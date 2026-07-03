"""iter 91 — Add-to-practices, daily-acts, schedule complete (pilgrimage)."""
import os, uuid, requests, pytest

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_feat_aug25"
HDR = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update(HDR)
    return sess


# ------- Companion daily acts (Home vocation card feed) -------
class TestDailyActs:
    def test_daily_acts_returns_items(self, s):
        r = s.get(f"{BASE_URL}/api/companions/daily-acts")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and isinstance(data["items"], list)
        # At least the guardian angel should be present
        slugs = [it.get("slug") for it in data["items"]]
        assert "guardian-angel" in slugs
        for it in data["items"]:
            assert "act" in it and it["act"]
            assert "name" in it


# ------- Add-to-practices on companion pages -------
class TestAddPractice:
    saint_slug = "blessed-virgin-mary"
    saint_name = "The Blessed Virgin Mary"
    practice = f"TEST_iter91_{uuid.uuid4().hex[:6]}"
    devotion_id = None

    def test_add_practice_creates(self, s):
        r = s.post(f"{BASE_URL}/api/my/devotions/add-practice", json={
            "saint_name": self.saint_name,
            "saint_slug": self.saint_slug,
            "practice": self.practice,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("added") is True
        assert self.practice in data.get("practices", [])
        assert data.get("saint_slug") == self.saint_slug
        TestAddPractice.devotion_id = data["devotion_id"]

    def test_add_practice_idempotent(self, s):
        r = s.post(f"{BASE_URL}/api/my/devotions/add-practice", json={
            "saint_name": self.saint_name,
            "saint_slug": self.saint_slug,
            "practice": self.practice,
        })
        assert r.status_code == 200
        assert r.json().get("added") is False  # already exists

    def test_get_devotions_lists_added(self, s):
        r = s.get(f"{BASE_URL}/api/my/devotions")
        assert r.status_code == 200
        items = r.json().get("items", [])
        match = [x for x in items if x.get("saint_slug") == self.saint_slug]
        assert match, "devotion for slug not found"
        assert self.practice in match[0].get("practices", [])

    def test_cleanup_delete_devotion(self, s):
        if TestAddPractice.devotion_id:
            r = s.delete(f"{BASE_URL}/api/my/devotions/{TestAddPractice.devotion_id}")
            assert r.status_code in (200, 404)


# ------- Schedule create + complete toggle (pilgrimage) -------
class TestSchedulePilgrimageComplete:
    item_id = None

    def test_create_pilgrimage(self, s):
        r = s.post(f"{BASE_URL}/api/schedule", json={
            "kind": "pilgrimage",
            "title": f"TEST_iter91 pilgrimage {uuid.uuid4().hex[:5]}",
            "recurrence": "once",
            "date": "2026-06-15",
            "time": "09:00",
            "notify": True,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["kind"] == "pilgrimage"
        assert d["notify"] is True
        assert d["time"] == "09:00"
        assert d["completed"] is False
        TestSchedulePilgrimageComplete.item_id = d["id"]

    def test_mark_completed_true(self, s):
        r = s.post(f"{BASE_URL}/api/schedule/{self.item_id}/complete", json={"completed": True})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["completed"] is True
        assert d["completed_at"]

    def test_mark_completed_false(self, s):
        r = s.post(f"{BASE_URL}/api/schedule/{self.item_id}/complete", json={"completed": False})
        assert r.status_code == 200
        d = r.json()
        assert d["completed"] is False
        assert d["completed_at"] is None

    def test_cleanup(self, s):
        if TestSchedulePilgrimageComplete.item_id:
            r = s.delete(f"{BASE_URL}/api/schedule/{self.item_id}")
            assert r.status_code == 200


# ------- Companion detail page returns traditions -------
class TestCompanionTraditions:
    @pytest.mark.parametrize("slug", ["blessed-virgin-mary", "st-joseph", "francis-assisi"])
    def test_companion_has_traditions(self, s, slug):
        r = s.get(f"{BASE_URL}/api/companions/{slug}")
        assert r.status_code == 200, r.text
        d = r.json()
        # These 3 companions should have non-empty ct/dt/vt arrays
        assert d.get("church_traditions"), f"{slug} church_traditions empty"
        assert d.get("daily_traditions"), f"{slug} daily_traditions empty"
        assert d.get("vocation_traditions") is not None
