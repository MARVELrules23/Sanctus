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
        "challenge": p.get("challenge"),
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
                  unread: int = 0,
                  members_lookup: Optional[Dict[str, Dict[str, Any]]] = None,
                  viewer_id: Optional[str] = None) -> Dict[str, Any]:
    """Project a DM thread for the client.

    Backwards-compatible with 1-on-1 threads: `other` is set to the other
    member's public user for non-group threads. Group threads get the
    full `members` array, `is_group`, `name`, and an `auto_name` fallback
    so the client can render "Mary, John + 3" when no custom name is set.
    """
    is_group = bool(t.get("is_group"))
    member_ids: List[str] = list(t.get("member_ids") or [])
    out: Dict[str, Any] = {
        "thread_id": t.get("thread_id"),
        "is_group": is_group,
        "name": t.get("name"),
        "created_by": t.get("created_by"),
        "last_message": t.get("last_message"),
        "last_message_at": iso(t.get("last_message_at")),
        "unread": unread,
    }
    if is_group:
        # Resolve all members; fall back to a stub if a member was deleted.
        members_lookup = members_lookup or {}
        members = []
        for mid in member_ids:
            u = members_lookup.get(mid)
            members.append(public_user(u) if u else {"user_id": mid, "name": "Unknown", "picture": None})
        out["members"] = members
        # Auto-name uses everyone except the viewer for a contextual title.
        names = [m["name"] for m in members if m["user_id"] != viewer_id]
        if not names:
            names = [m["name"] for m in members]
        if len(names) <= 3:
            out["auto_name"] = ", ".join(names)
        else:
            out["auto_name"] = f"{', '.join(names[:2])} + {len(names) - 2} others"
        out["other"] = None
    else:
        out["other"] = public_user(other_user) if other_user else None
        out["members"] = None
        out["auto_name"] = None
    return out


def friendship_key(a: str, b: str) -> str:
    """Deterministic key so a friendship is unique regardless of who initiated."""
    x, y = sorted([a, b])
    return f"{x}__{y}"


def friendship_public(f: Dict[str, Any],
                      other_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Project a friendship row for the client."""
    return {
        "friendship_id": f.get("friendship_id"),
        "user": public_user(other_user) if other_user else None,
        "status": f.get("status", "pending"),       # pending | accepted
        "requested_by": f.get("requested_by"),      # who sent the original request
        "created_at": iso(f.get("created_at")),
        "accepted_at": iso(f.get("accepted_at")),
    }


# Validation helpers
MAX_POST_LEN = 1500
MAX_REPLY_LEN = 800
MAX_DM_LEN = 1500
MAX_GROUP_MEMBERS = 50
MAX_GROUP_NAME_LEN = 60


def clean_body(text: str, limit: int) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if len(text) > limit:
        text = text[:limit].rstrip()
    return text


def clean_group_name(text: Optional[str]) -> Optional[str]:
    """Trim and validate a group-chat name. Returns None if empty (so the
    client falls back to the auto-name)."""
    if not text:
        return None
    s = text.strip()
    if not s:
        return None
    if len(s) > MAX_GROUP_NAME_LEN:
        s = s[:MAX_GROUP_NAME_LEN].rstrip()
    return s
