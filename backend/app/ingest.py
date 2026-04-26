"""
ingest.py
Pulls raw data from Census, BLS, Zillow, and OpenStreetMap (walkability).
"""

import os
import time
import logging
import requests
import pandas as pd
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY")

ZILLOW_RENT_URL = os.environ.get("ZILLOW_RENT_CSV_URL", "https://files.zillowstatic.com/research/public_csvs/zori/Metro_zori_uc_sfrcondomfr_sm_sa_month.csv")
ZILLOW_HOME_URL = os.environ.get("ZILLOW_HOME_CSV_URL", "https://files.zillowstatic.com/research/public_csvs/zhvi/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv")

METROS = [
    {"name": "New York, NY",    "state_fips": "36", "metro_fips": "35620", "bls_area_code": "S35620", "zillow_region": "New York, NY",                         "walkscore_address": "New York, NY",    "lat": 40.7128,  "lon": -74.0060},
    {"name": "Los Angeles, CA", "state_fips": "06", "metro_fips": "31080", "bls_area_code": "S31080", "zillow_region": "Los Angeles-Long Beach-Anaheim, CA",    "walkscore_address": "Los Angeles, CA", "lat": 34.0522,  "lon": -118.2437},
    {"name": "Chicago, IL",     "state_fips": "17", "metro_fips": "16980", "bls_area_code": "S16980", "zillow_region": "Chicago, IL",                           "walkscore_address": "Chicago, IL",     "lat": 41.8781,  "lon": -87.6298},
    {"name": "Austin, TX",      "state_fips": "48", "metro_fips": "12420", "bls_area_code": "S12420", "zillow_region": "Austin, TX",                            "walkscore_address": "Austin, TX",      "lat": 30.2672,  "lon": -97.7431},
    {"name": "Denver, CO",      "state_fips": "08", "metro_fips": "19740", "bls_area_code": "S19740", "zillow_region": "Denver, CO",                            "walkscore_address": "Denver, CO",      "lat": 39.7392,  "lon": -104.9903},
    {"name": "Nashville, TN",   "state_fips": "47", "metro_fips": "34980", "bls_area_code": "S34980", "zillow_region": "Nashville, TN",                         "walkscore_address": "Nashville, TN",   "lat": 36.1627,  "lon": -86.7816},
    {"name": "Phoenix, AZ",     "state_fips": "04", "metro_fips": "38060", "bls_area_code": "S38060", "zillow_region": "Phoenix, AZ",                           "walkscore_address": "Phoenix, AZ",     "lat": 33.4484,  "lon": -112.0740},
    {"name": "Seattle, WA",     "state_fips": "53", "metro_fips": "42660", "bls_area_code": "S42660", "zillow_region": "Seattle, WA",                           "walkscore_address": "Seattle, WA",     "lat": 47.6062,  "lon": -122.3321},
]

OSM_RADIUS = 2000
OSM_QUERIES = {
    "food":     'node["amenity"~"restaurant|cafe|fast_food|bar|pub"](around:{r},{lat},{lon});',
    "grocery":  'node["shop"~"supermarket|convenience|greengrocer"](around:{r},{lat},{lon});',
    "transit":  'node["highway"="bus_stop"](around:{r},{lat},{lon}); node["railway"~"station|subway_entrance|tram_stop"](around:{r},{lat},{lon});',
    "pharmacy": 'node["amenity"="pharmacy"](around:{r},{lat},{lon});',
    "bike":     'node["amenity"="bicycle_parking"](around:{r},{lat},{lon}); way["cycleway"](around:{r},{lat},{lon});',
}
OSM_CAP     = {"food": 300, "grocery": 50, "transit": 200, "pharmacy": 30, "bike": 100}
OSM_WEIGHTS = {"food": 0.30, "grocery": 0.25, "transit": 0.25, "pharmacy": 0.10, "bike": 0.10}


def fetch_census(year: int = 2022) -> list[dict]:
    if not CENSUS_API_KEY:
        raise EnvironmentError("CENSUS_API_KEY is not set")
    logger.info("Fetching Census income data for year %s", year)
    url    = f"https://api.census.gov/data/{year}/acs/acs1"
    params = {"get": "B19013_001E,NAME", "for": "metropolitan statistical area/micropolitan statistical area:*", "key": CENSUS_API_KEY}
    response = _get(url, params=params)
    if response is None:
        return []
    raw         = response.json()
    headers     = raw[0]
    rows        = raw[1:]
    income_col  = headers.index("B19013_001E")
    fips_col    = headers.index("metropolitan statistical area/micropolitan statistical area")
    target_fips = {m["metro_fips"] for m in METROS}
    results = []
    for row in rows:
        fips = row[fips_col]
        if fips not in target_fips:
            continue
        raw_income = row[income_col]
        if raw_income is None or int(raw_income) < 0:
            continue
        results.append({"metro_fips": fips, "median_income": int(raw_income), "year": year, "source": "census"})
    logger.info("Census: fetched %d metro records", len(results))
    return results


