"""Seed a curated set of well-known real Catholic charities into the Sanctus
charity directory.

Idempotent: skips entries whose `slug` already exists (or duplicates by
case-insensitive name+city). Marks each as approved + auto-attributed to the
seeded admin user.

Run from /app/backend:
    python3 scripts/seed_charities.py
"""
from __future__ import annotations

import os
import sys
import uuid
import secrets
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
ADMIN_USER_ID = "user_ade7a898e281"
ADMIN_EMAIL = "philipwils13@gmail.com"

# ---------------------------------------------------------------------------
# Curated real-world Catholic charities (drawn from public mission statements).
# Categories must match charity.py ALLOWED_CATEGORIES.
# ---------------------------------------------------------------------------
CHARITIES: list[dict] = [
    {
        "name": "Catholic Charities USA",
        "mission": (
            "The national office of the Catholic Charities ministry — supporting "
            "165+ local agencies across the country that serve the poor, "
            "vulnerable, and marginalized through food assistance, refugee "
            "resettlement, housing, disaster relief, and family support."
        ),
        "category": "general",
        "city": "Alexandria",
        "state": "VA",
        "country": "US",
        "website": "https://www.catholiccharitiesusa.org",
        "email": "info@catholiccharitiesusa.org",
        "phone": "+1-703-549-1390",
    },
    {
        "name": "Catholic Relief Services",
        "mission": (
            "The official international humanitarian agency of the U.S. Catholic "
            "Church. CRS works in over 100 countries, serving the poor through "
            "disaster response, food security, agriculture, education, peace-"
            "building, and health programs — regardless of race, religion, or "
            "nationality."
        ),
        "category": "general",
        "city": "Baltimore",
        "state": "MD",
        "country": "US",
        "website": "https://www.crs.org",
        "email": "info@crs.org",
        "phone": "+1-877-435-7277",
    },
    {
        "name": "St. Vincent de Paul Society — National Council USA",
        "mission": (
            "A lay Catholic organization founded in 1845, leading 90,000+ "
            "members in person-to-person service of the poor through home "
            "visits, food pantries, thrift stores, rent assistance, and "
            "spiritual accompaniment of those who suffer."
        ),
        "category": "general",
        "city": "Maryland Heights",
        "state": "MO",
        "country": "US",
        "website": "https://www.svdpusa.org",
        "email": "info@svdpusa.org",
        "phone": "+1-314-576-3993",
    },
    {
        "name": "Cross Catholic Outreach",
        "mission": (
            "Channels aid from Catholics in the United States to the poorest "
            "of the poor overseas — feeding hungry children, building homes for "
            "destitute families, supporting orphanages, and equipping local "
            "priests and religious sisters who serve on the front lines."
        ),
        "category": "international_aid",
        "city": "Boca Raton",
        "state": "FL",
        "country": "US",
        "website": "https://www.crossCatholic.org",
        "email": "info@crosscatholic.org",
        "phone": "+1-800-914-2420",
    },
    {
        "name": "Food for the Poor",
        "mission": (
            "An interdenominational Christian relief organization with deep "
            "Catholic roots, serving the poor of Latin America and the "
            "Caribbean through housing, water, food, and medical care. "
            "Partners with hundreds of parishes and religious communities."
        ),
        "category": "international_aid",
        "city": "Coconut Creek",
        "state": "FL",
        "country": "US",
        "website": "https://www.foodforthepoor.org",
        "email": "info@foodforthepoor.org",
        "phone": "+1-954-427-2222",
    },
    {
        "name": "Aid to the Church in Need",
        "mission": (
            "A pontifical foundation of the Holy See supporting the suffering "
            "and persecuted Church in over 140 countries — rebuilding chapels, "
            "training seminarians, providing Mass stipends to poor priests, "
            "and standing with Christians who face violence for the faith."
        ),
        "category": "international_aid",
        "city": "New York",
        "state": "NY",
        "country": "US",
        "website": "https://www.churchinneed.org",
        "email": "info@churchinneed.org",
        "phone": "+1-800-628-6333",
    },
    {
        "name": "Mary's Meals USA",
        "mission": (
            "Provides one daily meal in a place of education to the world's "
            "hungriest children. Founded by Magnus MacFarlane-Barrow as a "
            "Catholic response to chronic hunger; today feeds more than 2.4 "
            "million children every school day across 18 countries."
        ),
        "category": "international_aid",
        "city": "Bloomington",
        "state": "IN",
        "country": "US",
        "website": "https://www.marysmealsusa.org",
        "email": "info@marysmealsusa.org",
        "phone": "+1-812-558-1080",
    },
    {
        "name": "Knights of Columbus Charities",
        "mission": (
            "The charitable arm of the world's largest Catholic fraternal "
            "service organization. Funds wheelchair distribution, ultrasound "
            "machines for pregnancy resource centers, disaster relief, "
            "Christian Refugee Relief, and seminary scholarships."
        ),
        "category": "general",
        "city": "New Haven",
        "state": "CT",
        "country": "US",
        "website": "https://www.kofc.org/en/charities",
        "email": "info@kofc.org",
        "phone": "+1-203-752-4000",
    },
    {
        "name": "Sisters of Life — Visitation Mission",
        "mission": (
            "A contemplative-active religious community of women dedicated to "
            "the protection and enhancement of the sacredness of every human "
            "life. The Visitation Mission accompanies pregnant women facing "
            "crisis with material, emotional, and spiritual support — entirely "
            "free of charge."
        ),
        "category": "pro_life",
        "city": "Bronx",
        "state": "NY",
        "country": "US",
        "website": "https://sistersoflife.org",
        "email": "info@sistersoflife.org",
        "phone": "+1-718-863-2264",
    },
    {
        "name": "USCCB Migration and Refugee Services",
        "mission": (
            "The largest refugee resettlement agency in the United States, "
            "carrying out the Gospel mandate to welcome the stranger. Helps "
            "refugees, asylum-seekers, and migrants rebuild their lives in "
            "dignity through resettlement, legal support, and integration."
        ),
        "category": "refugee_support",
        "city": "Washington",
        "state": "DC",
        "country": "US",
        "website": "https://www.usccb.org/committees/migration",
        "email": "mrs@usccb.org",
        "phone": "+1-202-541-3000",
    },
    {
        "name": "Catholic Worker Movement",
        "mission": (
            "Founded by Servant of God Dorothy Day and Peter Maurin in 1933 — "
            "an international network of lay communities living in voluntary "
            "poverty, operating houses of hospitality for the homeless, soup "
            "kitchens, and farms rooted in the corporal works of mercy."
        ),
        "category": "homeless_outreach",
        "city": "New York",
        "state": "NY",
        "country": "US",
        "website": "https://www.catholicworker.org",
        "email": None,
        "phone": None,
    },
    {
        "name": "Covenant House — Catholic Founders Network",
        "mission": (
            "Founded by Franciscan Friar Bruce Ritter in 1972, Covenant House "
            "is the largest privately funded charity in the Americas providing "
            "loving care and vital services to homeless, abandoned, abused, "
            "trafficked, and exploited youth ages 16–24."
        ),
        "category": "homeless_outreach",
        "city": "New York",
        "state": "NY",
        "country": "US",
        "website": "https://www.covenanthouse.org",
        "email": "info@covenanthouse.org",
        "phone": "+1-212-727-4000",
    },
    {
        "name": "Mater Filius — Catholic Maternity Homes",
        "mission": (
            "Provides safe, faith-based maternity housing for women in crisis "
            "pregnancies, accompanied by religious sisters and lay volunteers. "
            "Mothers receive shelter, food, counseling, sacramental life, and "
            "vocational training — for as long as they need."
        ),
        "category": "pro_life",
        "city": "Phoenix",
        "state": "AZ",
        "country": "US",
        "website": "https://materfilius.org",
        "email": "info@materfilius.org",
        "phone": None,
    },
]


