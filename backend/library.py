"""Sanctus Library — Phase 1 (Books).

Endpoints:
  GET    /api/library/books                       — list published books
  GET    /api/library/books/{slug}                — book detail (incl. chapters meta + reading progress)
  GET    /api/library/books/{slug}/chapters/{n}   — single chapter markdown
  POST   /api/library/books/{slug}/progress       — save reading position
  GET    /api/library/books/{slug}/progress       — get reading position

Admin (is_admin):
  GET    /api/library/admin/books                 — list ALL books (incl. drafts)
  POST   /api/library/admin/books                 — create a book
  PATCH  /api/library/admin/books/{slug}          — patch book
  DELETE /api/library/admin/books/{slug}          — delete book
  POST   /api/library/admin/books/{slug}/chapters — append/replace chapter
  DELETE /api/library/admin/books/{slug}/chapters/{n} — remove chapter

Phase 2 (Radio) & Phase 3 (Films) will live in this same router.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from library_seed_data import SEED_BOOKS, SEED_FILMS, SEED_STATIONS

logger = logging.getLogger("sanctus.library")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ChapterModel(BaseModel):
    title: str
    body_md: str


class BookCreateModel(BaseModel):
    slug: str
    title: str
    author: str
    year: Optional[int] = None
    blurb: Optional[str] = None
    tradition: Optional[str] = "catholic-classic"
    cover_color: Optional[str] = None
    cover_icon: Optional[str] = None
    type: str = Field("embedded", pattern="^(embedded|external)$")
    source_url: Optional[str] = None
    chapters: List[ChapterModel] = Field(default_factory=list)
    status: str = Field("published", pattern="^(draft|published)$")


class BookPatchModel(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    blurb: Optional[str] = None
    tradition: Optional[str] = None
    cover_color: Optional[str] = None
    cover_icon: Optional[str] = None
    type: Optional[str] = Field(None, pattern="^(embedded|external)$")
    source_url: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|published)$")


class ChapterUpsertModel(BaseModel):
    index: Optional[int] = None  # None → append, otherwise replace at index
    title: str
    body_md: str


class ProgressUpdateModel(BaseModel):
    chapter_index: int = Field(ge=0)
    scroll_pct: float = Field(ge=0.0, le=1.0, default=0.0)


# ---- Radio ----
class StationCreateModel(BaseModel):
    slug: str
    name: str
    blurb: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    stream_url: str
    website_url: Optional[str] = None
    accent_color: Optional[str] = None
    icon: Optional[str] = "radio-outline"
    status: str = Field("published", pattern="^(draft|published)$")


class StationPatchModel(BaseModel):
    name: Optional[str] = None
    blurb: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    stream_url: Optional[str] = None
    website_url: Optional[str] = None
    accent_color: Optional[str] = None
    icon: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|published)$")


# ---- Films ----
class FilmCreateModel(BaseModel):
    slug: str
    title: str
    blurb: Optional[str] = None
    youtube_id: str
    duration_label: Optional[str] = None
    category: str = Field("documentary", pattern="^(saints|doctrine|animated|documentary)$")
    accent_color: Optional[str] = None
    status: str = Field("published", pattern="^(draft|published)$")


class FilmPatchModel(BaseModel):
    title: Optional[str] = None
    blurb: Optional[str] = None
    youtube_id: Optional[str] = None
    duration_label: Optional[str] = None
    category: Optional[str] = Field(None, pattern="^(saints|doctrine|animated|documentary)$")
    accent_color: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|published)$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _public_book(doc: Dict[str, Any], include_chapter_bodies: bool = False) -> Dict[str, Any]:
    """Project a book doc for public consumption."""
    chapters = doc.get("chapters") or []
    chapters_out: List[Dict[str, Any]] = []
    for i, c in enumerate(chapters):
        item: Dict[str, Any] = {
            "index": i,
            "title": c.get("title", f"Chapter {i + 1}"),
            "word_count": _word_count(c.get("body_md", "")),
        }
        if include_chapter_bodies:
            item["body_md"] = c.get("body_md", "")
        chapters_out.append(item)
    return {
        "book_id": doc.get("book_id"),
        "slug": doc.get("slug"),
        "title": doc.get("title"),
        "author": doc.get("author"),
        "year": doc.get("year"),
        "blurb": doc.get("blurb"),
        "tradition": doc.get("tradition") or "catholic-classic",
        "cover_color": doc.get("cover_color"),
        "cover_icon": doc.get("cover_icon"),
        "type": doc.get("type") or "embedded",
        "source_url": doc.get("source_url"),
        "status": doc.get("status") or "published",
        "chapter_count": len(chapters_out),
        "chapters": chapters_out,
    }


def _admin_book(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = _public_book(doc, include_chapter_bodies=True)
    out["created_at"] = (doc.get("created_at") or datetime.now(timezone.utc)).isoformat()
    out["updated_at"] = (doc.get("updated_at") or out["created_at"]).isoformat()
    return out


def _word_count(s: str) -> int:
    if not s:
        return 0
    return len([w for w in s.split() if w])


async def _seed_books_if_missing(db: AsyncIOMotorDatabase) -> int:
    """Insert seed books only when they don't already exist (by slug)."""
    inserted = 0
    for entry in SEED_BOOKS:
        existing = await db["library_books"].find_one({"slug": entry["slug"]}, {"_id": 0, "slug": 1})
        if existing:
            continue
        now = datetime.now(timezone.utc)
        doc = {
            "book_id": f"bk_{uuid.uuid4().hex[:10]}",
            "slug": entry["slug"],
            "title": entry["title"],
            "author": entry["author"],
            "year": entry.get("year"),
            "blurb": entry.get("blurb"),
            "tradition": entry.get("tradition", "catholic-classic"),
            "cover_color": entry.get("cover_color"),
            "cover_icon": entry.get("cover_icon"),
            "type": entry.get("type", "embedded"),
            "source_url": entry.get("source_url"),
            "chapters": entry.get("chapters", []),
            "status": "published",
            "created_at": now,
            "updated_at": now,
        }
        await db["library_books"].insert_one(doc)
        inserted += 1
    if inserted:
        logger.info("library: seeded %d books", inserted)
    return inserted


