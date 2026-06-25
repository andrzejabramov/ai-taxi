from fastapi import APIRouter
from loguru import logger
from src.schemas.geo import GeocodeRequest, GeocodeResponse
from src.services.geo_service import geocode_address
from src.middleware.request_id import request_id_ctx

router = APIRouter(prefix="/geo", tags=["geo"])


@router.post("/geocode", response_model=GeocodeResponse)
async def geocode_endpoint(payload: GeocodeRequest):
    """Геокодинг адреса"""
    request_id = request_id_ctx.get()

    logger.info(
        "🗺 Geocode request",
        extra={"request_id": request_id, "address": payload.address},
    )

    result = await geocode_address(payload.address)

    return GeocodeResponse(**result)