def _hash(n: str, c: str) -> str:
    return (n + "|" + c).strip().lower()


def main() -> int:
    cli = MongoClient(MONGO_URL)
    db = cli[DB_NAME]

    # Make sure the admin user exists & is admin.
    if db.users.find_one({"user_id": ADMIN_USER_ID}) is None:
        print(
            f"[seed_charities] Admin user {ADMIN_USER_ID} not found — refusing "
            f"to seed (we need an approver_id). Sign in as {ADMIN_EMAIL} first."
        )
        return 1

    # Index existing for idempotency.
    existing = list(
        db.charities.find(
            {"status": {"$ne": "archived"}},
            {"_id": 0, "charity_id": 1, "name": 1, "city": 1},
        )
    )
    have = {_hash(e["name"], e.get("city") or "") for e in existing}

    now = datetime.now(timezone.utc)
    inserted = 0
    skipped = 0
    for entry in CHARITIES:
        key = _hash(entry["name"], entry.get("city") or "")
        if key in have:
            skipped += 1
            continue

        charity_id = f"chr_{secrets.token_hex(6)}"
        doc = {
            "charity_id": charity_id,
            "name": entry["name"].strip(),
            "name_lower": entry["name"].strip().lower(),
            "mission": entry["mission"].strip(),
            "category": entry["category"],
            "city": entry.get("city"),
            "state": (entry.get("state") or "").upper() or None,
            "country": entry.get("country") or "US",
            "website": entry.get("website"),
            "email": entry.get("email"),
            "phone": entry.get("phone"),
            "logo_url": None,
            "status": "approved",
            "submitted_by": ADMIN_USER_ID,
            "submitted_by_email": ADMIN_EMAIL,
            "submitted_at": now,
            "approved_by": ADMIN_USER_ID,
            "approved_at": now,
            "rejected_at": None,
            "rejection_reason": None,
            "claimed_by": None,
            "claim_status": None,
            "claim_history": [],
            "tags": [],
            "verified": True,
            "verified_source": "seed",
            "created_at": now,
            "updated_at": now,
        }
        db.charities.insert_one(doc)
        have.add(key)
        inserted += 1
        print(f"  + {entry['name']} ({entry.get('city') or 'n/a'}, {entry.get('state') or '-'}) — {charity_id}")

    print(f"\n[seed_charities] inserted={inserted} skipped={skipped} total_in_db={db.charities.count_documents({'status': 'approved'})}")
    cli.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