async def _seed_stations_if_missing(db: AsyncIOMotorDatabase) -> int:
    inserted = 0
    for entry in SEED_STATIONS:
        existing = await db["library_radio_stations"].find_one(
            {"slug": entry["slug"]}, {"_id": 0, "slug": 1}
        )
        if existing:
            continue
        now = datetime.now(timezone.utc)
        doc = {
            "station_id": f"st_{uuid.uuid4().hex[:10]}",
            "status": "published",
            "created_at": now,
            "updated_at": now,
            **entry,
        }
        await db["library_radio_stations"].insert_one(doc)
        inserted += 1
    if inserted:
        logger.info("library: seeded %d radio stations", inserted)
    return inserted


async def _seed_films_if_missing(db: AsyncIOMotorDatabase) -> int:
    inserted = 0
    for entry in SEED_FILMS:
        existing = await db["library_films"].find_one(
            {"slug": entry["slug"]}, {"_id": 0, "slug": 1}
        )
        if existing:
            continue
        now = datetime.now(timezone.utc)
        doc = {
            "film_id": f"fm_{uuid.uuid4().hex[:10]}",
            "status": "published",
            "created_at": now,
            "updated_at": now,
            **entry,
        }
        await db["library_films"].insert_one(doc)
        inserted += 1
    if inserted:
        logger.info("library: seeded %d films", inserted)
    return inserted


def _public_station(d: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "station_id": d.get("station_id"),
        "slug": d.get("slug"),
        "name": d.get("name"),
        "blurb": d.get("blurb"),
        "country": d.get("country"),
        "language": d.get("language"),
        "stream_url": d.get("stream_url"),
        "website_url": d.get("website_url"),
        "accent_color": d.get("accent_color"),
        "icon": d.get("icon") or "radio-outline",
        "status": d.get("status") or "published",
    }


