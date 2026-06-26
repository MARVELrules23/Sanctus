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
    "https://overpass-api.de/api/interpreter",
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
        out.append({
            "osm_id": f"{el.get('type','n')[0]}{el.get('id')}",
            "name": name, "type": "church",
            "city": tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:village") or "",
            "country": tags.get("addr:country") or "",
            "lat": lat, "lng": lng, "osm": True,
        })
    return out


async def main():
    import random
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    col = db["osm_churches"]
    await col.create_index("osm_id", unique=True)
    await col.create_index([("lat", 1), ("lng", 1)])

    cities = CITIES[:]
    random.shuffle(cities)  # broad global coverage early, not country-by-country
    start_total = await col.count_documents({})
    print(f"START: {start_total} churches already stored. Sweeping {len(cities)} metros...")

    async with httpx.AsyncClient(timeout=50) as client:
        failed = []
        for i, (name, lat, lng) in enumerate(cities, 1):
            t0 = time.time()
            els = await fetch_box(client, lat - HALF, lng - HALF, lat + HALF, lng + HALF)
            if els is None:
                print(f"[{i}/{len(cities)}] {name}: FAILED")
                failed.append((name, lat, lng))
                await asyncio.sleep(2)
                continue
            docs = parse(els)
            new = 0
            for d in docs:
                res = await col.update_one({"osm_id": d["osm_id"]}, {"$set": d}, upsert=True)
                if res.upserted_id is not None:
                    new += 1
            total = await col.count_documents({})
            print(f"[{i}/{len(cities)}] {name}: +{new} new ({len(docs)} found) | total={total} | {time.time()-t0:.1f}s")
            await asyncio.sleep(1.5)  # be polite to Overpass

        if failed:
            print(f"--- retry pass: {len(failed)} cities ---")
            await asyncio.sleep(15)
            for name, lat, lng in failed:
                els = await fetch_box(client, lat - HALF, lng - HALF, lat + HALF, lng + HALF)
                if els is None:
                    print(f"  retry {name}: still failed")
                    await asyncio.sleep(3)
                    continue
                for d in parse(els):
                    await col.update_one({"osm_id": d["osm_id"]}, {"$set": d}, upsert=True)
                print(f"  retry {name}: OK")
                await asyncio.sleep(2)

    total = await col.count_documents({})
    print(f"DONE. Total stored churches: {total} (added {total - start_total} this run).")


if __name__ == "__main__":
    asyncio.run(main())
