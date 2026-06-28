"""One-time(ish) bulk ingest of real Catholic churches from OpenStreetMap.

Sweeps a list of bounding boxes over the world's Catholic-dense metros and
upserts every Catholic place-of-worship it finds into the `osm_churches`
collection. Safe to re-run — documents are upserted by OSM id, so the count
only grows toward "every church".

Run in the background:
    cd /app/backend && python3 ingest_osm_churches.py >/tmp/ingest.log 2>&1 &
Then poll progress:
    db.osm_churches.count_documents({})
"""
from __future__ import annotations

import asyncio
import os
import time

import httpx
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

OVERPASS = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

# Half-size of each query box in degrees (~0.35° ≈ 35-40 km half-width).
HALF = 0.35

# Catholic-dense metros / regions across every continent. (name, lat, lng)
CITIES = [
    # --- Italy (extremely dense) ---
    ("Rome", 41.90, 12.50), ("Milan", 45.46, 9.19), ("Naples", 40.85, 14.27),
    ("Turin", 45.07, 7.69), ("Palermo", 38.12, 13.36), ("Florence", 43.77, 11.26),
    ("Bologna", 44.49, 11.34), ("Venice", 45.44, 12.32), ("Bari", 41.12, 16.87),
    ("Catania", 37.50, 15.09), ("Genoa", 44.41, 8.93), ("Verona", 45.44, 10.99),
    # --- Spain ---
    ("Madrid", 40.42, -3.70), ("Barcelona", 41.39, 2.17), ("Seville", 37.39, -5.99),
    ("Valencia", 39.47, -0.38), ("Zaragoza", 41.65, -0.88), ("Malaga", 36.72, -4.42),
    ("Toledo", 39.86, -4.03), ("Santiago de Compostela", 42.88, -8.54),
    ("Granada", 37.18, -3.60), ("Bilbao", 43.26, -2.93),
    # --- Portugal ---
    ("Lisbon", 38.72, -9.14), ("Porto", 41.15, -8.61), ("Braga", 41.55, -8.43),
    ("Fatima", 39.63, -8.67),
    # --- France ---
    ("Paris", 48.86, 2.35), ("Lyon", 45.76, 4.84), ("Marseille", 43.30, 5.37),
    ("Toulouse", 43.60, 1.44), ("Lille", 50.63, 3.06), ("Bordeaux", 44.84, -0.58),
    ("Strasbourg", 48.58, 7.75), ("Nantes", 47.22, -1.55), ("Lourdes", 43.10, -0.05),
    # --- Poland ---
    ("Warsaw", 52.23, 21.01), ("Krakow", 50.06, 19.94), ("Lodz", 51.76, 19.46),
    ("Wroclaw", 51.11, 17.04), ("Poznan", 52.41, 16.93), ("Czestochowa", 50.81, 19.12),
    ("Gdansk", 54.35, 18.65),
    # --- Ireland / UK ---
    ("Dublin", 53.35, -6.26), ("Cork", 51.90, -8.47), ("Galway", 53.27, -9.05),
    ("London", 51.51, -0.13), ("Liverpool", 53.41, -2.99), ("Glasgow", 55.86, -4.25),
    ("Birmingham", 52.49, -1.89),
    # --- Germany / Austria / Switzerland / Benelux ---
    ("Cologne", 50.94, 6.96), ("Munich", 48.14, 11.58), ("Berlin", 52.52, 13.40),
    ("Frankfurt", 50.11, 8.68), ("Vienna", 48.21, 16.37), ("Salzburg", 47.81, 13.04),
    ("Zurich", 47.38, 8.54), ("Brussels", 50.85, 4.35), ("Amsterdam", 52.37, 4.90),
    ("Munster", 51.96, 7.63),
    # --- Rest of Europe ---
    ("Prague", 50.08, 14.44), ("Budapest", 47.50, 19.04), ("Zagreb", 45.81, 15.98),
    ("Bratislava", 48.15, 17.11), ("Ljubljana", 46.06, 14.51), ("Vilnius", 54.69, 25.28),
    ("Valletta", 35.90, 14.51), ("Bucharest", 44.43, 26.10),
    # --- Mexico (huge) ---
    ("Mexico City", 19.43, -99.13), ("Guadalajara", 20.67, -103.35), ("Puebla", 19.04, -98.21),
    ("Monterrey", 25.69, -100.32), ("Leon", 21.12, -101.68), ("Morelia", 19.70, -101.19),
    ("Oaxaca", 17.07, -96.72), ("Merida", 20.97, -89.62),
    # --- Central America / Caribbean ---
    ("Guatemala City", 14.63, -90.51), ("San Salvador", 13.69, -89.22),
    ("Tegucigalpa", 14.07, -87.19), ("Managua", 12.13, -86.25), ("San Jose CR", 9.93, -84.08),
    ("Panama City", 8.98, -79.52), ("Havana", 23.11, -82.37), ("Santo Domingo", 18.49, -69.93),
    ("San Juan PR", 18.47, -66.10),
    # --- South America (huge) ---
    ("Bogota", 4.71, -74.07), ("Medellin", 6.24, -75.58), ("Cali", 3.45, -76.53),
    ("Lima", -12.05, -77.04), ("Quito", -0.18, -78.47), ("Caracas", 10.49, -66.88),
    ("Sao Paulo", -23.55, -46.63), ("Rio de Janeiro", -22.91, -43.20),
    ("Belo Horizonte", -19.92, -43.94), ("Salvador BA", -12.97, -38.50),
    ("Buenos Aires", -34.60, -58.38), ("Cordoba AR", -31.42, -64.18),
    ("Santiago CL", -33.45, -70.67), ("Asuncion", -25.30, -57.64),
    ("La Paz", -16.50, -68.15), ("Montevideo", -34.90, -56.16),
    # --- United States / Canada ---
    ("New York", 40.71, -74.01), ("Boston", 42.36, -71.06), ("Philadelphia", 39.95, -75.17),
    ("Chicago", 41.88, -87.63), ("Los Angeles", 34.05, -118.24), ("San Antonio", 29.42, -98.49),
    ("New Orleans", 29.95, -90.07), ("Miami", 25.76, -80.19), ("Washington DC", 38.90, -77.04),
    ("Detroit", 42.33, -83.05), ("St. Louis", 38.63, -90.20), ("San Francisco", 37.77, -122.42),
    ("Montreal", 45.50, -73.57), ("Quebec City", 46.81, -71.21), ("Toronto", 43.65, -79.38),
    # --- Philippines (very dense) ---
    ("Manila", 14.60, 120.98), ("Cebu", 10.32, 123.89), ("Davao", 7.07, 125.61),
    ("Iloilo", 10.72, 122.56), ("Vigan", 17.57, 120.39),
    # --- Africa ---
    ("Kinshasa", -4.32, 15.31), ("Lagos", 6.45, 3.39), ("Nairobi", -1.29, 36.82),
    ("Kampala", 0.31, 32.58), ("Luanda", -8.84, 13.23), ("Abidjan", 5.36, -4.01),
    ("Yaounde", 3.85, 11.50), ("Accra", 5.55, -0.20), ("Cape Town", -33.93, 18.42),
    ("Antananarivo", -18.92, 47.53),
    # --- Asia / Oceania ---
    ("Goa", 15.50, 73.91), ("Bangalore", 12.97, 77.59), ("Mumbai", 19.08, 72.88),
    ("Chennai", 13.08, 80.27), ("Kerala (Kochi)", 9.93, 76.27), ("Seoul", 37.56, 126.97),
    ("Ho Chi Minh City", 10.82, 106.63), ("Hanoi", 21.03, 105.85), ("Jakarta", -6.21, 106.85),
    ("Sydney", -33.87, 151.21), ("Melbourne", -37.81, 144.96), ("Auckland", -36.85, 174.76),
    ("Dili", -8.56, 125.56),
]


