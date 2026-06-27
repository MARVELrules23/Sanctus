"""Sanctuary — calming spaces (Study / Meditation) within the app.

Currently exposes a lazily-generated, permanently-cached lo-fi illustration of
St. Joseph at his carpenter's bench, used as the animated backdrop of the
"St. Joseph's Workshop" study mode. Generation + caching reuse the same helper
as the companion saints (Gemini Nano Banana, cached in `companion_images`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from companions import _get_or_make_image

WORKSHOP_SLUG = "sanctuary-joseph-workshop"
WORKSHOP_PROMPT = (
    "Saint Joseph the carpenter working quietly at his wooden workbench in a cozy "
    "candle-lit Nazareth workshop at dusk, gently planing a plank of wood with curling "
    "wood shavings, hand tools and sawdust on the bench, the young Christ Child sitting "
    "nearby watching with wonder, warm amber and ochre lighting, soft golden halo, "
    "lo-fi study anime aesthetic, dreamy muted pastel colours, gentle film grain, "
    "calm contemplative cozy atmosphere, soft glow, no text, no words"
)


def build_router(db: AsyncIOMotorDatabase, get_current_user, emergent_llm_key: str = "") -> APIRouter:
    router = APIRouter(prefix="/sanctuary", tags=["sanctuary"])

    @router.get("/study-image")
    async def study_image(user=Depends(get_current_user)):
        data_url = await _get_or_make_image(db, WORKSHOP_SLUG, WORKSHOP_PROMPT, emergent_llm_key)
        return {"image": data_url}

    return router
