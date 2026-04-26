import logging
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from db import get_pool

logger = logging.getLogger("routes.map")
router = APIRouter()
VALID_COLOR_BY = {"median_income", "rpp", "walk_score", "rent_to_income"}

@router.get("/map", summary="GeoJSON map data")
async def get_map_data(color_by: str = Query(default="median_income", enum=list(VALID_COLOR_BY))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.metro_fips,c.name,c.lat,c.lon,c.median_income,c.rpp,c.walk_score,c.transit_score,c.bike_score,
                   t.rent_to_income,t.median_rent,t.date AS latest_trend_date
            FROM cities c
            LEFT JOIN LATERAL (SELECT rent_to_income,median_rent,date FROM trends WHERE metro_fips=c.metro_fips ORDER BY date DESC LIMIT 1) t ON true
            WHERE c.lat IS NOT NULL AND c.lon IS NOT NULL ORDER BY c.name
        """)
    features = [_feature(dict(r)) for r in rows]
    values   = [f["properties"].get(color_by) for f in features if f["properties"].get(color_by) is not None]
    return JSONResponse({"type":"FeatureCollection","features":features,"metadata":{"color_by":color_by,"color_range":{"min":min(values) if values else None,"max":max(values) if values else None},"city_count":len(features)}})

def _feature(row):
    return {"type":"Feature","geometry":{"type":"Point","coordinates":[row["lon"],row["lat"]]},"properties":{"metro_fips":row["metro_fips"],"name":row["name"],"median_income":row["median_income"],"rpp":row["rpp"],"walk_score":row["walk_score"],"transit_score":row["transit_score"],"bike_score":row["bike_score"],"rent_to_income":row["rent_to_income"],"median_rent":row["median_rent"],"latest_trend_date":str(row["latest_trend_date"]) if row["latest_trend_date"] else None}}
