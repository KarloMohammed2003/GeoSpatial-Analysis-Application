"""
scheduler.py
Orchestrates the full ETL pipeline on a weekly schedule.

Usage:
    python scheduler.py            # start scheduler (blocking)
    python scheduler.py --run-now  # run once and exit
    python scheduler.py --run-now --source walkscore
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from ingest import fetch_census, fetch_bls, fetch_zillow, fetch_walkscore
from clean  import clean_census, clean_bls, clean_walkscore, clean_zillow, merge_city_records
from load   import upsert_cities, upsert_trends, record_pipeline_run

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("scheduler")

ALERT_WEBHOOK_URL = os.environ.get("PIPELINE_ALERT_URL")


def run_pipeline(source="all"):
    started_at = datetime.now(timezone.utc)
    logger.info("Pipeline starting - source=%s", source)
    census_clean, bls_clean, ws_clean, zillow_clean = {}, {}, {}, []
    errors = []

    if source in ("census", "all"):
        try:
            census_clean = clean_census(fetch_census())
        except Exception as e:
            errors.append(f"Census: {e}"); logger.error("Census failed: %s", e, exc_info=True)

    if source in ("bls", "all"):
        try:
            bls_clean = clean_bls(fetch_bls())
        except Exception as e:
            errors.append(f"BLS: {e}"); logger.error("BLS failed: %s", e, exc_info=True)

    if source in ("walkscore", "all"):
        try:
            ws_clean = clean_walkscore(fetch_walkscore())
        except Exception as e:
            errors.append(f"OSM: {e}"); logger.error("OSM failed: %s", e, exc_info=True)

    if source in ("zillow", "all"):
        try:
            zillow_clean = clean_zillow(fetch_zillow(), income_by_fips=census_clean)
        except Exception as e:
            errors.append(f"Zillow: {e}"); logger.error("Zillow failed: %s", e, exc_info=True)

    cities_upserted = trends_upserted = 0
    try:
        if source == "all" or source in ("census", "bls", "walkscore"):
            city_records = merge_city_records(census_clean, bls_clean, ws_clean)
            if city_records:
                cities_upserted = upsert_cities(city_records)
        if zillow_clean:
            trends_upserted = upsert_trends(zillow_clean)
    except Exception as e:
        errors.append(f"Load: {e}"); logger.error("Load failed: %s", e, exc_info=True)

    finished_at = datetime.now(timezone.utc)
    success     = len(errors) == 0
    record_pipeline_run(source, success, started_at, finished_at, cities_upserted, trends_upserted, errors)

    if success:
        logger.info("Pipeline done - %d cities, %d trends", cities_upserted, trends_upserted)
    else:
        logger.error("Pipeline failed: %s", "; ".join(errors))

    return success


def _check_env():
    return [v for v in ["CENSUS_API_KEY", "DATABASE_URL"] if not os.environ.get(v)]


def start_scheduler():
    missing = _check_env()
    if missing:
        logger.error("Missing env vars: %s", ", ".join(missing)); sys.exit(1)
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run_pipeline, CronTrigger(day_of_week="sun", hour=2), kwargs={"source": "all"},    id="full_pipeline",  max_instances=1, coalesce=True, misfire_grace_time=3600)
    scheduler.add_job(run_pipeline, CronTrigger(day_of_week="mon", hour=3), kwargs={"source": "zillow"}, id="zillow_refresh", max_instances=1, coalesce=True, misfire_grace_time=3600)
    logger.info("Scheduler started")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument("--source",  choices=["census","bls","zillow","walkscore","all"], default="all")
    args = parser.parse_args()
    missing = _check_env()
    if missing:
        logger.error("Missing env vars: %s", ", ".join(missing)); sys.exit(1)
    if args.run_now:
        sys.exit(0 if run_pipeline(source=args.source) else 1)
    else:
        start_scheduler()
