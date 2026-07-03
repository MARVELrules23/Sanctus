"""Legal / Support pages for Sanctus.

These endpoints serve a public Privacy Policy and Support page (suitable for
linking from app store listings) plus a small contact-form endpoint that
records support tickets in MongoDB for the maintainer to follow up on.

The HTML rendered here is intentionally self-contained (inline styles) so it
renders correctly when a reviewer or end-user opens the URL in a plain
browser — no static asset pipeline required.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr, Field


log = logging.getLogger("sanctus.legal")

SUPPORT_EMAIL = "philipwils13@gmail.com"
APP_NAME = "Sanctus"
LAST_UPDATED = "June 9, 2026"


# ----------------------------------------------------------------------------
# Plain-text content (also returned as JSON for the in-app screens).
# ----------------------------------------------------------------------------

PRIVACY_POLICY_SECTIONS = [
    {
        "title": "Who we are",
        "body": (
            f"{APP_NAME} is a personal-formation app that helps Catholics order "
            "their meals, movement, prayer, and parish life around the Church's "
            "liturgical calendar. The app is operated by an independent developer."
        ),
    },
    {
        "title": "Information we collect",
        "body": (
            "We only collect what is necessary for the features you use:\n\n"
            "• Account information — When you sign in with Google we receive your "
            "name, email address, and profile picture. We do not receive your "
            "Google password.\n\n"
            "• Faith profile — Optional fields you choose to fill in: denomination, "
            "faith background (convert / revert / cradle), and age.\n\n"
            "• Wellness data — Optional height, weight, target weight, activity "
            "level, dietary pattern, allergies, fitness level, fitness goals, and "
            "devotional focus, used to personalize meal and workout plans.\n\n"
            "• Plans & history — Generated meal, workout, and self-defense sessions, "
            "your daily-practice progress, journal entries, Bible highlights, and "
            "catechism reading state.\n\n"
            "• Community content — Posts, replies, direct messages, group "
            "memberships, friend connections, reports, and blocks you make in the "
            "Parish (community) area of the app.\n\n"
            "• Saved churches & community church edits — Churches you save for "
            "quick access, plus Mass / Confession times, websites, or phone numbers "
            "you contribute to the shared community church layer.\n\n"
            "• Parish events — Events you submit or RSVP to.\n\n"
            "• Approximate location — Only when you tap \"Use my location\" to find "
            "nearby churches. The coordinates are used in-memory to query a public "
            "map service and are not stored against your account.\n\n"
            "• Support tickets — If you use the in-app contact form, we store the "
            "subject and message text you submit so we can reply to you."
        ),
    },
    {
        "title": "How we use it",
        "body": (
            "We use the information above to provide the features of the app:\n\n"
            "• Generate AI-personalized meal, workout, and self-defense plans that "
            "honor the liturgical season, your fasts, and your goals.\n"
            "• Render your home screen, daily-practice tracker, and progress views.\n"
            "• Power the Parish feed, direct messages, group chats, friends list, "
            "and parish events.\n"
            "• Resolve nearby churches when you tap the location button.\n"
            "• Respond to your support requests.\n\n"
            "We do not sell your personal information, and we do not run "
            "advertising in the app."
        ),
    },
    {
        "title": "Third-party services",
        "body": (
            "To deliver the app we send limited data to the following providers:\n\n"
            "• Google Sign-In — to verify who you are at login.\n"
            "• Anthropic (Claude) — to generate plans, catechism summaries, and "
            "self-defense sessions. We send the prompt context required for the "
            "feature; we do not share your contact information.\n"
            "• Bolls.life — public Bible API for scripture readings (no user data "
            "is sent).\n"
            "• Universalis — public liturgical calendar API (no user data is sent).\n"
            "• OpenStreetMap / Overpass — public map data used for nearby-church "
            "searches (only the coordinate you provided is sent).\n"
            "• YouTube — embedded reflections in the Sanctuary section.\n\n"
            "Each provider has its own privacy policy."
        ),
    },
    {
        "title": "How we store and protect it",
        "body": (
            "Your data is stored in a MongoDB database hosted in a secured cloud "
            "environment, accessed only over encrypted connections. Authentication "
            "is handled by short-lived session tokens. We follow reasonable "
            "industry-standard precautions, but no system is perfectly secure."
        ),
    },
    {
        "title": "Your choices",
        "body": (
            "• You can edit or clear your name, profile picture, and faith profile "
            "any time from Profile → Edit.\n"
            "• You can delete any post, reply, message, saved church, parish "
            "event, or community church edit you've authored.\n"
            "• You can leave any group conversation, unfriend any user, and block "
            "users from the Parish tab.\n"
            "• To delete your account entirely — including all of your generated "
            "plans, community content, and saved data — open Profile → "
            "\"Delete my account\" and confirm. Deletion is immediate. You may "
            f"also email {SUPPORT_EMAIL} and we will remove your record within 30 days."
        ),
    },
    {
        "title": "Children",
        "body": (
            f"{APP_NAME} is intended for users aged 13 and older. If you believe a "
            "child under 13 has provided personal information, please contact us "
            "so we can remove it."
        ),
    },
    {
        "title": "Changes to this policy",
        "body": (
            "We may update this policy as the app evolves. The 'Last updated' date "
            "at the top of this page will reflect when changes take effect. "
            "Material changes will be surfaced inside the app."
        ),
    },
    {
        "title": "Contact",
        "body": (
            "Privacy or data-deletion questions can be sent to "
            f"{SUPPORT_EMAIL}. We aim to respond within 48 hours."
        ),
    },
]

SUPPORT_FAQ = [
    {
        "q": "How do I sign in?",
        "a": (
            "Sanctus uses Google Sign-In. Tap \"Continue with Google\" on the "
            "welcome screen. We only receive your name, email, and profile picture."
        ),
    },
    {
        "q": "How do I delete my account or my data?",
        "a": (
            f"Email {SUPPORT_EMAIL} from the address you used to sign in and we "
            "will remove your record within 30 days. You can also delete most "
            "content (posts, messages, saved churches, parish events) directly "
            "in the app."
        ),
    },
    {
        "q": "A church's Mass time is wrong — can I fix it?",
        "a": (
            "Yes. Open the church from the Churches tab, tap \"Edit,\" and submit "
            "your correction. Approved edits become a community overlay visible to "
            "everyone."
        ),
    },
    {
        "q": "I added a church that doesn't show up on the map.",
        "a": (
            "Manually-added churches are saved to the shared community list rather "
            "than the public map. They appear in the Community Churches list and "
            "to people who save them."
        ),
    },
    {
        "q": "How do I report a post, message, or user?",
        "a": (
            "Tap the three-dot menu on the content (or open the user's profile) "
            "and choose Report. Pick a reason and add detail if needed — every "
            "report is reviewed."
        ),
    },
    {
        "q": "Why does a self-defense plan ask for equipment I don't have?",
        "a": (
            "Tell the generator what you actually have (or leave \"No equipment\"). "
            "The AI will adapt drills to what you own. You can also toggle "
            "\"Solo / no partner\" for the kendo-style disciplines."
        ),
    },
    {
        "q": "Can I export my data?",
        "a": (
            f"Not yet directly in the app. Email {SUPPORT_EMAIL} and we will send "
            "you a JSON export within 7 days."
        ),
    },
]

# ----------------------------------------------------------------------------
# HTML rendering — small, dependency-free template.
# ----------------------------------------------------------------------------


def _html_shell(title: str, inner_html: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} · {APP_NAME}</title>
  <style>
    :root {{
      --bg: #F6F1E1;
      --surface: #FBF7EA;
      --primary: #2E2A21;
      --gold: #B68A2A;
      --text: #2A241B;
      --muted: #6A604B;
      --border: rgba(46, 42, 33, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: 'Lora', Georgia, 'Times New Roman', serif;
      line-height: 1.6;
      padding: 24px 16px 64px;
    }}
    .wrap {{
      max-width: 720px;
      margin: 0 auto;
    }}
    header {{
      text-align: center;
      padding: 32px 0 24px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 24px;
    }}
    .brand {{
      font-family: 'Cormorant Garamond', 'Playfair Display', Georgia, serif;
      font-size: 14px;
      letter-spacing: 4px;
      color: var(--gold);
      text-transform: uppercase;
    }}
    h1 {{
      font-family: 'Cormorant Garamond', 'Playfair Display', Georgia, serif;
      font-size: 32px;
      margin: 8px 0 4px;
      color: var(--primary);
    }}
    .updated {{
      font-size: 12px;
      color: var(--muted);
      font-style: italic;
    }}
    h2 {{
      font-family: 'Cormorant Garamond', 'Playfair Display', Georgia, serif;
      font-size: 22px;
      margin-top: 32px;
      margin-bottom: 8px;
      color: var(--primary);
    }}
    p, li {{
      font-size: 16px;
      color: var(--text);
    }}
    p {{
      white-space: pre-wrap;
    }}
    a {{
      color: var(--gold);
      text-decoration: none;
      border-bottom: 1px solid rgba(182, 138, 42, 0.4);
    }}
    a:hover {{
      border-bottom-color: var(--gold);
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px 20px;
      margin-bottom: 16px;
    }}
    .faq-q {{
      font-weight: 600;
      color: var(--primary);
      margin: 0 0 6px;
    }}
    .faq-a {{
      margin: 0;
      color: var(--text);
    }}
    .email-btn {{
      display: inline-block;
      margin-top: 8px;
      padding: 10px 18px;
      border-radius: 999px;
      background: var(--primary);
      color: var(--gold) !important;
      border-bottom: none;
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 14px;
      letter-spacing: 0.4px;
    }}
    footer {{
      margin-top: 48px;
      padding-top: 24px;
      border-top: 1px solid var(--border);
      text-align: center;
      font-size: 12px;
      color: var(--muted);
      font-style: italic;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="brand">SANCTUS</div>
      <h1>{title}</h1>
      <div class="updated">Last updated {LAST_UPDATED}</div>
    </header>
    {inner_html}
    <footer>
      Ad maiorem Dei gloriam — for the greater glory of God.<br>
      <a href="/api/legal/privacy">Privacy Policy</a> · <a href="/api/legal/support">Support</a>
    </footer>
  </div>
</body>
</html>
"""