def query(s: float, w: float, n: float, e: float) -> str:
    return (
        "[out:json][timeout:60];"
        "("
        f'node["amenity"="place_of_worship"]["religion"="christian"]["denomination"~"catholic",i]({s},{w},{n},{e});'
        f'way["amenity"="place_of_worship"]["religion"="christian"]["denomination"~"catholic",i]({s},{w},{n},{e});'
        ");"
        "out center 2000;"
    )


# Country-wide sweep — catches rural/village churches the metro boxes miss, so
# we approach "every running Catholic church". ISO-3166-1 alpha-2 codes.
COUNTRIES = [
    # --- Europe ---
    "VA", "SM", "MT", "AD", "MC", "LI", "IE", "GB", "PT", "ES", "FR", "IT",
    "BE", "NL", "LU", "DE", "AT", "CH", "PL", "CZ", "SK", "HU", "SI", "HR",
    "BA", "RS", "ME", "MK", "AL", "XK", "GR", "BG", "RO", "MD", "UA", "BY",
    "LT", "LV", "EE", "FI", "SE", "NO", "DK", "IS", "RU", "CY", "TR", "GE",
    "AM", "AZ",
    # --- Americas ---
    "US", "CA", "MX", "GT", "BZ", "SV", "HN", "NI", "CR", "PA", "CU", "DO",
    "HT", "PR", "JM", "TT", "BS", "BB", "GD", "LC", "VC", "DM", "AG", "KN",
    "CO", "VE", "GY", "SR", "EC", "PE", "BO", "BR", "PY", "UY", "AR", "CL",
    # --- Africa ---
    "MA", "DZ", "TN", "LY", "EG", "SD", "SS", "ER", "ET", "DJ", "SO", "KE",
    "UG", "RW", "BI", "TZ", "MZ", "MW", "ZM", "ZW", "AO", "CD", "CG", "GA",
    "GQ", "CM", "CF", "TD", "NE", "NG", "BJ", "TG", "GH", "CI", "BF", "ML",
    "MR", "SN", "GM", "GW", "GN", "SL", "LR", "ST", "ZA", "NA", "BW", "LS",
    "SZ", "MG", "MU", "SC", "KM", "CV",
    # --- Middle East ---
    "LB", "IL", "PS", "JO", "SY", "IQ", "IR", "SA", "YE", "OM", "AE", "QA",
    "BH", "KW",
    # --- Asia ---
    "IN", "PK", "BD", "LK", "NP", "BT", "MV", "MM", "TH", "LA", "KH", "VN",
    "MY", "SG", "BN", "ID", "TL", "PH", "CN", "HK", "MO", "TW", "JP", "KR",
    "MN", "KZ", "KG", "TJ", "TM", "UZ",
    # --- Oceania ---
    "AU", "NZ", "PG", "FJ", "SB", "VU", "NC", "PF", "WS", "TO", "KI", "FM",
    "MH", "PW", "GU",
]