def fetch_bls() -> list[dict]:
    logger.info("Fetching BLS regional price parity data")
    url        = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    series_ids = [f"RPPALL{m['bls_area_code']}" for m in METROS]
    payload    = {"seriesid": series_ids, "startyear": "2020", "endyear": "2022", "calculations": False, "annualaverage": True}
    bls_key    = os.environ.get("BLS_API_KEY")
    if bls_key:
        payload["registrationkey"] = bls_key
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error("BLS request failed: %s", e)
        return []
    if data.get("status") != "REQUEST_SUCCEEDED":
        return []
    area_code_map = {f"RPPALL{m['bls_area_code']}": m["bls_area_code"] for m in METROS}
    results = []
    for series in data["Results"]["series"]:
        area_code = area_code_map.get(series["seriesID"])
        if not area_code:
            continue
        annual = [d for d in series["data"] if d.get("period") == "M13"]
        if not annual:
            continue
        latest = sorted(annual, key=lambda d: d["year"], reverse=True)[0]
        results.append({"bls_area_code": area_code, "rpp": float(latest["value"]), "year": int(latest["year"]), "source": "bls"})
    logger.info("BLS: fetched %d metro records", len(results))
    return results


def fetch_zillow(months_of_history: int = 60) -> list[dict]:
    logger.info("Fetching Zillow rent and home value CSVs")
    target_regions = {m["zillow_region"] for m in METROS}
    rent_df = _load_zillow_csv(ZILLOW_RENT_URL, "median_rent",       target_regions, months_of_history)
    home_df = _load_zillow_csv(ZILLOW_HOME_URL, "median_home_value", target_regions, months_of_history)
    if rent_df.empty and home_df.empty:
        return []
    if not rent_df.empty and not home_df.empty:
        merged = pd.merge(rent_df, home_df, on=["zillow_region", "date"], how="outer")
    elif not rent_df.empty:
        merged = rent_df
    else:
        merged = home_df
    merged["source"] = "zillow"
    return merged.to_dict(orient="records")


def _load_zillow_csv(url, value_col_name, target_regions, months):
    try:
        df = pd.read_csv(url)
    except Exception as e:
        logger.error("Failed to load Zillow CSV: %s", e)
        return pd.DataFrame()
    if "RegionName" not in df.columns:
        return pd.DataFrame()
    df        = df[df["RegionName"].isin(target_regions)]
    date_cols = sorted([c for c in df.columns if _is_date_col(c)])[-months:]
    melted    = df[["RegionName"] + date_cols].melt(id_vars="RegionName", var_name="date", value_name=value_col_name)
    melted.rename(columns={"RegionName": "zillow_region"}, inplace=True)
    melted.dropna(subset=[value_col_name], inplace=True)
    melted[value_col_name] = melted[value_col_name].astype(int)
    melted["date"] = melted["date"].str[:7]
    return melted


def _is_date_col(col):
    parts = col.split("-")
    return len(parts) == 3 and parts[0].isdigit() and len(parts[0]) == 4


def fetch_walkscore(delay_seconds: float = 2.0) -> list[dict]:
    logger.info("Fetching OSM walkability data for %d metros", len(METROS))
    overpass_servers = [
        "https://overpass-api.de/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]
    results = []
    for metro in METROS:
        counts = {}
        for cat_name, query_template in OSM_QUERIES.items():
            query_body     = query_template.format(r=OSM_RADIUS, lat=metro["lat"], lon=metro["lon"])
            overpass_query = f"[out:json][timeout:25];({query_body});out count;"
            success        = False
            for server in overpass_servers:
                try:
                    resp = requests.post(server, data={"data": overpass_query}, timeout=35, headers={"User-Agent": "LiveIndex/1.0"})
                    if resp.status_code in (429, 504):
                        time.sleep(3)
                        continue
                    resp.raise_for_status()
                    data             = resp.json()
                    counts[cat_name] = int(data.get("elements", [{}])[0].get("tags", {}).get("total", 0))
                    success          = True
                    break
                except Exception as e:
                    logger.warning("OSM %s failed for %s/%s: %s", server, metro["name"], cat_name, e)
                    time.sleep(3)
            if not success:
                counts[cat_name] = 0
            time.sleep(delay_seconds)
        normalized    = {k: min(100, int((counts[k] / OSM_CAP[k]) * 100)) for k in counts}
        walk_score    = int(sum(normalized[k] * OSM_WEIGHTS[k] for k in OSM_WEIGHTS if k in normalized))
        transit_score = normalized.get("transit", 0)
        bike_score    = normalized.get("bike", 0)
        results.append({"walkscore_address": metro["walkscore_address"], "walk_score": min(100, walk_score), "transit_score": transit_score, "bike_score": bike_score, "source": "osm"})
        logger.info("OSM: %s -> walk=%d transit=%d bike=%d", metro["name"], walk_score, transit_score, bike_score)
    logger.info("OSM: fetched %d metro records", len(results))
    return results


def _get(url, params=None, headers=None, retries=3):
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp
        except requests.HTTPError as e:
            if e.response.status_code in (401, 403, 404):
                return None
        except requests.RequestException:
            pass
        if attempt < retries:
            time.sleep(2 ** attempt)
    return None