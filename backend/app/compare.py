import logging
from fastapi import APIRouter, HTTPException, Query
from models import CompareResponse
from db import get_pool

logger = logging.getLogger("routes.compare")
router = APIRouter()

@router.get("/compare", response_model=CompareResponse, summary="Compare 2-4 cities")
async def compare_cities(ids: str = Query(..., description="Comma-separated FIPS codes, 2-4 cities")):
    fips_list = [f.strip() for f in ids.split(",") if f.strip()]
    if len(fips_list) < 2: raise HTTPException(status_code=422, detail="At least 2 FIPS codes required.")
    if len(fips_list) > 4: raise HTTPException(status_code=422, detail="Maximum 4 cities per comparison.")
    bad = [f for f in fips_list if not f.isdigit() or len(f) != 5]
    if bad: raise HTTPException(status_code=422, detail=f"Invalid FIPS code(s): {', '.join(bad)}.")
    seen = set()
    unique = [f for f in fips_list if not (f in seen or seen.add(f))]
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT metro_fips,name,lat,lon,median_income,income_year,rpp,rpp_year,walk_score,transit_score,bike_score,updated_at FROM cities WHERE metro_fips=ANY($1::text[])", unique)
    if not rows: raise HTTPException(status_code=404, detail="None of the provided FIPS codes matched known cities.")
    fips_map = {r["metro_fips"]: dict(r) for r in rows}
    cities   = [fips_map[f] for f in unique if f in fips_map]
    return {"cities": cities, "rankings": _rankings(cities), "count": len(cities)}

def _rankings(cities):
    def best(key, higher=True):
        c = [x for x in cities if x.get(key) is not None]
        return (max if higher else min)(c, key=lambda x: x[key])["metro_fips"] if c else None
    return {"best_income": best("median_income"), "best_rpp": best("rpp", higher=False), "best_walk_score": best("walk_score"), "best_transit_score": best("transit_score"), "best_bike_score": best("bike_score")}
