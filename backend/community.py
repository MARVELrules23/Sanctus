"""Sanctus Community — global parish feed, topical rooms, and 1-on-1 DMs."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Predefined topical "rooms". `slug=None` => Global parish feed.
TOPICS: List[Dict[str, Any]] = [
    {"slug": None,                 "label": "Parish",            "icon": "people-outline"},
    {"slug": "daily-mass",         "label": "Daily Mass",        "icon": "book-outline"},
    {"slug": "rosary",             "label": "Rosary",            "icon": "rose-outline"},
    {"slug": "saints",             "label": "Saints & Devotions","icon": "star-outline"},
    {"slug": "scripture",          "label": "Scripture",         "icon": "library-outline"},
    {"slug": "family-life",        "label": "Family Life",       "icon": "home-outline"},
    {"slug": "young-adults",       "label": "Young Adults",      "icon": "sparkles-outline"},
    {"slug": "wellness-holiness",  "label": "Wellness & Holiness","icon": "fitness-outline"},
    {"slug": "vocations",          "label": "Vocations",         "icon": "ribbon-outline"},
    {"slug": "confession",         "label": "Confession & Examen","icon": "leaf-outline"},
]

TOPIC_SLUGS = {t["slug"] for t in TOPICS if t["slug"]}

REPORT_REASONS = [
    "Inappropriate content",
    "Harassment or hateful speech",
    "Spam or misleading",
    "Doctrinal error / scandal",
    "Other",
]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def thread_key(a: str, b: str) -> str:
    """Deterministic key for a 1-on-1 DM thread."""
    x, y = sorted([a, b])
    return f"{x}__{y}"


def public_user(u: Dict[str, Any]) -> Dict[str, Any]:
    """Trim user document for community surfaces."""
    return {
        "user_id": u.get("user_id"),
        "name": u.get("name") or (u.get("email") or "").split("@")[0],
        "picture": u.get("picture"),
    }


def post_public(p: Dict[str, Any], author: Optional[Dict[str, Any]],
                liked_by_me: bool = False) -> Dict[str, Any]:
    """Project a post document for the client."""
    return {
        "post_id": p.get("post_id"),
        "author": public_user(author) if author else {"user_id": p.get("author_id"), "name": "Unknown", "picture": None},
        "body": p.get("body", ""),
        "topic": p.get("topic"),
        "liturgical_color": p.get("liturgical_color"),
        "liturgical_season": p.get("liturgical_season"),
        "created_at": iso(p.get("created_at")),
        "like_count": int(p.get("like_count") or 0),
        "reply_count": int(p.get("reply_count") or 0),
        "liked_by_me": bool(liked_by_me),
        "image": p.get("image"),
        "is_pinned": bool(p.get("is_pinned")),
    }


def reply_public(r: Dict[str, Any], author: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "reply_id": r.get("reply_id"),
        "post_id": r.get("post_id"),
        "author": public_user(author) if author else {"user_id": r.get("author_id"), "name": "Unknown", "picture": None},
        "body": r.get("body", ""),
        "created_at": iso(r.get("created_at")),
    }


def message_public(m: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "message_id": m.get("message_id"),
        "thread_id": m.get("thread_id"),
        "sender_id": m.get("sender_id"),
        "body": m.get("body", ""),
        "created_at": iso(m.get("created_at")),
    }


def thread_public(t: Dict[str, Any], other_user: Optional[Dict[str, Any]],
                  unread: int = 0) -> Dict[str, Any]:
    return {
        "thread_id": t.get("thread_id"),
        "other": public_user(other_user) if other_user else None,
        "last_message": t.get("last_message"),
        "last_message_at": iso(t.get("last_message_at")),
        "unread": unread,
    }


# Validation helpers
MAX_POST_LEN = 1500
MAX_REPLY_LEN = 800
MAX_DM_LEN = 1500


def clean_body(text: str, limit: int) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if len(text) > limit:
        text = text[:limit].rstrip()
    return text
