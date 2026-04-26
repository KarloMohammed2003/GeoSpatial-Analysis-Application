"""
main.py — FastAPI application entry point.
Run: uvicorn main:app --reload --port 8000
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from db import get_pool, close_pool
import cities, compare, trends, listings
import map as map_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("main")

API_PREFIX      = "/api/v1"
APP_ENV         = os.environ.get("APP_ENV", "development")
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting LiveIndex API (env=%s)", APP_ENV)
    await get_pool()
    logger.info("Database pool ready")
    yield
    await close_pool()


app = FastAPI(title="LiveIndex API", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["GET"], allow_headers=["*"])


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start    = time.perf_counter()
    response = await call_next(request)
    logger.info("%s %s -> %d (%.1fms)", request.method, request.url.path, response.status_code, (time.perf_counter() - start) * 1000)
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"error": "internal_server_error", "message": "Something went wrong."})


app.include_router(cities.router,       prefix=API_PREFIX, tags=["Cities"])
app.include_router(compare.router,      prefix=API_PREFIX, tags=["Compare"])
app.include_router(trends.router,       prefix=API_PREFIX, tags=["Trends"])
app.include_router(map_router.router,   prefix=API_PREFIX, tags=["Map"])
app.include_router(listings.router,     prefix=API_PREFIX, tags=["Listings"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/status", tags=["Health"])
async def status_check():
    db_ok = city_count = trend_count = 0
    last_run = None
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            db_ok       = True
            city_count  = await conn.fetchval("SELECT COUNT(*) FROM cities")
            trend_count = await conn.fetchval("SELECT COUNT(*) FROM trends")
            row = await conn.fetchrow("SELECT source,success,started_at,cities_upserted,trends_upserted,errors FROM pipeline_runs ORDER BY started_at DESC LIMIT 1")
            if row:
                last_run = dict(row)
                last_run["started_at"] = last_run["started_at"].isoformat()
    except Exception as e:
        logger.error("Status check failed: %s", e)
    return {"status": "ok" if db_ok else "degraded", "database": "connected" if db_ok else "unavailable", "records": {"cities": city_count, "trends": trend_count}, "last_pipeline_run": last_run, "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/", include_in_schema=False)
async def root():
    return {"name": "LiveIndex API", "version": "1.0.0", "docs": "/docs"}
