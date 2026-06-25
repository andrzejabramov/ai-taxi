from fastapi import APIRouter, Depends, HTTPException
from asyncpg import Pool
from loguru import logger
from src.schemas.trips import OrderTripRequest, TripResponse, TripListItem
from src.services.trips_service import order_trip, get_trip, get_user_trips
from src.services.geo_service import build_route
from src.dependencies.db import get_write_db, get_read_db
from src.middleware.request_id import request_id_ctx

router = APIRouter(prefix="/trips", tags=["trips"])


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
        start_address="Текущее местоположение",
        end_address=payload.end_address or "Точка на карте",
        route_geometry=route["geometry"],
        distance_m=route["distance_m"],
        duration_s=route["duration_s"],
    )

    return TripResponse(
        trip_id=trip_id,
        distance_m=route["distance_m"],
        duration_s=route["duration_s"],
        geometry=route["geometry"],
    )


@router.get("/{trip_id}", response_model=TripListItem)
async def get_trip_endpoint(trip_id: int, pool: Pool = Depends(get_read_db)):
    """Получение поездки по ID"""
    request_id = request_id_ctx.get()

    logger.info(
        "🔍 Get trip request", extra={"request_id": request_id, "trip_id": trip_id}
    )

    trip = await get_trip(pool, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    return TripListItem(**trip)


@router.get("/user/{user_id}", response_model=list[TripListItem])
async def list_user_trips_endpoint(
    user_id: str, limit: int = 50, offset: int = 0, pool: Pool = Depends(get_read_db)
):
    """Список поездок пользователя"""
    request_id = request_id_ctx.get()

    logger.info(
        "📋 List user trips request",
        extra={"request_id": request_id, "user_id": user_id},
    )

    trips = await get_user_trips(pool, user_id, limit, offset)

    return [TripListItem(**trip) for trip in trips]
