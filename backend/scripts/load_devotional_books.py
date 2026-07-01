"""
Upsert curated devotional BOOKS as external-link library entries.

These open the full text in the in-app browser (type="external"). Topics:
Guardian Angels, the Blessed Mother, St. Joseph, and the Saints. Sources are
public-domain classics or reputable Catholic libraries (New Advent, CCEL, EWTN).

Usage:
    cd /app/backend && python -m scripts.load_devotional_books
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

BOOKS: List[Dict] = [
    # ---- Guardian Angels ----
    {
        "slug": "treatise-on-the-angels",
        "title": "Treatise on the Angels",
        "author": "St. Thomas Aquinas",
        "year": 1274,
        "blurb": "The Angelic Doctor's classic treatment of the angels — their nature, knowledge, and guardianship — from the Summa Theologiae (I, QQ. 50–64).",
        "tradition": "doctor",
        "cover_color": "#4A5D8A",
        "cover_icon": "sparkles-outline",
        "source_url": "https://www.newadvent.org/summa/1050.htm",
    },
    {
        "slug": "the-guardian-angel",
        "title": "The Guardian Angel",
        "author": "Catholic Encyclopedia",
        "year": 1910,
        "blurb": "A concise, authoritative survey of the Church's teaching and devotion regarding each person's Guardian Angel.",
        "tradition": "catholic-classic",
        "cover_color": "#4A7C8C",
        "cover_icon": "shield-outline",
        "source_url": "https://www.newadvent.org/cathen/07049c.htm",
    },
    {
        "slug": "devotion-to-the-guardian-angels",
        "title": "Devotion to the Guardian Angels",
        "author": "EWTN Library",
        "year": 2000,
        "blurb": "Prayers, Scripture, and the tradition of the Church on our Guardian Angels — how to know, thank, and follow them.",
        "tradition": "catholic-classic",
        "cover_color": "#5C7A99",
        "cover_icon": "sparkles-outline",
        "source_url": "https://www.ewtn.com/catholicism/devotions/guardian-angels-21200",
    },
    # ---- Blessed Mother ----
    {
        "slug": "the-glories-of-mary",
        "title": "The Glories of Mary",
        "author": "St. Alphonsus Liguori",
        "year": 1750,
        "blurb": "The beloved classic of Marian devotion — a prayerful commentary on the Salve Regina and Our Lady's titles, feasts, and virtues.",
        "tradition": "doctor",
        "cover_color": "#3F62A8",
        "cover_icon": "star-outline",
        "source_url": "https://www.ewtn.com/catholicism/library/glories-of-mary-11433",
    },
    {
        "slug": "true-devotion-to-mary",
        "title": "True Devotion to Mary",
        "author": "St. Louis de Montfort",
        "year": 1712,
        "blurb": "The foundational text of total consecration to Jesus through Mary — 'to Jesus through Mary' as the surest, easiest path to holiness.",
        "tradition": "catholic-classic",
        "cover_color": "#5B21B6",
        "cover_icon": "flower-outline",
        "source_url": "https://www.ewtn.com/catholicism/library/true-devotion-to-mary-11376",
    },
    # ---- St. Joseph ----
    {
        "slug": "life-and-glories-of-st-joseph",
        "title": "The Life and Glories of St. Joseph",
        "author": "Edward Healy Thompson",
        "year": 1888,
        "blurb": "A rich, devotional life of St. Joseph — his dignity, virtues, patronage, and role as Guardian of the Redeemer.",
        "tradition": "catholic-classic",
        "cover_color": "#7A5C00",
        "cover_icon": "hammer-outline",
        "source_url": "https://www.ewtn.com/catholicism/library/life-and-glories-of-st-joseph-11363",
    },
    # ---- Saints ----
    {
        "slug": "story-of-a-soul",
        "title": "The Story of a Soul",
        "author": "St. Thérèse of Lisieux",
        "year": 1898,
        "blurb": "The autobiography of the 'Little Flower,' Doctor of the Church — her 'little way' of spiritual childhood, trust, and love.",
        "tradition": "doctor",
        "cover_color": "#9E4A63",
        "cover_icon": "rose-outline",
        "source_url": "https://www.ccel.org/ccel/therese/autobio.html",
    },
]


async def main() -> None:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ.get("DB_NAME", "sanctus")]
    now = datetime.now(timezone.utc)
    for meta in BOOKS:
        slug = meta["slug"]
        doc = {
            "book_id": str(uuid.uuid4()),
            "slug": slug,
            "title": meta["title"],
            "author": meta["author"],
            "year": meta["year"],
            "blurb": meta["blurb"],
            "tradition": meta["tradition"],
            "cover_color": meta["cover_color"],
            "cover_icon": meta["cover_icon"],
            "type": "external",
            "status": "published",
            "source_url": meta["source_url"],
            "chapters": [],
            "created_at": now,
            "updated_at": now,
        }
        existing = await db["library_books"].find_one({"slug": slug}, {"book_id": 1})
        if existing and existing.get("book_id"):
            doc["book_id"] = existing["book_id"]
            doc.pop("created_at", None)
        await db["library_books"].replace_one({"slug": slug}, doc, upsert=True)
        print(f"  ✓ {slug}")


if __name__ == "__main__":
    asyncio.run(main())
