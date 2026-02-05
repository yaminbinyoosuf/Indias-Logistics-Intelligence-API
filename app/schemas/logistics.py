from pydantic import BaseModel
from typing import List, Optional

class ServiceabilityRequest(BaseModel):
    origin_pincode: str
    destination_pincode: str
    payment_method: Optional[str] = "COD"  # COD or PREPAID

class ServiceabilityResponse(BaseModel):
    distance_km: float
    zone: str
    estimated_days: int
    risk: str
    recommended_action: str  # SHIP, CONFIRM_CUSTOMER, PREPAID_ONLY, DO_NOT_SHIP
    action_reason: str  # Why this action is recommended
    disclaimer: str  # Seller safeguard warning

class NearbyPincodesResponse(BaseModel):
    pincodes: List[str]
