from asyncpg import Pool, Connection
from typing import Any, Dict, List, Optional
import json


# ============================================
# СОЗДАНИЕ ПОЕЗДКИ (с новыми полями)
# ============================================
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
    tariff: str = "economy",
    price: Optional[float] = None,
    payment_method: str = "card",
    car_model: Optional[str] = None,
    car_number: Optional[str] = None,
    driver_name: Optional[str] = None,
    driver_phone: Optional[str] = None,
) -> int:
    """Создание поездки через хранимую функцию taxi.create_trip"""
    async with pool.acquire() as conn:
        trip_id = await conn.fetchval(
            """
            SELECT taxi.create_trip(
                $1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10,
                $11, $12, $13, $14, $15, $16, $17
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
            tariff,
            price,
            payment_method,
            car_model,
            car_number,
            driver_name,
            driver_phone,
        )
        return trip_id


# ============================================
# ДЕТАЛИ ПОЕЗДКИ (автоматически возвращает все поля)
# ============================================
async def get_trip_by_id(pool: Pool, trip_id: int) -> Optional[Dict[str, Any]]:
    """Получение поездки по ID через taxi.get_trip_by_id"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM taxi.get_trip_by_id($1)", trip_id)
        return dict(row) if row else None


# ============================================
# СПИСОК ПОЕЗДОК (автоматически возвращает все поля)
# ============================================
async def list_user_trips(
    pool: Pool, user_id: str, limit: int = 15, offset: int = 0
) -> List[Dict[str, Any]]:
    """Список поездок пользователя через taxi.list_user_trips"""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM taxi.list_user_trips($1, $2, $3)", user_id, limit, offset
        )
        return [dict(row) for row in rows]


# ============================================
# ОЦЕНКА ПОЕЗДКИ (новая функция)
# ============================================
async def rate_trip_db(pool: Pool, trip_id: int, user_id: str, rating: int) -> bool:
    """Оценка поездки через taxi.rate_trip"""
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            "SELECT taxi.rate_trip($1, $2, $3)",
            trip_id,
            user_id,
            rating,
        )
        return bool(result)


# ============================================
# СТАТИСТИКА (новая функция)
# ============================================
async def get_user_trip_stats(pool: Pool, user_id: str) -> Dict[str, Any]:
    """Статистика поездок через taxi.get_user_trip_stats"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM taxi.get_user_trip_stats($1)", user_id)
        return (
            dict(row)
            if row
            else {
                "total_trips": 0,
                "month_trips": 0,
                "total_spent": 0,
                "month_spent": 0,
                "avg_rating": None,
            }
        )
