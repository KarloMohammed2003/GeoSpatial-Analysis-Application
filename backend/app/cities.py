import logging
from fastapi import APIRouter, HTTPException, Query
from models import CityListItem, CityDetail
from db import get_pool

logger = logging.getLogger("routes.cities")
router = APIRouter()

@router.get("/cities", response_model=list[CityListItem], summary="List all cities")
async def list_cities(
    sort_by: str = Query(default="median_income", enum=["median_income","rpp","walk_score","name"]),
    order:   str = Query(default="desc",          enum=["asc","desc"]),
):
    col       = {"median_income":"median_income","rpp":"rpp","walk_score":"walk_score","name":"name"}.get(sort_by, "median_income")
    direction = "ASC" if order == "asc" else "DESC"
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(f"SELECT metro_fips,name,lat,lon,median_income,income_year,rpp,rpp_year,walk_score,transit_score,bike_score,updated_at FROM cities ORDER BY {col} {direction} NULLS LAST")
    return [dict(r) for r in rows]

@router.get("/cities/{fips}", response_model=CityDetail, summary="Get a city profile")
async def get_city(fips: str):
    if not fips.isdigit() or len(fips) != 5:
        raise HTTPException(status_code=422, detail=f"'{fips}' is not a valid 5-digit FIPS code.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT metro_fips,name,lat,lon,median_income,income_year,rpp,rpp_year,walk_score,transit_score,bike_score,updated_at FROM cities WHERE metro_fips=$1", fips)
        if not row:
            raise HTTPException(status_code=404, detail=f"No city found with FIPS '{fips}'.")
        trends = await conn.fetch("SELECT date,median_rent,median_home_value,rent_to_income FROM trends WHERE metro_fips=$1 ORDER BY date DESC LIMIT 12", fips)
    city = dict(row)
    city["trends"] = [dict(r) for r in trends]
    return city
