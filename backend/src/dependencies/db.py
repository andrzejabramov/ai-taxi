from fastapi import Depends
from asyncpg import Pool
from loguru import logger
from src.db.pools import get_write_pool, get_read_pool
from src.middleware.request_id import request_id_ctx


async def get_write_db() -> Pool:
    """Dependency: пул для записи"""
    request_id = request_id_ctx.get()
    logger.debug("🔌 Acquiring write DB pool", extra={"request_id": request_id})

    try:
        pool = get_write_pool()
        logger.debug("✅ Write DB pool acquired", extra={"request_id": request_id})
        return pool
    except Exception as e:
        logger.error(
            "❌ Failed to acquire write DB pool",
            extra={"request_id": request_id, "error": str(e)},
        )
        raise


async def get_read_db() -> Pool:
    """Dependency: пул для чтения"""
    request_id = request_id_ctx.get()
    logger.debug("🔌 Acquiring read DB pool", extra={"request_id": request_id})

    try:
        pool = get_read_pool()
        logger.debug("✅ Read DB pool acquired", extra={"request_id": request_id})
        return pool
    except Exception as e:
        logger.error(
            "❌ Failed to acquire read DB pool",
            extra={"request_id": request_id, "error": str(e)},
        )
        raise
