from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class OrderTripRequest(BaseModel):
    user_id: str
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    end_address: Optional[str] = None


class TripResponse(BaseModel):
    trip_id: int
    distance_m: int
    duration_s: int
    geometry: List[List[float]]


class TripListItem(BaseModel):
    id: int
    start_address: Optional[str]
    end_address: Optional[str]
    distance_m: Optional[int]
    duration_s: Optional[int]
    status: str
    created_at: datetime
