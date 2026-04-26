import asyncio
import logging
from datetime import datetime
import asyncpg
from db import get_pool

logger = logging.getLogger(__name__)

METRO_COORDS = {
    "35620": (40.7128,  -74.0060), "31080": (34.0522, -118.2437),
    "16980": (41.8781,  -87.6298), "12420": (30.2672,  -97.7431),
    "19740": (39.7392, -104.9903), "34980": (36.1627,  -86.7816),
    "38060": (33.4484, -112.0740), "42660": (47.6062, -122.3321),
}

def upsert_cities(records):
    return asyncio.get_event_loop().run_until_complete(_upsert_cities_async(records))

async def _upsert_cities_async(records):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = []
        for r in records:
            lat, lon = METRO_COORDS.get(r["metro_fips"], (None, None))
            rows.append((r["metro_fips"], r["name"], lat, lon, r.get("median_income"), r.get("income_year"), r.get("rpp"), r.get("rpp_year"), r.get("walk_score"), r.get("transit_score"), r.get("bike_score")))
        await conn.executemany("""
            INSERT INTO cities (metro_fips,name,lat,lon,median_income,income_year,rpp,rpp_year,walk_score,transit_score,bike_score)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            ON CONFLICT (metro_fips) DO UPDATE SET
                name=EXCLUDED.name, lat=COALESCE(EXCLUDED.lat,cities.lat), lon=COALESCE(EXCLUDED.lon,cities.lon),
                median_income=COALESCE(EXCLUDED.median_income,cities.median_income),
                income_year=COALESCE(EXCLUDED.income_year,cities.income_year),
                rpp=COALESCE(EXCLUDED.rpp,cities.rpp), rpp_year=COALESCE(EXCLUDED.rpp_year,cities.rpp_year),
                walk_score=COALESCE(EXCLUDED.walk_score,cities.walk_score),
                transit_score=COALESCE(EXCLUDED.transit_score,cities.transit_score),
                bike_score=COALESCE(EXCLUDED.bike_score,cities.bike_score)
        """, rows)
    return len(rows)

def upsert_trends(records):
    return asyncio.get_event_loop().run_until_complete(_upsert_trends_async(records))

async def _upsert_trends_async(records):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = [(r["metro_fips"], r["date"], r.get("median_rent"), r.get("median_home_value"), r.get("rent_to_income")) for r in records]
        await conn.executemany("""
            INSERT INTO trends (metro_fips,date,median_rent,median_home_value,rent_to_income)
            VALUES ($1,$2,$3,$4,$5)
            ON CONFLICT (metro_fips,date) DO UPDATE SET
                median_rent=COALESCE(EXCLUDED.median_rent,trends.median_rent),
                median_home_value=COALESCE(EXCLUDED.median_home_value,trends.median_home_value),
                rent_to_income=COALESCE(EXCLUDED.rent_to_income,trends.rent_to_income)
        """, rows)
    return len(rows)

def record_pipeline_run(source, success, started_at, finished_at, cities_upserted, trends_upserted, errors):
    try:
        asyncio.get_event_loop().run_until_complete(_record_pipeline_run_async(source, success, started_at, finished_at, cities_upserted, trends_upserted, errors))
    except Exception as e:
        logger.error("record_pipeline_run failed: %s", e)

async def _record_pipeline_run_async(source, success, started_at, finished_at, cities_upserted, trends_upserted, errors):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO pipeline_runs (source,success,started_at,finished_at,cities_upserted,trends_upserted,errors) VALUES ($1,$2,$3,$4,$5,$6,$7)", source, success, started_at, finished_at, cities_upserted, trends_upserted, errors)
