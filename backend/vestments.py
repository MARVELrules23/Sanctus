"""Liturgical vestments reference, per rite, with real photos.

Each vestment carries a Wikipedia article title; the lead photo is resolved at
request time from the Wikipedia REST summary API (real images, not AI) and
cached in the `vestment_images` collection so we only fetch once.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger("sanctus.vestments")

RITES: List[Dict[str, Any]] = [
    {
        "key": "roman",
        "label": "Roman (Ordinary Form)",
        "blurb": "The vestments of the priest at Mass in the modern Roman Rite. Each is put on with a vesting prayer.",
        "vestments": [
            {"name": "Amice", "wiki": "Amice",
             "meaning": "A rectangular linen cloth tied about the neck and shoulders. The vesting prayer calls it 'the helmet of salvation,' guarding the priest against the assaults of the devil."},
            {"name": "Alb", "wiki": "Alb",
             "meaning": "A long white linen tunic covering the whole body. Its whiteness signifies the purity of soul with which the priest approaches the altar, recalling baptismal innocence."},
            {"name": "Cincture", "wiki": "Cincture",
             "meaning": "A cord tied around the waist to gird the alb. It symbolises chastity and self-mastery — 'Gird me, O Lord, with the cincture of purity.'"},
            {"name": "Stole", "wiki": "Stole (vestment)",
             "meaning": "A long band worn around the neck, the mark of priestly authority and the 'yoke of the Lord.' It signifies the immortality lost by sin and restored by Christ."},
            {"name": "Chasuble", "wiki": "Chasuble",
             "meaning": "The outermost garment, worn over all the rest. It represents charity, which covers all, and the sweet yoke of Christ: 'My yoke is easy and my burden light.' Its colour follows the liturgical season."},
        ],
    },
    {
        "key": "tlm",
        "label": "Traditional Latin (1962)",
        "blurb": "The Traditional Latin Mass keeps two vestments the Ordinary Form made optional: the maniple and (for solemn Mass) the biretta.",
        "vestments": [
            {"name": "Amice", "wiki": "Amice",
             "meaning": "The 'helmet of salvation' laid first upon the shoulders, a defence against distraction and the enemy."},
            {"name": "Alb", "wiki": "Alb",
             "meaning": "The white robe of purity, worn by every cleric, recalling the garment of the newly baptised."},
            {"name": "Cincture", "wiki": "Cincture",
             "meaning": "The cord of chastity binding the alb, a reminder to restrain the desires of the flesh."},
            {"name": "Maniple", "wiki": "Maniple (vestment)",
             "meaning": "A band worn on the left forearm, proper to the traditional Mass. It signifies the tears and toil of this life: 'May I deserve, O Lord, to bear the maniple of weeping and sorrow.'"},
            {"name": "Stole", "wiki": "Stole (vestment)",
             "meaning": "Worn crossed over the breast at the traditional Mass, the stole is the sign of priestly office and the immortality regained in Christ."},
            {"name": "Chasuble", "wiki": "Chasuble",
             "meaning": "The vestment of charity and the yoke of the Lord, often in the fuller 'Roman' or 'Gothic' cut, coloured for the day."},
        ],
    },
    {
        "key": "byzantine",
        "label": "Byzantine (Eastern Catholic)",
        "blurb": "The priest's vestments in the Byzantine Rite, each with a Scripture verse said while vesting.",
        "vestments": [
            {"name": "Sticharion", "wiki": "Sticharion",
             "meaning": "A long tunic of light colour, worn by all ranks of clergy. It signifies purity of soul and the 'garment of salvation and the robe of gladness.'"},
            {"name": "Epitrachelion", "wiki": "Epitrachelion",
             "meaning": "The priestly stole, worn around the neck with both ends hanging in front. It represents the grace of the priesthood poured out, 'like the oil upon the head running down upon the beard.'"},
            {"name": "Zone (Belt)", "wiki": "Zone (vestment)",
             "meaning": "A belt binding the sticharion and epitrachelion, signifying the strength God gives His priest to serve."},
            {"name": "Epimanikia (Cuffs)", "wiki": "Epimanikia",
             "meaning": "Cuffs bound over the wrists, recalling the bonds of Christ and the strength of His right hand; they free the hands for the sacred action."},
            {"name": "Epigonation", "wiki": "Epigonation",
             "meaning": "A stiff diamond-shaped cloth hung at the right knee, an award for priests. It symbolises the 'sword of the Spirit,' Christ's victory over death."},
            {"name": "Phelonion", "wiki": "Phelonion",
             "meaning": "The great cape-like outer vestment of the priest, corresponding to the chasuble. It clothes him wholly in the grace and truth of Christ."},
        ],
    },
]


_WIKI_UA = "SanctusCatholicApp/1.0 (https://sanctus.app; contact@sanctus.app)"


async def _resolve_images(titles: List[str]) -> Dict[str, Optional[str]]:
    """Resolve lead photos for several Wikipedia article titles in one call
    via the MediaWiki action API (the REST summary API blocks generic clients)."""
    out: Dict[str, Optional[str]] = {t: None for t in titles}
    if not titles:
        return out
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "pageimages",
        "piprop": "thumbnail",
        "pithumbsize": "800",
        "redirects": "1",
        "titles": "|".join(titles),
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            r = await client.get(url, params=params, headers={"User-Agent": _WIKI_UA}, timeout=12.0)
            if r.status_code != 200:
                return out
            data = r.json()
            # Map any redirect targets back to the requested title.
            norm = {n["to"]: n["from"] for n in data.get("query", {}).get("normalized", [])}
            redir = {rd["to"]: rd["from"] for rd in data.get("query", {}).get("redirects", [])}
            for _pid, pg in data.get("query", {}).get("pages", {}).items():
                title = pg.get("title", "")
                src = (pg.get("thumbnail") or {}).get("source")
                # resolve back through redirect + normalization chains
                key = title
                key = redir.get(key, key)
                key = norm.get(key, key)
                if key in out:
                    out[key] = src
                elif title in out:
                    out[title] = src
    except Exception as e:  # noqa: BLE001
        logger.warning("vestment image batch resolve failed: %s", e)
    return out


def build_router(db: AsyncIOMotorDatabase, get_current_user, *_ignore) -> APIRouter:
    router = APIRouter(prefix="/vestments", tags=["vestments"])
    cache = db["vestment_images"]

    @router.get("")
    async def get_vestments(user=Depends(get_current_user)):
        # Gather all wiki titles needing images.
        titles = {v["wiki"] for rite in RITES for v in rite["vestments"]}
        images: Dict[str, Optional[str]] = {}
        missing = []
        async for doc in cache.find({"title": {"$in": list(titles)}}):
            images[doc["title"]] = doc.get("image")
        missing = [t for t in titles if t not in images or images[t] is None]
        if missing:
            resolved = await _resolve_images(missing)
            for t, img in resolved.items():
                images[t] = img
                await cache.update_one({"title": t}, {"$set": {"title": t, "image": img}}, upsert=True)
        out = []
        for rite in RITES:
            out.append({
                "key": rite["key"],
                "label": rite["label"],
                "blurb": rite["blurb"],
                "vestments": [
                    {"name": v["name"], "meaning": v["meaning"], "image": images.get(v["wiki"])}
                    for v in rite["vestments"]
                ],
            })
        return {"rites": out}

    return router