def area_query(iso: str) -> str:
    return (
        "[out:json][timeout:600];"
        f'area["ISO3166-1"="{iso}"][admin_level=2]->.a;'
        "("
        'node["amenity"="place_of_worship"]["religion"="christian"]["denomination"~"catholic",i](area.a);'
        'way["amenity"="place_of_worship"]["religion"="christian"]["denomination"~"catholic",i](area.a);'
        ");"
        "out center;"
    )


async def fetch_q(client: httpx.AsyncClient, q: str):
    for attempt in range(5):
        for url in OVERPASS:
            try:
                r = await client.post(url, data={"data": q},
                                      headers={"User-Agent": "SanctusApp/1.0 (church ingest)"})
                if r.status_code == 200:
                    return r.json().get("elements", [])
                if r.status_code in (429, 504):
                    break
            except Exception as ex:  # noqa: BLE001
                print("  err", repr(ex)[:70])
        await asyncio.sleep(10 * (attempt + 1))
    return None


async def fetch_area(client: httpx.AsyncClient, iso: str):
    """Country-wide sweep (slow). Uses a generous timeout for big nations."""
    q = area_query(iso)
    for attempt in range(4):
        for url in OVERPASS:
            try:
                r = await client.post(url, data={"data": q},
                                      headers={"User-Agent": "SanctusApp/1.0 (church ingest)"})
                if r.status_code == 200:
                    return r.json().get("elements", [])
                if r.status_code in (429, 504):
                    break
            except Exception as ex:  # noqa: BLE001
                print("  err", repr(ex)[:70])
        await asyncio.sleep(20 * (attempt + 1))  # heavier backoff for big queries
    return None


async def fetch_box(client: httpx.AsyncClient, s, w, n, e):
    q = query(s, w, n, e)
    for attempt in range(5):
        for url in OVERPASS:
            try:
                r = await client.post(url, data={"data": q},
                                      headers={"User-Agent": "SanctusApp/1.0 (church ingest)"})
                if r.status_code == 200:
                    return r.json().get("elements", [])
                if r.status_code in (429, 504):
                    break  # rate limited — back off below
            except Exception as ex:  # noqa: BLE001
                print("  err", repr(ex)[:70])
        await asyncio.sleep(8 * (attempt + 1))  # 8,16,24,32s backoff
    return None


