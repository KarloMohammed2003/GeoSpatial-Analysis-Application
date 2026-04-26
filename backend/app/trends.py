import logging
from fastapi import APIRouter, HTTPException, Query
from models import TrendResponse
from db import get_pool

logger = logging.getLogger("routes.trends")
router = APIRouter()

@router.get("/trends/{fips}", response_model=TrendResponse, summary="Get trend data for a city")
async def get_trends(fips: str, months: int = Query(default=24, ge=1, le=60)):
    if not fips.isdigit() or len(fips) != 5:
        raise HTTPException(status_code=422, detail=f"'{fips}' is not a valid 5-digit FIPS code.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        name = await conn.fetchval("SELECT name FROM cities WHERE metro_fips=$1", fips)
        if not name: raise HTTPException(status_code=404, detail=f"No city found with FIPS '{fips}'.")
        rows = await conn.fetch("SELECT date,median_rent,median_home_value,rent_to_income FROM trends WHERE metro_fips=$1 ORDER BY date DESC LIMIT $2", fips, months)
    if not rows:
        return {"metro_fips": fips, "name": name, "months_returned": 0, "series": [], "summary": None}
    series = [dict(r) for r in reversed(rows)]
    return {"metro_fips": fips, "name": name, "months_returned": len(series), "series": series, "summary": _summary(series)}

def _summary(series):
    if not series: return None
    latest = series[-1]
    cr, ch, crti = latest.get("median_rent"), latest.get("median_home_value"), latest.get("rent_to_income")
    yoy_r = yoy_h = None
    if len(series) >= 12:
        ago = series[-12]
        if cr and ago.get("median_rent") and ago["median_rent"] > 0:
            yoy_r = round(((cr - ago["median_rent"]) / ago["median_rent"]) * 100, 1)
        if ch and ago.get("median_home_value") and ago["median_home_value"] > 0:
            yoy_h = round(((ch - ago["median_home_value"]) / ago["median_home_value"]) * 100, 1)
    return {"latest_date": latest.get("date"), "current_rent": cr, "current_home_value": ch, "current_rent_to_income": crti, "yoy_rent_change_pct": yoy_r, "yoy_home_change_pct": yoy_h}
