import logging
import os
from typing import Optional
import asyncpg

logger = logging.getLogger("db")
_pool: Optional[asyncpg.Pool] = None
DATABASE_URL = os.environ.get("DATABASE_URL")

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise EnvironmentError("DATABASE_URL is not set")
        logger.info("Creating database connection pool")
        _pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=2, max_size=10, command_timeout=30)
    return _pool

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")