def _render_privacy_html() -> str:
    parts = []
    for section in PRIVACY_POLICY_SECTIONS:
        # Escape angle brackets defensively (none today, but cheap insurance).
        body_html = (
            section["body"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        # Linkify the support email.
        body_html = body_html.replace(
            SUPPORT_EMAIL,
            f'<a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a>',
        )
        parts.append(f"<h2>{section['title']}</h2><p>{body_html}</p>")
    return _html_shell("Privacy Policy", "\n".join(parts))


def _render_support_html() -> str:
    faq_html = "\n".join(
        f"<div class=\"card\"><p class=\"faq-q\">{item['q']}</p>"
        f"<p class=\"faq-a\">{item['a']}</p></div>"
        for item in SUPPORT_FAQ
    )
    inner = f"""
    <h2>Get in touch</h2>
    <p>
      We're a small project and we genuinely read every message. The quickest
      way to reach us is email — usually a response within 48 hours.
    </p>
    <p>
      <a class="email-btn" href="mailto:{SUPPORT_EMAIL}?subject=Sanctus%20support">
        Email {SUPPORT_EMAIL}
      </a>
    </p>
    <p>
      Already signed in? You can also open the app and tap
      <em>Profile → Help &amp; Support</em> to send a message without leaving
      Sanctus.
    </p>

    <h2>Frequently asked</h2>
    {faq_html}

    <h2>Report abuse</h2>
    <p>
      Inside the app, tap the three-dot menu on any post, reply, message, or
      profile and choose <em>Report</em>. For urgent safety concerns email
      <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a> with the word
      <strong>URGENT</strong> in the subject line.
    </p>
    """
    return _html_shell("Help & Support", inner)


# ----------------------------------------------------------------------------
# Pydantic models for the contact-form endpoint.
# ----------------------------------------------------------------------------


class SupportContactRequest(BaseModel):
    subject: str = Field(min_length=2, max_length=140)
    message: str = Field(min_length=4, max_length=4000)
    email: Optional[EmailStr] = None  # Optional override for unauthenticated submitters
    # Free-form category from the in-app picker (bug | account | suggestion | other).
    category: Optional[str] = Field(default=None, max_length=40)


# ----------------------------------------------------------------------------
# Router builder
# ----------------------------------------------------------------------------


def build_legal_router(db, resolve_session_user: Callable) -> APIRouter:
    """Builds the /legal/* router.

    `resolve_session_user(authorization_header)` is an async callable that
    returns the current user's `(user_id, name, email)` tuple — OR None for
    anonymous callers. This is used so the contact-form endpoint works for
    anonymous visitors too (e.g. from a desktop browser link).
    """

    router = APIRouter(prefix="/legal", tags=["legal"])

    @router.get("/privacy", response_class=HTMLResponse)
    async def privacy_html() -> HTMLResponse:
        return HTMLResponse(_render_privacy_html())

    @router.get("/privacy.json")
    async def privacy_json() -> Dict[str, Any]:
        return {
            "app": APP_NAME,
            "last_updated": LAST_UPDATED,
            "support_email": SUPPORT_EMAIL,
            "sections": PRIVACY_POLICY_SECTIONS,
        }

    @router.get("/support", response_class=HTMLResponse)
    async def support_html() -> HTMLResponse:
        return HTMLResponse(_render_support_html())

    @router.get("/support.json")
    async def support_json() -> Dict[str, Any]:
        return {
            "app": APP_NAME,
            "last_updated": LAST_UPDATED,
            "support_email": SUPPORT_EMAIL,
            "faq": SUPPORT_FAQ,
        }

    @router.post("/support/contact")
    async def support_contact(
        payload: SupportContactRequest,
        request: Request,
    ) -> JSONResponse:
        # Try to attach an authenticated user if a bearer token is present.
        user = None
        try:
            user = await resolve_session_user(request.headers.get("authorization"))
        except Exception:  # noqa: BLE001
            user = None

        ticket_id = f"sup_{uuid.uuid4().hex[:14]}"
        now = datetime.now(timezone.utc)
        doc = {
            "ticket_id": ticket_id,
            "subject": payload.subject.strip(),
            "message": payload.message.strip(),
            "category": (payload.category or "other").strip().lower(),
            "submitter_email": (
                (payload.email and str(payload.email))
                or getattr(user, "email", None)
                or None
            ),
            "submitter_name": getattr(user, "name", None),
            "submitter_user_id": getattr(user, "user_id", None),
            "status": "open",
            "created_at": now,
            "user_agent": request.headers.get("user-agent"),
        }
        await db.support_tickets.insert_one(doc)
        log.info(
            "Support ticket %s from %s — %s",
            ticket_id,
            doc["submitter_email"] or "anonymous",
            payload.subject[:60],
        )
        return JSONResponse(
            {
                "ok": True,
                "ticket_id": ticket_id,
                "message": (
                    "Thanks — we received your message. We'll reply to "
                    + (doc["submitter_email"] or "your email")
                    + " within 48 hours."
                ),
            }
        )

    return router
