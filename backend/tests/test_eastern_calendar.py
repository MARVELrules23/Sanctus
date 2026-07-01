"""Backend tests for Eastern (Byzantine) liturgical calendar endpoints.

Verifies:
- /api/eastern/month?year&month&calendar (new vs old) — feast dates shift +13 days
- /api/eastern/day for great feasts (fixed) and Pascha (moveable, differs by cal)
- Invalid month → 400
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _find(days, month, day):
    target = f"-{month:02d}-{day:02d}"
    for d in days:
        if d["date"].endswith(target):
            return d
    return None


# ---- Month endpoint ----
class TestEasternMonth:
    def test_dec_2026_new_nativity(self, sess):
        r = sess.get(f"{API}/eastern/month", params={"year": 2026, "month": 12, "calendar": "new"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["calendar"] == "new"
        assert body["year"] == 2026 and body["month"] == 12
        dec25 = _find(body["days"], 12, 25)
        assert dec25 is not None
        assert dec25["feast"] == "Nativity of Christ"
        assert dec25["rank"] == "greatfeast"

    def test_dec_2026_old_no_nativity(self, sess):
        r = sess.get(f"{API}/eastern/month", params={"year": 2026, "month": 12, "calendar": "old"})
        assert r.status_code == 200
        body = r.json()
        assert body["calendar"] == "old"
        dec25 = _find(body["days"], 12, 25)
        assert dec25 is not None
        assert dec25["feast"] != "Nativity of Christ"
        assert dec25["season"] == "Nativity Fast (Philip's Fast)"

    def test_jan_2027_old_nativity_on_jan7(self, sess):
        r = sess.get(f"{API}/eastern/month", params={"year": 2027, "month": 1, "calendar": "old"})
        assert r.status_code == 200
        jan7 = _find(r.json()["days"], 1, 7)
        assert jan7 is not None
        assert jan7["feast"] == "Nativity of Christ"

    def test_theophany_new_jan6(self, sess):
        r = sess.get(f"{API}/eastern/month", params={"year": 2027, "month": 1, "calendar": "new"})
        assert r.status_code == 200
        jan6 = _find(r.json()["days"], 1, 6)
        assert jan6 and "Theophany" in (jan6["feast"] or "")

    def test_theophany_old_jan19(self, sess):
        r = sess.get(f"{API}/eastern/month", params={"year": 2027, "month": 1, "calendar": "old"})
        assert r.status_code == 200
        jan19 = _find(r.json()["days"], 1, 19)
        assert jan19 and "Theophany" in (jan19["feast"] or "")

    def test_invalid_month_400(self, sess):
        r = sess.get(f"{API}/eastern/month", params={"year": 2026, "month": 13, "calendar": "new"})
        assert r.status_code == 400


# ---- Day endpoint ----
class TestEasternDay:
    def test_pascha_new_2026(self, sess):
        r = sess.get(f"{API}/eastern/day", params={"date": "2026-04-05", "calendar": "new"})
        assert r.status_code == 200
        j = r.json()
        assert j["feast"] == "Pascha — Resurrection of the Lord"
        assert j["rank"] == "greatfeast"
        assert j["calendar"] == "new"

    def test_pascha_old_2026(self, sess):
        r = sess.get(f"{API}/eastern/day", params={"date": "2026-04-12", "calendar": "old"})
        assert r.status_code == 200
        j = r.json()
        assert j["feast"] == "Pascha — Resurrection of the Lord"
        assert j["calendar"] == "old"

    def test_transfiguration_new_aug6(self, sess):
        r = sess.get(f"{API}/eastern/day", params={"date": "2026-08-06", "calendar": "new"})
        assert r.status_code == 200
        assert "Transfiguration" in (r.json()["feast"] or "")

    def test_dormition_new_aug15(self, sess):
        r = sess.get(f"{API}/eastern/day", params={"date": "2026-08-15", "calendar": "new"})
        assert r.status_code == 200
        assert "Dormition" in (r.json()["feast"] or "")

    def test_annunciation_new_mar25(self, sess):
        r = sess.get(f"{API}/eastern/day", params={"date": "2026-03-25", "calendar": "new"})
        assert r.status_code == 200
        assert "Annunciation" in (r.json()["feast"] or "")

    def test_pentecost_new_2026(self, sess):
        # Pascha 2026 (new/Gregorian) = Apr 5 → Pentecost = May 24
        r = sess.get(f"{API}/eastern/day", params={"date": "2026-05-24", "calendar": "new"})
        assert r.status_code == 200
        assert r.json()["feast"] == "Pentecost"

    def test_ascension_new_2026(self, sess):
        # Pascha 2026 (new) = Apr 5 → Ascension = May 14
        r = sess.get(f"{API}/eastern/day", params={"date": "2026-05-14", "calendar": "new"})
        assert r.status_code == 200
        assert "Ascension" in (r.json()["feast"] or "")

    def test_invalid_date_400(self, sess):
        r = sess.get(f"{API}/eastern/day", params={"date": "not-a-date", "calendar": "new"})
        assert r.status_code == 400

    def test_pascha_differs_new_vs_old(self, sess):
        r1 = sess.get(f"{API}/eastern/day", params={"date": "2026-04-05", "calendar": "old"})
        # In 'old' reckoning, Apr 5 2026 is not Orthodox Pascha (which falls Apr 12)
        assert r1.status_code == 200
        assert r1.json().get("feast") != "Pascha — Resurrection of the Lord"


# ---- Roman calendar sanity — must be unchanged ----
class TestRomanUnchanged:
    def test_roman_month_still_works(self, sess):
        r = sess.get(f"{API}/liturgical/month", params={"year": 2026, "month": 12})
        assert r.status_code == 200
        assert "days" in r.json()