def parse(elements):
    out = []
    for el in elements:
        tags = el.get("tags") or {}
        name = (tags.get("name") or "").strip()
        if not name:
            continue
        if el.get("type") == "node":
            lat, lng = el.get("lat"), el.get("lon")
        else:
            c = el.get("center") or {}
            lat, lng = c.get("lat"), c.get("lon")
        if lat is None or lng is None:
            continue
        # Build a human-readable address from OSM addr:* tags.
        house = (tags.get("addr:housenumber") or "").strip()
        street = (tags.get("addr:street") or "").strip()
        city = (tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:village") or "").strip()
        state = (tags.get("addr:state") or tags.get("addr:province") or "").strip()
        postcode = (tags.get("addr:postcode") or "").strip()
        country = (tags.get("addr:country") or "").strip()
        line1 = " ".join(p for p in [house, street] if p).strip()
        address = ", ".join(p for p in [line1, city, state, postcode, country] if p)
        out.append({
            "osm_id": f"{el.get('type','n')[0]}{el.get('id')}",
            "name": name, "type": "church",
            "city": city, "country": country,
            "street": line1, "state": state, "postcode": postcode,
            "address": address,
            "website": (tags.get("website") or tags.get("contact:website") or "").strip(),
            "phone": (tags.get("phone") or tags.get("contact:phone") or "").strip(),
            "lat": lat, "lng": lng, "osm": True,
        })
    return out


async def main():
    import random
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    col = db["osm_churches"]
    await col.create_index("osm_id", unique=True)
    await col.create_index([("lat", 1), ("lng", 1)])

    start_total = await col.count_documents({})
    print(f"START: {start_total} churches already stored.")

    # The metro city sweep is redundant once the whole-country sweep runs
    # (countries include their metros). Enable only with RUN_CITIES=1.
    if os.environ.get("RUN_CITIES") == "1":
        cities = CITIES[:]
        random.shuffle(cities)
        print(f"Sweeping {len(cities)} metros...")
        async with httpx.AsyncClient(timeout=50) as client:
            for i, (name, lat, lng) in enumerate(cities, 1):
                els = await fetch_box(client, lat - HALF, lng - HALF, lat + HALF, lng + HALF)
                if els is None:
                    print(f"[{i}/{len(cities)}] {name}: FAILED")
                    await asyncio.sleep(2)
                    continue
                for d in parse(els):
                    await col.update_one({"osm_id": d["osm_id"]}, {"$set": d}, upsert=True)
                await asyncio.sleep(1.0)

    # --- Country-wide sweep (resumable + continuous): pass after pass, skip
    # ISO codes already completed and re-attempt failures, until every nation
    # in COUNTRIES is covered. Progress persists in Mongo so a restart resumes
    # instead of starting over. ---
    prog = db["osm_ingest_progress"]
    state = await prog.find_one({"_id": "country_sweep"}) or {}
    done = set(state.get("done", []))
    remaining = [iso for iso in COUNTRIES if iso not in done]
    print(f"=== COUNTRY SWEEP: {len(remaining)} of {len(COUNTRIES)} nations remaining "
          f"({len(done)} already done) ===")

    MAX_PASSES = 12
    pass_no = 0
    async with httpx.AsyncClient(timeout=660) as cclient:
        while remaining and pass_no < MAX_PASSES:
            pass_no += 1
            still = []
            for idx, iso in enumerate(remaining, 1):
                t0 = time.time()
                els = await fetch_area(cclient, iso)
                if els is None:
                    print(f"[pass {pass_no}] {iso} ({idx}/{len(remaining)}): FAILED — will retry")
                    still.append(iso)
                    await asyncio.sleep(5)
                    continue
                new = 0
                for d in parse(els):
                    res = await col.update_one({"osm_id": d["osm_id"]}, {"$set": d}, upsert=True)
                    if res.upserted_id is not None:
                        new += 1
                done.add(iso)
                await prog.update_one(
                    {"_id": "country_sweep"},
                    {"$set": {"done": sorted(done), "updated_at": time.time()}},
                    upsert=True,
                )
                total = await col.count_documents({})
                print(f"[pass {pass_no}] {iso} ({idx}/{len(remaining)}): +{new} new | total={total} | {time.time()-t0:.1f}s")
                await asyncio.sleep(3)
            remaining = still
            if remaining:
                print(f"--- pass {pass_no} done; {len(remaining)} still failing: {remaining}. Cooling 60s ---")
                await asyncio.sleep(60)

    total = await col.count_documents({})
    if remaining:
        print(f"STOPPED after {pass_no} passes. Still unreachable: {remaining}")
    else:
        print(f"COMPLETE — all {len(COUNTRIES)} nations swept.")
    print(f"Total stored churches: {total} (added {total - start_total} this run).")


if __name__ == "__main__":
    asyncio.run(main())
