from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
import json


# ============================================
# ЗАПРОСЫ
# ============================================
class OrderTripRequest(BaseModel):
    """Запрос на создание поездки"""

    user_id: str
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    end_address: Optional[str] = None
    start_address: Optional[str] = None
    route_geometry: Optional[List[List[float]]] = None
    distance_m: Optional[int] = None
    duration_s: Optional[int] = None
    tariff: Optional[str] = "economy"


class RateTripRequest(BaseModel):
    """Запрос на оценку поездки"""

    user_id: str
    rating: int = Field(..., ge=1, le=5, description="Оценка от 1 до 5")


# ============================================
# ОТВЕТЫ
# ============================================
class TripResponse(BaseModel):
    """Ответ после создания поездки"""

    trip_id: int
    distance_m: int
    duration_s: int
    geometry: List[List[float]]


class TripListItem(BaseModel):
    """Элемент списка поездок (для таблицы в дашборде)"""

    id: int
    start_address: Optional[str] = None
    end_address: Optional[str] = None
    distance_m: Optional[int] = None
    duration_s: Optional[int] = None
    status: str
    created_at: datetime
    tariff: Optional[str] = None
    price: Optional[float] = None
    car_model: Optional[str] = None
    driver_name: Optional[str] = None
    rating: Optional[int] = None


class TripListResponse(BaseModel):
    """Ответ со списком поездок"""

    trips: List[TripListItem]
    total: int
    limit: int
    offset: int


class TripDetail(BaseModel):
    """Детали конкретной поездки (для карточки)"""

    id: int
    user_id: str
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    start_address: Optional[str] = None
    end_address: Optional[str] = None
    route_geometry: Optional[Any] = None
    distance_m: Optional[int] = None
    duration_s: Optional[int] = None
    status: str
    created_at: datetime
    tariff: Optional[str] = None
    price: Optional[float] = None
    payment_method: Optional[str] = None
    car_model: Optional[str] = None
    car_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    rating: Optional[int] = None

    @field_validator("route_geometry", mode="before")
    @classmethod
    def parse_route_geometry(cls, v):
        """Парсит JSON-строку в список"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v


class RateTripResponse(BaseModel):
    """Ответ после оценки"""

    success: bool
    message: str


class TripStats(BaseModel):
    """Статистика поездок для дашборда"""

    total_trips: int
    month_trips: int
    total_spent: float
    month_spent: float
    avg_rating: Optional[float] = None
