from fastapi import APIRouter, Depends, HTTPException, Query
from asyncpg import Pool
from loguru import logger
from typing import Optional
from src.schemas.trips import (
    OrderTripRequest,
    TripResponse,
    TripListItem,
    TripListResponse,
    TripDetail,
    RateTripRequest,
    RateTripResponse,
    TripStats,
)
from src.services.trips_service import (
    order_trip,
    get_trip,
    get_user_trips,
    rate_trip,
    get_user_stats,
)
from src.services.geo_service import build_route
from src.dependencies.db import get_write_db, get_read_db
from src.middleware.request_id import request_id_ctx

router = APIRouter(prefix="/trips", tags=["trips"])


# ============================================
# СОЗДАНИЕ ПОЕЗДКИ
# ============================================
@router.post("/order", response_model=TripResponse)
async def order_trip_endpoint(
    payload: OrderTripRequest, pool: Pool = Depends(get_write_db)
):
    """Заказ поездки"""
    request_id = request_id_ctx.get()

    logger.info(
        "🚕 Order trip request",
        extra={"request_id": request_id, "user_id": payload.user_id},
    )

    start = (payload.start_lat, payload.start_lon)
    end = (payload.end_lat, payload.end_lon)

    route = await build_route(start, end)

    trip_id = await order_trip(
        pool=pool,
        user_id=payload.user_id,
        start_lat=payload.start_lat,
        start_lon=payload.start_lon,
        end_lat=payload.end_lat,
        end_lon=payload.end_lon,
        start_address=payload.start_address or "Текущее местоположение",
        end_address=payload.end_address or "Точка на карте",
        route_geometry=route["geometry"],
        distance_m=route["distance_m"],
        duration_s=route["duration_s"],
        tariff=payload.tariff or "economy",
    )

    return TripResponse(
        trip_id=trip_id,
        distance_m=route["distance_m"],
        duration_s=route["duration_s"],
        geometry=route["geometry"],
    )


# ============================================
# СТАТИСТИКА (ДОЛЖНА БЫТЬ ДО /{trip_id}!)
# ============================================
@router.get("/stats", response_model=TripStats)
async def get_stats_endpoint(
    user_id: str = Query(..., description="ID пользователя"),
    pool: Pool = Depends(get_read_db),
):
    """Статистика поездок пользователя"""
    request_id = request_id_ctx.get()

    logger.info(
        "📊 Get trip stats", extra={"request_id": request_id, "user_id": user_id}
    )

    stats = await get_user_stats(pool, user_id)
    return TripStats(**stats)


# ============================================
# СПИСОК ПОЕЗДОК (ДОЛЖЕН БЫТЬ ДО /{trip_id}!)
# ============================================
@router.get("/", response_model=TripListResponse)
async def list_user_trips_endpoint(
    user_id: str = Query(..., description="ID пользователя"),
    limit: int = Query(15, ge=1, le=100, description="Количество на странице"),
    offset: int = Query(0, ge=0, description="Смещение"),
    pool: Pool = Depends(get_read_db),
):
    """Список поездок пользователя с пагинацией"""
    request_id = request_id_ctx.get()

    logger.info(
        "📋 List user trips",
        extra={
            "request_id": request_id,
            "user_id": user_id,
            "limit": limit,
            "offset": offset,
        },
    )

    trips = await get_user_trips(pool, user_id, limit, offset)
    total = len(trips)

    return TripListResponse(
        trips=[TripListItem(**trip) for trip in trips],
        total=total,
        limit=limit,
        offset=offset,
    )


# ============================================
# ДЕТАЛИ ПОЕЗДКИ (ДОЛЖЕН БЫТЬ ПОСЛЕ /stats и /)
# ============================================
@router.get("/{trip_id}", response_model=TripDetail)
async def get_trip_endpoint(trip_id: int, pool: Pool = Depends(get_read_db)):
    """Получение деталей поездки по ID"""
    request_id = request_id_ctx.get()

    logger.info(
        "🔍 Get trip details", extra={"request_id": request_id, "trip_id": trip_id}
    )

    trip = await get_trip(pool, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    return TripDetail(**trip)


# ============================================
# ОЦЕНКА ПОЕЗДКИ
# ============================================
@router.post("/{trip_id}/rate", response_model=RateTripResponse)
async def rate_trip_endpoint(
    trip_id: int, payload: RateTripRequest, pool: Pool = Depends(get_write_db)
):
    """Оценка поездки"""
    request_id = request_id_ctx.get()

    logger.info(
        "⭐ Rate trip",
        extra={"request_id": request_id, "trip_id": trip_id, "rating": payload.rating},
    )

    success = await rate_trip(pool, trip_id, payload.user_id, payload.rating)

    if not success:
        raise HTTPException(status_code=404, detail="Trip not found or access denied")

    return RateTripResponse(success=True, message="Rating saved successfully")


# ============================================
# СТАРЫЙ ENDPOINT (для совместимости)
# ============================================
@router.get("/user/{user_id}", response_model=list[TripListItem])
async def list_user_trips_legacy_endpoint(
    user_id: str, limit: int = 50, offset: int = 0, pool: Pool = Depends(get_read_db)
):
    """Список поездок пользователя (legacy)"""
    request_id = request_id_ctx.get()

    logger.info(
        "📋 List user trips (legacy)",
        extra={"request_id": request_id, "user_id": user_id},
    )

    trips = await get_user_trips(pool, user_id, limit, offset)
    return [TripListItem(**trip) for trip in trips]
