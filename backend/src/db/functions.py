from asyncpg import Pool, Connection
from typing import Any, Dict, List, Optional
import json


async def create_trip(
    pool: Pool,
    user_id: str,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    start_address: Optional[str],
    end_address: Optional[str],
    route_geometry: List[List[float]],
    distance_m: int,
    duration_s: int,
) -> int:
    """Создание поездки через хранимую функцию"""
    async with pool.acquire() as conn:
        trip_id = await conn.fetchval(
            """
            SELECT taxi.create_trip(
                $1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10
            )
            """,
            user_id,
            start_lat,
            start_lon,
            end_lat,
            end_lon,
            start_address,
            end_address,
            json.dumps(route_geometry),
            distance_m,
            duration_s,
        )
        return trip_id


async def get_trip_by_id(pool: Pool, trip_id: int) -> Optional[Dict[str, Any]]:
    """Получение поездки по ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM taxi.get_trip_by_id($1)", trip_id)
        return dict(row) if row else None


async def list_user_trips(
    pool: Pool, user_id: str, limit: int = 50, offset: int = 0
) -> List[Dict[str, Any]]:
    """Список поездок пользователя"""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM taxi.list_user_trips($1, $2, $3)", user_id, limit, offset
        )
        return [dict(row) for row in rows]
