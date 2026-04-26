"""
clean.py
Normalizes raw ingest data into a unified schema for load.py.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

INCOME_MIN, INCOME_MAX         = 10_000, 500_000
RPP_MIN,    RPP_MAX            = 50.0,   200.0
RENT_MIN,   RENT_MAX           = 200,    20_000
HOME_VALUE_MIN, HOME_VALUE_MAX = 50_000, 5_000_000
SCORE_MIN,  SCORE_MAX          = 0,      100

FIPS_TO_NAME = {
    "35620": "New York, NY",    "31080": "Los Angeles, CA",
    "16980": "Chicago, IL",     "12420": "Austin, TX",
    "19740": "Denver, CO",      "34980": "Nashville, TN",
    "38060": "Phoenix, AZ",     "42660": "Seattle, WA",
}

BLS_AREA_TO_FIPS = {
    "S35620": "35620", "S31080": "31080", "S16980": "16980", "S12420": "12420",
    "S19740": "19740", "S34980": "34980", "S38060": "38060", "S42660": "42660",
}

ZILLOW_REGION_TO_FIPS = {
    "New York, NY": "35620", "Los Angeles-Long Beach-Anaheim, CA": "31080",
    "Chicago, IL":  "16980", "Austin, TX":      "12420",
    "Denver, CO":   "19740", "Nashville, TN":   "34980",
    "Phoenix, AZ":  "38060", "Seattle, WA":     "42660",
}

WALKSCORE_ADDRESS_TO_FIPS = {
    "New York, NY": "35620", "Los Angeles, CA": "31080", "Chicago, IL":   "16980",
    "Austin, TX":   "12420", "Denver, CO":      "19740", "Nashville, TN": "34980",
    "Phoenix, AZ":  "38060", "Seattle, WA":     "42660",
}


def clean_census(raw):
    cleaned, skipped = {}, 0
    for record in raw:
        fips   = _coerce_str(record.get("metro_fips"))
        income = _coerce_int(record.get("median_income"))
        year   = _coerce_int(record.get("year"))
        if not fips or not _in_range(income, INCOME_MIN, INCOME_MAX) or fips not in FIPS_TO_NAME:
            skipped += 1; continue
        cleaned[fips] = {"metro_fips": fips, "median_income": income, "income_year": year}
    logger.info("Census clean: %d kept, %d skipped", len(cleaned), skipped)
    return cleaned


def clean_bls(raw):
    cleaned, skipped = {}, 0
    for record in raw:
        area_code = _coerce_str(record.get("bls_area_code"))
        rpp       = _coerce_float(record.get("rpp"))
        year      = _coerce_int(record.get("year"))
        fips      = BLS_AREA_TO_FIPS.get(area_code)
        if not fips or not _in_range(rpp, RPP_MIN, RPP_MAX):
            skipped += 1; continue
        cleaned[fips] = {"metro_fips": fips, "rpp": rpp, "rpp_year": year}
    logger.info("BLS clean: %d kept, %d skipped", len(cleaned), skipped)
    return cleaned


def clean_walkscore(raw):
    cleaned, skipped = {}, 0
    for record in raw:
        address = _coerce_str(record.get("walkscore_address"))
        fips    = WALKSCORE_ADDRESS_TO_FIPS.get(address)
        walk    = _coerce_score(record.get("walk_score"))
        if not fips or walk is None:
            skipped += 1; continue
        cleaned[fips] = {"metro_fips": fips, "walk_score": walk, "transit_score": _coerce_score(record.get("transit_score")), "bike_score": _coerce_score(record.get("bike_score"))}
    logger.info("WalkScore clean: %d kept, %d skipped", len(cleaned), skipped)
    return cleaned


def clean_zillow(raw, income_by_fips=None):
    cleaned, skipped = [], 0
    for record in raw:
        region = _coerce_str(record.get("zillow_region"))
        fips   = ZILLOW_REGION_TO_FIPS.get(region)
        if not fips:
            skipped += 1; continue
        date = _coerce_date(record.get("date"))
        if not date:
            skipped += 1; continue
        rent       = _coerce_int(record.get("median_rent"))
        home_value = _coerce_int(record.get("median_home_value"))
        if rent       is not None and not _in_range(rent,       200,    20_000):  rent       = None
        if home_value is not None and not _in_range(home_value, 50_000, 5_000_000): home_value = None
        if rent is None and home_value is None:
            skipped += 1; continue
        rent_to_income = None
        if rent and income_by_fips:
            rec = income_by_fips.get(fips)
            if rec and rec.get("median_income"):
                rent_to_income = round((rent / (rec["median_income"] / 12)) * 100, 1)
        cleaned.append({"metro_fips": fips, "date": date, "median_rent": rent, "median_home_value": home_value, "rent_to_income": rent_to_income})
    logger.info("Zillow clean: %d kept, %d skipped", len(cleaned), skipped)
    return cleaned


def merge_city_records(census, bls, walkscore):
    results = []
    for fips in set(census) | set(bls) | set(walkscore):
        name = FIPS_TO_NAME.get(fips)
        if not name or not census.get(fips):
            continue
        c, b, w = census.get(fips, {}), bls.get(fips, {}), walkscore.get(fips, {})
        results.append({"metro_fips": fips, "name": name, "median_income": c.get("median_income"), "income_year": c.get("income_year"), "rpp": b.get("rpp"), "rpp_year": b.get("rpp_year"), "walk_score": w.get("walk_score"), "transit_score": w.get("transit_score"), "bike_score": w.get("bike_score")})
    logger.info("merge: %d unified city records", len(results))
    return results


def _coerce_str(v):
    return str(v).strip() or None if v is not None else None

def _coerce_int(v):
    try: return int(float(v))
    except: return None

def _coerce_float(v):
    try: return float(v)
    except: return None

def _coerce_score(v):
    n = _coerce_int(v)
    return n if n is not None and 0 <= n <= 100 else None

def _coerce_date(v):
    s = _coerce_str(v)
    if not s: return None
    parts = s.split("-")
    return f"{parts[0]}-{parts[1]}" if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit() else None

def _in_range(v, lo, hi):
    try: return lo <= float(v) <= hi
    except: return False
