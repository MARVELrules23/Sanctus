"""One-off generator for children's book covers + Catholic coloring line-art.

Run:  python gen_family_assets.py
Idempotent: skips covers already set and coloring pages already present.
Uses the Emergent universal key with Gemini "Nano Banana" image model.
"""
import asyncio
import base64
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv()
API_KEY = os.getenv("EMERGENT_LLM_KEY")
MODEL = "gemini-3.1-flash-image-preview"

COVERS = {
    "bible-stories-for-little-souls": "A warm, gentle children's storybook cover illustration for a Catholic Bible story book. Soft watercolor style, glowing light, a friendly Noah's ark with animals, a rainbow, a starry sky, and a small shepherd boy. Bright, joyful, safe and reverent. No text, no words, no letters.",
    "little-saints-for-little-hearts": "A warm children's storybook cover illustration of friendly Catholic saints for little children: a kind saint with a halo surrounded by children, birds and flowers, soft golden light, gentle watercolor style, joyful and reverent. No text, no words, no letters.",
    "the-holy-mass-for-little-ones": "A warm children's storybook cover illustration of the Catholic Mass for little children: a bright church interior with a golden chalice and host on the altar, stained-glass light, a child kneeling, angels, soft watercolor style, reverent and joyful. No text, no words, no letters.",
}

COLORING = [
    ("cross", "Simple Cross", "Black and white line-art coloring page for young children of a plain Christian cross with a few decorative flowers at the base. Thick clean black outlines, pure white background, no shading, no grey, no color, large simple shapes easy to color. Coloring book style."),
    ("chalice-host", "Chalice & Host", "Black and white line-art coloring page for young children of a Catholic chalice with a round host above it radiating simple rays of light. Thick clean black outlines, pure white background, no shading, no color, large simple shapes. Coloring book style."),
    ("nativity", "The Nativity", "Black and white line-art coloring page for young children of the Nativity: baby Jesus in a manger with Mary and Joseph, a star above, simple friendly shapes. Thick clean black outlines, pure white background, no shading, no color. Coloring book style."),
    ("guardian-angel", "Guardian Angel", "Black and white line-art coloring page for young children of a kind guardian angel with big wings watching over a small child. Thick clean black outlines, pure white background, no shading, no color, large simple shapes. Coloring book style."),
    ("holy-spirit-dove", "The Holy Spirit Dove", "Black and white line-art coloring page for young children of a peaceful dove descending with simple rays of light around it. Thick clean black outlines, pure white background, no shading, no color, large simple shapes. Coloring book style."),
    ("sacred-heart", "The Sacred Heart", "Black and white line-art coloring page for young children of the Sacred Heart of Jesus: a simple heart with a small cross and flames on top and a ring of thorns. Thick clean black outlines, pure white background, no shading, no color, large simple shapes. Coloring book style."),
]


async def _gen(prompt: str) -> str | None:
    chat = LlmChat(api_key=API_KEY, session_id=f"asset-{os.urandom(4).hex()}", system_message="You generate images.")
    chat.with_model("gemini", MODEL).with_params(modalities=["image", "text"])
    _, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
    if images:
        img = images[0]
        return f"data:{img['mime_type']};base64,{img['data']}"
    return None


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

    # Book covers
    for slug, prompt in COVERS.items():
        doc = await db.library_books.find_one({"slug": slug}, {"_id": 1, "cover_image": 1})
        if doc is None:
            print("missing book", slug); continue
        if doc.get("cover_image"):
            print("cover exists", slug); continue
        data = await _gen(prompt)
        if data:
            await db.library_books.update_one({"slug": slug}, {"$set": {"cover_image": data}})
            print("cover set", slug, "len", len(data))
        else:
            print("cover FAILED", slug)

    # Coloring pages
    for order, (slug, title, prompt) in enumerate(COLORING):
        if await db.coloring_pages.find_one({"slug": slug}, {"_id": 1}):
            print("coloring exists", slug); continue
        data = await _gen(prompt)
        if data:
            await db.coloring_pages.update_one(
                {"slug": slug},
                {"$set": {"slug": slug, "title": title, "order": order, "image": data}},
                upsert=True,
            )
            print("coloring set", slug, "len", len(data))
        else:
            print("coloring FAILED", slug)


if __name__ == "__main__":
    asyncio.run(main())