def _public_film(d: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "film_id": d.get("film_id"),
        "slug": d.get("slug"),
        "title": d.get("title"),
        "blurb": d.get("blurb"),
        "youtube_id": d.get("youtube_id"),
        "duration_label": d.get("duration_label"),
        "category": d.get("category") or "documentary",
        "accent_color": d.get("accent_color"),
        "status": d.get("status") or "published",
    }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def build_router(db: AsyncIOMotorDatabase, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/library", tags=["library"])

    books = db["library_books"]
    progress = db["library_reading_progress"]

    async def _ensure_admin(user) -> None:
        if not user or not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="Admin only")

    async def _get_book_or_404(slug: str, allow_drafts: bool = False):
        q: Dict[str, Any] = {"slug": slug}
        if not allow_drafts:
            q["status"] = "published"
        doc = await books.find_one(q, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="book not found")
        return doc

    # ----------------------------- Public -----------------------------------

    @router.get("/books")
    async def list_books(user=Depends(get_current_user)):
        await _seed_books_if_missing(db)
        is_admin = bool(getattr(user, "is_admin", False))
        q: Dict[str, Any] = {} if is_admin else {"status": "published"}
        cur = books.find(q, {"_id": 0}).sort([("year", 1), ("title", 1)])
        items = [_public_book(d) async for d in cur]
        return {"items": items, "total": len(items)}

    @router.get("/books/{slug}")
    async def get_book(slug: str, user=Depends(get_current_user)):
        is_admin = bool(getattr(user, "is_admin", False))
        doc = await _get_book_or_404(slug, allow_drafts=is_admin)
        out = _public_book(doc)
        # Embed reading progress for the current user if any
        prog = await progress.find_one(
            {"user_id": user.user_id, "book_id": doc["book_id"]}, {"_id": 0}
        )
        if prog:
            out["progress"] = {
                "chapter_index": int(prog.get("chapter_index", 0)),
                "scroll_pct": float(prog.get("scroll_pct", 0.0)),
                "updated_at": (prog.get("updated_at") or datetime.now(timezone.utc)).isoformat(),
            }
        else:
            out["progress"] = None
        return out

    @router.get("/books/{slug}/chapters/{idx}")
    async def get_chapter(slug: str, idx: int, user=Depends(get_current_user)):
        is_admin = bool(getattr(user, "is_admin", False))
        doc = await _get_book_or_404(slug, allow_drafts=is_admin)
        chapters = doc.get("chapters") or []
        if idx < 0 or idx >= len(chapters):
            raise HTTPException(status_code=404, detail="chapter not found")
        c = chapters[idx]
        return {
            "book_id": doc["book_id"],
            "slug": doc["slug"],
            "chapter_index": idx,
            "title": c.get("title", f"Chapter {idx + 1}"),
            "body_md": c.get("body_md", ""),
            "is_last": idx == len(chapters) - 1,
            "word_count": _word_count(c.get("body_md", "")),
        }

    @router.get("/books/{slug}/progress")
    async def get_progress(slug: str, user=Depends(get_current_user)):
        doc = await _get_book_or_404(slug)
        prog = await progress.find_one(
            {"user_id": user.user_id, "book_id": doc["book_id"]}, {"_id": 0}
        )
        if not prog:
            return {"chapter_index": 0, "scroll_pct": 0.0, "exists": False}
        return {
            "chapter_index": int(prog.get("chapter_index", 0)),
            "scroll_pct": float(prog.get("scroll_pct", 0.0)),
            "exists": True,
            "updated_at": (prog.get("updated_at") or datetime.now(timezone.utc)).isoformat(),
        }

    @router.post("/books/{slug}/progress")
    async def save_progress(
        slug: str,
        payload: ProgressUpdateModel,
        user=Depends(get_current_user),
    ):
        doc = await _get_book_or_404(slug)
        now = datetime.now(timezone.utc)
        await progress.update_one(
            {"user_id": user.user_id, "book_id": doc["book_id"]},
            {
                "$set": {
                    "user_id": user.user_id,
                    "book_id": doc["book_id"],
                    "chapter_index": int(payload.chapter_index),
                    "scroll_pct": float(payload.scroll_pct),
                    "updated_at": now,
                }
            },
            upsert=True,
        )
        return {"ok": True, "chapter_index": payload.chapter_index, "scroll_pct": payload.scroll_pct}

    # ----------------------------- Admin ------------------------------------

    @router.get("/admin/books")
    async def admin_list(user=Depends(get_current_user)):
        await _ensure_admin(user)
        await _seed_books_if_missing(db)
        cur = books.find({}, {"_id": 0}).sort([("created_at", -1)])
        items = [_admin_book(d) async for d in cur]
        return {"items": items, "total": len(items)}

    @router.post("/admin/books")
    async def admin_create(payload: BookCreateModel, user=Depends(get_current_user)):
        await _ensure_admin(user)
        existing = await books.find_one({"slug": payload.slug}, {"_id": 0, "slug": 1})
        if existing:
            raise HTTPException(status_code=409, detail="slug already exists")
        now = datetime.now(timezone.utc)
        doc = {
            "book_id": f"bk_{uuid.uuid4().hex[:10]}",
            "slug": payload.slug,
            "title": payload.title,
            "author": payload.author,
            "year": payload.year,
            "blurb": payload.blurb,
            "tradition": payload.tradition or "catholic-classic",
            "cover_color": payload.cover_color,
            "cover_icon": payload.cover_icon,
            "type": payload.type,
            "source_url": payload.source_url,
            "chapters": [c.model_dump() for c in payload.chapters],
            "status": payload.status,
            "created_at": now,
            "updated_at": now,
        }
        await books.insert_one(doc)
        return _admin_book(doc)

    @router.patch("/admin/books/{slug}")
    async def admin_patch(slug: str, payload: BookPatchModel, user=Depends(get_current_user)):
        await _ensure_admin(user)
        doc = await books.find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="book not found")
        updates: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        for f in (
            "title", "author", "year", "blurb", "tradition",
            "cover_color", "cover_icon", "type", "source_url", "status",
        ):
            v = getattr(payload, f)
            if v is not None:
                updates[f] = v
        await books.update_one({"slug": slug}, {"$set": updates})
        fresh = await books.find_one({"slug": slug}, {"_id": 0})
        return _admin_book(fresh)

    @router.delete("/admin/books/{slug}")
    async def admin_delete(slug: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        doc = await books.find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="book not found")
        await books.delete_one({"slug": slug})
        # Best-effort: drop any reading-progress rows for that book.
        await progress.delete_many({"book_id": doc["book_id"]})
        return {"ok": True, "slug": slug}

    @router.post("/admin/books/{slug}/chapters")
    async def admin_upsert_chapter(
        slug: str,
        payload: ChapterUpsertModel,
        user=Depends(get_current_user),
    ):
        await _ensure_admin(user)
        doc = await books.find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="book not found")
        chapters = list(doc.get("chapters") or [])
        new_ch = {"title": payload.title, "body_md": payload.body_md}
        if payload.index is None or payload.index >= len(chapters):
            chapters.append(new_ch)
            new_index = len(chapters) - 1
        else:
            if payload.index < 0:
                raise HTTPException(status_code=400, detail="invalid index")
            chapters[payload.index] = new_ch
            new_index = payload.index
        await books.update_one(
            {"slug": slug},
            {"$set": {"chapters": chapters, "updated_at": datetime.now(timezone.utc)}},
        )
        return {"ok": True, "chapter_index": new_index, "chapter_count": len(chapters)}

    @router.delete("/admin/books/{slug}/chapters/{idx}")
    async def admin_delete_chapter(slug: str, idx: int, user=Depends(get_current_user)):
        await _ensure_admin(user)
        doc = await books.find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="book not found")
        chapters = list(doc.get("chapters") or [])
        if idx < 0 or idx >= len(chapters):
            raise HTTPException(status_code=404, detail="chapter not found")
        chapters.pop(idx)
        await books.update_one(
            {"slug": slug},
            {"$set": {"chapters": chapters, "updated_at": datetime.now(timezone.utc)}},
        )
        return {"ok": True, "chapter_count": len(chapters)}

    # -------------------------------------------------------------------- #
    # Phase 2 — RADIO                                                      #
    # -------------------------------------------------------------------- #
    stations = db["library_radio_stations"]

    @router.get("/radio")
    async def list_stations(user=Depends(get_current_user)):
        await _seed_stations_if_missing(db)
        is_admin = bool(getattr(user, "is_admin", False))
        q: Dict[str, Any] = {} if is_admin else {"status": "published"}
        cur = stations.find(q, {"_id": 0}).sort([("name", 1)])
        items = [_public_station(d) async for d in cur]
        return {"items": items, "total": len(items)}

    @router.get("/radio/{slug}")
    async def get_station(slug: str, user=Depends(get_current_user)):
        is_admin = bool(getattr(user, "is_admin", False))
        q: Dict[str, Any] = {"slug": slug}
        if not is_admin:
            q["status"] = "published"
        doc = await stations.find_one(q, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="station not found")
        return _public_station(doc)

    @router.get("/admin/radio")
    async def admin_list_stations(user=Depends(get_current_user)):
        await _ensure_admin(user)
        await _seed_stations_if_missing(db)
        cur = stations.find({}, {"_id": 0}).sort([("created_at", -1)])
        items = [_public_station(d) async for d in cur]
        return {"items": items, "total": len(items)}

    @router.post("/admin/radio")
    async def admin_create_station(payload: StationCreateModel, user=Depends(get_current_user)):
        await _ensure_admin(user)
        existing = await stations.find_one({"slug": payload.slug}, {"_id": 0, "slug": 1})
        if existing:
            raise HTTPException(status_code=409, detail="slug already exists")
        now = datetime.now(timezone.utc)
        doc = {
            "station_id": f"st_{uuid.uuid4().hex[:10]}",
            "created_at": now,
            "updated_at": now,
            **payload.model_dump(),
        }
        await stations.insert_one(doc)
        return _public_station(doc)

    @router.patch("/admin/radio/{slug}")
    async def admin_patch_station(
        slug: str, payload: StationPatchModel, user=Depends(get_current_user)
    ):
        await _ensure_admin(user)
        doc = await stations.find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="station not found")
        updates: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        for f, v in payload.model_dump(exclude_unset=True).items():
            if v is not None:
                updates[f] = v
        await stations.update_one({"slug": slug}, {"$set": updates})
        fresh = await stations.find_one({"slug": slug}, {"_id": 0})
        return _public_station(fresh)

    @router.delete("/admin/radio/{slug}")
    async def admin_delete_station(slug: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        res = await stations.delete_one({"slug": slug})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="station not found")
        return {"ok": True, "slug": slug}

    # -------------------------------------------------------------------- #
    # Phase 3 — FILMS                                                      #
    # -------------------------------------------------------------------- #
    films = db["library_films"]

    @router.get("/films")
    async def list_films(
        category: Optional[str] = None,
        user=Depends(get_current_user),
    ):
        await _seed_films_if_missing(db)
        is_admin = bool(getattr(user, "is_admin", False))
        q: Dict[str, Any] = {} if is_admin else {"status": "published"}
        if category and category in {"saints", "doctrine", "animated", "documentary"}:
            q["category"] = category
        cur = films.find(q, {"_id": 0}).sort([("category", 1), ("title", 1)])
        items = [_public_film(d) async for d in cur]
        return {"items": items, "total": len(items)}

    @router.get("/films/{slug}")
    async def get_film(slug: str, user=Depends(get_current_user)):
        is_admin = bool(getattr(user, "is_admin", False))
        q: Dict[str, Any] = {"slug": slug}
        if not is_admin:
            q["status"] = "published"
        doc = await films.find_one(q, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="film not found")
        return _public_film(doc)

    @router.get("/admin/films")
    async def admin_list_films(user=Depends(get_current_user)):
        await _ensure_admin(user)
        await _seed_films_if_missing(db)
        cur = films.find({}, {"_id": 0}).sort([("created_at", -1)])
        items = [_public_film(d) async for d in cur]
        return {"items": items, "total": len(items)}

    @router.post("/admin/films")
    async def admin_create_film(payload: FilmCreateModel, user=Depends(get_current_user)):
        await _ensure_admin(user)
        existing = await films.find_one({"slug": payload.slug}, {"_id": 0, "slug": 1})
        if existing:
            raise HTTPException(status_code=409, detail="slug already exists")
        now = datetime.now(timezone.utc)
        doc = {
            "film_id": f"fm_{uuid.uuid4().hex[:10]}",
            "created_at": now,
            "updated_at": now,
            **payload.model_dump(),
        }
        await films.insert_one(doc)
        return _public_film(doc)

    @router.patch("/admin/films/{slug}")
    async def admin_patch_film(
        slug: str, payload: FilmPatchModel, user=Depends(get_current_user)
    ):
        await _ensure_admin(user)
        doc = await films.find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="film not found")
        updates: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        for f, v in payload.model_dump(exclude_unset=True).items():
            if v is not None:
                updates[f] = v
        await films.update_one({"slug": slug}, {"$set": updates})
        fresh = await films.find_one({"slug": slug}, {"_id": 0})
        return _public_film(fresh)

    @router.delete("/admin/films/{slug}")
    async def admin_delete_film(slug: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        res = await films.delete_one({"slug": slug})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="film not found")
        return {"ok": True, "slug": slug}

    return router


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db["library_books"].create_index("book_id", unique=True)
    await db["library_books"].create_index("slug", unique=True)
    await db["library_books"].create_index([("status", 1), ("title", 1)])
    await db["library_reading_progress"].create_index(
        [("user_id", 1), ("book_id", 1)], unique=True
    )
    # Radio
    await db["library_radio_stations"].create_index("station_id", unique=True)
    await db["library_radio_stations"].create_index("slug", unique=True)
    await db["library_radio_stations"].create_index([("status", 1), ("name", 1)])
    # Films
    await db["library_films"].create_index("film_id", unique=True)
    await db["library_films"].create_index("slug", unique=True)
    await db["library_films"].create_index([("status", 1), ("category", 1), ("title", 1)])
    try:
        n = await _seed_books_if_missing(db)
        if n:
            logger.info("library: seeded %d books on startup", n)
        ns = await _seed_stations_if_missing(db)
        if ns:
            logger.info("library: seeded %d radio stations on startup", ns)
        nf = await _seed_films_if_missing(db)
        if nf:
            logger.info("library: seeded %d films on startup", nf)
    except Exception as e:  # noqa: BLE001
        logger.warning("library seed skipped: %s", e)
