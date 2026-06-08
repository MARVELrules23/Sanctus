"""Nearby Catholic churches via OpenStreetMap Overpass API.

We query Overpass for `amenity=place_of_worship` features with
`religion=christian` and `denomination=catholic` (also `roman_catholic`,
`greek_catholic`, etc.) within a radius of a given lat/lng.

We never store user GPS. The caller resolves nearby churches each time and
persists only church IDs they choose to star.

We also expose a best-effort masstimes.org lookup for Mass / confession
schedules — frequently 403s or returns no data, so the frontend should treat
those fields as informational only and the user can override / fill them.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("sanctus.churches")

OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
)

USER_AGENT = "SanctusApp/1.0 (Catholic devotional app)"

CATHOLIC_DENOMS = {
    "catholic",
    "roman_catholic",
    "greek_catholic",
    "ukrainian_catholic",
    "melkite_catholic",
    "maronite",
    "chaldean_catholic",
    "syro_malabar",
    "syro_malankara",
    "old_catholic",  # arguable but commonly searched
}


def _haversine_km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    r = 6371.0
    p1 = math.radians(a_lat)
    p2 = math.radians(b_lat)
    dp = math.radians(b_lat - a_lat)
    dl = math.radians(b_lng - a_lng)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _church_id(element: dict) -> str:
    osm_type = element.get("type", "node")
    osm_id = element.get("id")
    if osm_id is not None:
        return f"osm:{osm_type}/{osm_id}"
    # Fallback: hash by name + coords if Overpass returned a malformed node.
    tags = element.get("tags", {}) or {}
    seed = f"{tags.get('name','')}-{element.get('lat')},{element.get('lon')}"
    return f"osm:hash/{hashlib.sha1(seed.encode()).hexdigest()[:10]}"


def _coords(element: dict) -> tuple[Optional[float], Optional[float]]:
    if "lat" in element and "lon" in element:
        return element["lat"], element["lon"]
    center = element.get("center") or {}
    return center.get("lat"), center.get("lon")


def _format_address(tags: dict) -> str:
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:city"),
        tags.get("addr:state"),
        tags.get("addr:postcode"),
    ]
    parts = [p for p in parts if p]
    return ", ".join(parts)


def _is_catholic(tags: dict) -> bool:
    denom = (tags.get("denomination") or "").lower().strip()
    if any(d in denom for d in CATHOLIC_DENOMS):
        return True
    religion = (tags.get("religion") or "").lower().strip()
    if religion == "catholic":
        return True
    # name heuristic for nodes that lack denomination tag.
    name = (tags.get("name") or "").lower()
    if religion == "christian" and any(
        kw in name
        for kw in ("catholic", "st. ", "st ", "saint ", "basilica", "cathedral", "our lady")
    ):
        return True
    return False


def _to_church_dict(element: dict, origin: tuple[float, float]) -> Optional[dict]:
    tags = element.get("tags", {}) or {}
    if not _is_catholic(tags):
        return None
    lat, lng = _coords(element)
    if lat is None or lng is None:
        return None
    name = (tags.get("name") or "Unnamed Catholic church").strip()
    dist = round(_haversine_km(origin[0], origin[1], lat, lng), 2)
    return {
        "church_id": _church_id(element),
        "name": name,
        "lat": lat,
        "lng": lng,
        "distance_km": dist,
        "address": _format_address(tags),
        "denomination": tags.get("denomination", ""),
        "website": tags.get("website", "") or tags.get("contact:website", ""),
        "phone": tags.get("phone", "") or tags.get("contact:phone", ""),
        "mass_times_raw": tags.get("service_times", ""),
        "opening_hours": tags.get("opening_hours", ""),
    }


async def nearby_churches(
    lat: float, lng: float, radius_m: int = 8000, limit: int = 30
) -> list[dict]:
    """Find Catholic churches near (lat,lng) within `radius_m` meters."""
    radius_m = max(500, min(int(radius_m), 50_000))
    query = (
        "[out:json][timeout:18];"
        "("
        f'  node["amenity"="place_of_worship"]["religion"~"christian",i](around:{radius_m},{lat},{lng});'
        f'  way["amenity"="place_of_worship"]["religion"~"christian",i](around:{radius_m},{lat},{lng});'
        f'  relation["amenity"="place_of_worship"]["religion"~"christian",i](around:{radius_m},{lat},{lng});'
        ");"
        "out center tags;"
    )

    for endpoint in OVERPASS_ENDPOINTS:
        try:
            async with httpx.AsyncClient(timeout=22.0, follow_redirects=True) as c:
                r = await c.post(
                    endpoint,
                    data={"data": query},
                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                )
            if r.status_code != 200:
                logger.warning("overpass %s -> %s", endpoint, r.status_code)
                continue
            data = r.json()
        except Exception as e:  # noqa: BLE001
            logger.warning("overpass %s failed: %s", endpoint, e)
            continue

        elements = data.get("elements") or []
        churches: list[dict] = []
        for el in elements:
            c = _to_church_dict(el, (lat, lng))
            if c:
                churches.append(c)
        churches.sort(key=lambda x: x["distance_km"])
        return churches[:limit]

    return []


async def search_churches(
    query: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_m: int = 60_000,
    limit: int = 30,
) -> list[dict]:
    """Search Catholic churches by name.

    If ``lat``/``lng`` are provided, we first search via Overpass within
    ``radius_m`` of the user (default 60km — broader than the auto-detected
    list) so the result keeps OSM tags (website, opening_hours, etc.) and we
    can compute a real distance. If Overpass returns nothing, we fall back to
    Nominatim search (OSM's geocoder) which can find places by name globally;
    those results don't have OSM tags, but we still return name + coords.
    """
    q = (query or "").strip()
    if not q:
        return []

    safe_q = re.sub(r"[^a-zA-Z0-9'\s\-\.]", " ", q).strip()
    if not safe_q:
        return []

    # PRIMARY: Nominatim text search — much faster and better at fuzzy
    # name matches. We bound it to a viewbox around the user (~165km) when
    # coords are available so we don't surface results in other states.
    async def _nominatim(q_text: str) -> list[dict]:
        try:
            p: dict[str, str] = {
                "q": q_text,
                "format": "jsonv2",
                "addressdetails": "1",
                "limit": str(limit),
            }
            if lat is not None and lng is not None:
                p["viewbox"] = f"{lng - 1.5},{lat + 1.5},{lng + 1.5},{lat - 1.5}"
                p["bounded"] = "1"
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as c:
                rr = await c.get(
                    "https://nominatim.openstreetmap.org/search",
                    params=p,
                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                )
            return rr.json() if rr.status_code == 200 else []
        except Exception as e:  # noqa: BLE001
            logger.warning("nominatim %r failed: %s", q_text, e)
            return []

    # Try two queries: first with explicit "Catholic church" prefix to bias
    # towards parishes; then a bare query in case the user typed the full
    # parish name. Merge & de-dup by osm id.
    seen_ids: set[str] = set()
    nominatim_results: list[dict] = []
    for query_text in (f"Catholic church {safe_q}", safe_q):
        for el in await _nominatim(query_text):
            key = f"{el.get('osm_type','?')}/{el.get('osm_id','?')}"
            if key in seen_ids:
                continue
            seen_ids.add(key)
            nominatim_results.append(el)
        if len(nominatim_results) >= limit:
            break

    churches: list[dict] = []
    for el in nominatim_results or []:
        try:
            r_lat = float(el.get("lat"))
            r_lng = float(el.get("lon"))
        except (TypeError, ValueError):
            continue
        # Filter to actual places of worship / Catholic-ish points of
        # interest. Exclude roads, suburbs, etc. Nominatim's "category" is the
        # OSM key (e.g. "amenity", "highway", "place") and "type" the value
        # (e.g. "place_of_worship", "residential", "suburb").
        category = (el.get("category") or "").lower()
        ntype = (el.get("type") or "").lower()
        is_pow = (
            (category == "amenity" and ntype == "place_of_worship")
            or (category == "building" and ntype in {"church", "chapel", "cathedral", "basilica"})
            or (category == "historic" and ntype in {"church", "chapel", "monastery"})
            or (category == "tourism" and ntype in {"attraction", "place_of_worship"})
        )
        if not is_pow:
            continue
        name = (el.get("name") or el.get("display_name") or "").split(",")[0].strip()
        if not name:
            continue
        # Loose Catholic filter: name keyword or category hint.
        haystack = (
            f"{name} {el.get('display_name','')} {ntype}"
        ).lower()
        if "catholic" not in haystack and not any(
            kw in haystack for kw in (
                "cathedral", "basilica", "parish", "our lady", "st.", "saint",
                "shrine", "rosary", "blessed", "assumption", "immaculate",
            )
        ):
            # Some Catholic churches don't include any of these markers in
            # the name; still accept if Nominatim returned them under the
            # explicit Catholic query path.
            if "catholic" not in (el.get("display_name") or "").lower():
                continue
        dist = None
        if lat is not None and lng is not None:
            dist = round(_haversine_km(lat, lng, r_lat, r_lng), 2)
        addr_parts = el.get("address") or {}
        address = ", ".join(
            [
                p
                for p in [
                    addr_parts.get("road"),
                    addr_parts.get("suburb"),
                    addr_parts.get("city") or addr_parts.get("town") or addr_parts.get("village"),
                    addr_parts.get("state"),
                    addr_parts.get("country"),
                ]
                if p
            ]
        )
        osm_type = el.get("osm_type") or "node"
        osm_id = el.get("osm_id") or hashlib.sha1(f"{name}{r_lat}{r_lng}".encode()).hexdigest()[:10]
        churches.append(
            {
                "church_id": f"osm:{osm_type}/{osm_id}",
                "name": name,
                "lat": r_lat,
                "lng": r_lng,
                "distance_km": dist,
                "address": address,
                "denomination": "catholic",
                "website": "",
                "phone": "",
                "mass_times_raw": "",
                "opening_hours": "",
            }
        )
    if lat is not None and lng is not None:
        churches.sort(key=lambda x: (x["distance_km"] if x["distance_km"] is not None else 1e9))
    return churches[:limit]


# ---------- best-effort masstimes.org enrichment ----------

_TIME_LINE_RE = re.compile(
    r"(mon|tue|wed|thu|fri|sat|sun|sunday|saturday|weekday|daily)\b[^\n\r\.;|]*(\d{1,2}:\d{2}\s*(?:am|pm)?)",
    re.I,
)


async def masstimes_lookup(name: str, lat: float, lng: float) -> Optional[dict]:
    """Try to scrape masstimes.org for Mass + Confession times for a church.

    Returns dict with `mass_times` (list[str]) and `confession_times` (list[str])
    or None. The site frequently rate-limits or returns no result — failures are
    silent and the caller must fall back to user-curated schedules.
    """
    if not name:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as c:
            search = await c.get(
                "https://masstimes.org/search-by-keyword",
                params={"keyword": name, "page": 1},
                headers={"User-Agent": USER_AGENT},
            )
        if search.status_code != 200:
            return None
        soup = BeautifulSoup(search.text, "html.parser")
        # First parish result
        link = soup.select_one("a.parish-result, a.list-group-item, .search-results a")
        if not link or not link.get("href"):
            return None
        href = link["href"]
        if href.startswith("/"):
            href = "https://masstimes.org" + href
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as c:
            page = await c.get(href, headers={"User-Agent": USER_AGENT})
        if page.status_code != 200:
            return None
        page_soup = BeautifulSoup(page.text, "html.parser")
        text = page_soup.get_text("\n", strip=True)

        mass_lines = []
        confession_lines = []
        for chunk in re.split(r"\n+", text):
            low = chunk.lower()
            if "mass" in low and _TIME_LINE_RE.search(chunk):
                mass_lines.append(chunk[:120])
            if ("confession" in low or "reconciliation" in low) and _TIME_LINE_RE.search(chunk):
                confession_lines.append(chunk[:120])
        if not (mass_lines or confession_lines):
            return None
        return {
            "mass_times": list(dict.fromkeys(mass_lines))[:12],
            "confession_times": list(dict.fromkeys(confession_lines))[:6],
            "source": href,
        }
    except Exception as e:  # noqa: BLE001
        logger.debug("masstimes scrape failed: %s", e)
        return None


async def enrich_with_masstimes(churches: list[dict]) -> list[dict]:
    """Best-effort enrichment for up to the first 5 churches."""
    if not churches:
        return churches
    tasks = [
        masstimes_lookup(c["name"], c["lat"], c["lng"]) for c in churches[:5]
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for c, res in zip(churches[:5], results):
        if isinstance(res, dict):
            c["mass_times"] = res.get("mass_times", [])
            c["confession_times"] = res.get("confession_times", [])
            c["schedule_source"] = res.get("source", "")
        else:
            c.setdefault("mass_times", [])
            c.setdefault("confession_times", [])
            c.setdefault("schedule_source", "")
    for c in churches[5:]:
        c.setdefault("mass_times", [])
        c.setdefault("confession_times", [])
        c.setdefault("schedule_source", "")
    return churches
