"""
routes/listings.py
GET /api/v1/listings/{fips}  Property listings for a city via Rentcast API.
Results are cached in Postgres for 7 days.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from db import get_pool

logger          = logging.getLogger("routes.listings")
router          = APIRouter()
RENTCAST_API_KEY = os.environ.get("RENTCAST_API_KEY")
CACHE_TTL_DAYS  = 7

FIPS_TO_CITY = {
    "35620": "New York, NY",    "31080": "Los Angeles, CA",
    "16980": "Chicago, IL",     "12420": "Austin, TX",
    "19740": "Denver, CO",      "34980": "Nashville, TN",
    "38060": "Phoenix, AZ",     "42660": "Seattle, WA",
}


@router.get("/listings/{fips}", summary="Get property listings for a city")
async def get_listings(
    fips:         str,
    listing_type: str = Query(default="residential", enum=["residential","commercial"]),
    status:       str = Query(default="For Rent",    enum=["For Rent","For Sale"]),
    limit:        int = Query(default=20, ge=1, le=50),
):
    if not fips.isdigit() or len(fips) != 5:
        raise HTTPException(status_code=422, detail=f"'{fips}' is not a valid FIPS code.")
    city = FIPS_TO_CITY.get(fips)
    if not city:
        raise HTTPException(status_code=404, detail=f"No city found for FIPS '{fips}'.")

    pool = await get_pool()

    # Check cache
    async with pool.acquire() as conn:
        cached = await conn.fetchrow(
            "SELECT listings,fetched_at FROM listings_cache WHERE metro_fips=$1 AND listing_type=$2 AND status=$3",
            fips, listing_type, status,
        )
    if cached:
        age = datetime.now(timezone.utc) - cached["fetched_at"].replace(tzinfo=timezone.utc)
        if age < timedelta(days=CACHE_TTL_DAYS):
            return JSONResponse({"listings": json.loads(cached["listings"]), "source": "cache", "city": city})

    if not RENTCAST_API_KEY:
        raise HTTPException(status_code=503, detail="Listings service not configured — RENTCAST_API_KEY missing.")

    listings = await _fetch_from_rentcast(city, listing_type, status, limit)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO listings_cache (metro_fips,listing_type,status,listings,fetched_at)
            VALUES ($1,$2,$3,$4,NOW())
            ON CONFLICT (metro_fips,listing_type,status)
            DO UPDATE SET listings=EXCLUDED.listings, fetched_at=EXCLUDED.fetched_at
            """,
            fips, listing_type, status, json.dumps(listings),
        )

    return JSONResponse({"listings": listings, "source": "rentcast", "city": city})


async def _fetch_from_rentcast(city: str, listing_type: str, status: str, limit: int) -> list:
    url = "https://api.rentcast.io/v1/listings/sale" if status == "For Sale" else "https://api.rentcast.io/v1/listings/rental/long-term"
    city_name, state = (city.split(",")[0].strip(), city.split(",")[1].strip()) if "," in city else (city, "")
    params = {"city": city_name, "state": state, "limit": limit, "status": "Active"}
    if listing_type == "commercial":
        params["propertyType"] = "Commercial"
    headers = {"X-Api-Key": RENTCAST_API_KEY, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Rentcast API error %s: %s", e.response.status_code, e.response.text)
        raise HTTPException(status_code=502, detail="Failed to fetch listings from Rentcast.")
    except Exception as e:
        logger.error("Rentcast request failed: %s", e)
        raise HTTPException(status_code=502, detail="Listings service unavailable.")

    results = []
    for item in (data if isinstance(data, list) else data.get("listings", [])):
        results.append({
            "id":             item.get("id"),
            "address":        item.get("formattedAddress") or item.get("addressLine1", ""),
            "price":          item.get("price") or item.get("rent"),
            "bedrooms":       item.get("bedrooms"),
            "bathrooms":      item.get("bathrooms"),
            "sqft":           item.get("squareFootage"),
            "property_type":  item.get("propertyType"),
            "listing_type":   status,
            "url":            item.get("listingUrl"),
            "days_on_market": item.get("daysOnMarket"),
        })
    return results
