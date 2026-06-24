from pydantic import BaseModel


class GeocodeRequest(BaseModel):
    address: str


class GeocodeResponse(BaseModel):
    lat: float
    lon: float
    name: str
