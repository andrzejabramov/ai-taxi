from asyncpg import Pool
from loguru import logger
from src.db.functions import (
    create_trip,
    get_trip_by_id,
    list_user_trips,
    rate_trip_db,
    get_user_trip_stats,
)
from src.middleware.request_id import request_id_ctx
from src.exceptions.base import ValidationError


async def order_trip(
    pool: Pool,
    user_id: str,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    start_address: str | None,
    end_address: str | None,
    route_geometry: list[list[float]],
    distance_m: int,
    duration_s: int,
    tariff: str = "economy",
    price: float | None = None,
    payment_method: str = "card",
    car_model: str | None = None,
    car_number: str | None = None,
    driver_name: str | None = None,
    driver_phone: str | None = None,
) -> int:
    """Создание поездки"""
    request_id = request_id_ctx.get()

    logger.info(
        "🚕 Creating trip",
        extra={
            "request_id": request_id,
            "user_id": user_id,
            "start": (start_lat, start_lon),
            "end": (end_lat, end_lon),
            "tariff": tariff,
        },
    )

    try:
        trip_id = await create_trip(
            pool=pool,
            user_id=user_id,
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            start_address=start_address,
            end_address=end_address,
            route_geometry=route_geometry,
            distance_m=distance_m,
            duration_s=duration_s,
            tariff=tariff,
            price=price,
            payment_method=payment_method,
            car_model=car_model,
            car_number=car_number,
            driver_name=driver_name,
            driver_phone=driver_phone,
        )

        logger.info(
            "✅ Trip created",
            extra={"request_id": request_id, "trip_id": trip_id, "tariff": tariff},
        )
        return trip_id

    except Exception as e:
        logger.error(
            "❌ Failed to create trip",
            extra={"request_id": request_id, "error": str(e)},
        )
        raise ValidationError("Не удалось создать поездку", {"error": str(e)})


async def get_trip(pool: Pool, trip_id: int) -> dict | None:
    """Получение поездки по ID (все поля, включая новые)"""
    request_id = request_id_ctx.get()

    logger.debug(
        "🔍 Getting trip", extra={"request_id": request_id, "trip_id": trip_id}
    )

    try:
        trip = await get_trip_by_id(pool, trip_id)

        if trip:
            logger.info(
                "✅ Trip found", extra={"request_id": request_id, "trip_id": trip_id}
            )
        else:
            logger.warning(
                "⚠️ Trip not found",
                extra={"request_id": request_id, "trip_id": trip_id},
            )

        return trip

    except Exception as e:
        logger.error(
            "❌ Failed to get trip",
            extra={"request_id": request_id, "trip_id": trip_id, "error": str(e)},
        )
        raise


async def get_user_trips(
    pool: Pool, user_id: str, limit: int = 15, offset: int = 0
) -> list[dict]:
    """Список поездок пользователя (с новыми полями)"""
    request_id = request_id_ctx.get()

    logger.debug(
        "📋 Listing user trips",
        extra={
            "request_id": request_id,
            "user_id": user_id,
            "limit": limit,
            "offset": offset,
        },
    )

    try:
        trips = await list_user_trips(pool, user_id, limit, offset)

        logger.info(
            "✅ User trips retrieved",
            extra={"request_id": request_id, "user_id": user_id, "count": len(trips)},
        )
        return trips

    except Exception as e:
        logger.error(
            "❌ Failed to list user trips",
            extra={"request_id": request_id, "user_id": user_id, "error": str(e)},
        )
        raise


async def rate_trip(pool: Pool, trip_id: int, user_id: str, rating: int) -> bool:
    """Оценка поездки"""
    request_id = request_id_ctx.get()

    logger.info(
        "⭐ Rating trip",
        extra={
            "request_id": request_id,
            "trip_id": trip_id,
            "user_id": user_id,
            "rating": rating,
        },
    )

    try:
        success = await rate_trip_db(pool, trip_id, user_id, rating)

        if success:
            logger.info(
                "✅ Trip rated", extra={"request_id": request_id, "trip_id": trip_id}
            )
        else:
            logger.warning(
                "⚠️ Failed to rate trip",
                extra={"request_id": request_id, "trip_id": trip_id},
            )

        return success

    except Exception as e:
        logger.error(
            "❌ Failed to rate trip",
            extra={"request_id": request_id, "trip_id": trip_id, "error": str(e)},
        )
        raise


async def get_user_stats(pool: Pool, user_id: str) -> dict:
    """Статистика поездок пользователя"""
    request_id = request_id_ctx.get()

    logger.debug(
        "📊 Getting user stats", extra={"request_id": request_id, "user_id": user_id}
    )

    try:
        stats = await get_user_trip_stats(pool, user_id)

        logger.info(
            "✅ User stats retrieved",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "total_trips": stats.get("total_trips"),
            },
        )
        return stats

    except Exception as e:
        logger.error(
            "❌ Failed to get user stats",
            extra={"request_id": request_id, "user_id": user_id, "error": str(e)},
        )
        raise
