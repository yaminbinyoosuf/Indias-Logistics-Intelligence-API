from pydantic import BaseModel
from typing import List

class ServiceabilityRequest(BaseModel):
    origin_pincode: str
    destination_pincode: str

class ServiceabilityResponse(BaseModel):
    distance_km: float
    zone: str
    estimated_days: int
    risk: str

class NearbyPincodesResponse(BaseModel):
    pincodes: List[str]
