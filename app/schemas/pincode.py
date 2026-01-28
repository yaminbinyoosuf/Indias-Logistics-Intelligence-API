from pydantic import BaseModel

class PincodeResponse(BaseModel):
    pincode: str
    office_name: str
    district: str
    state: str
    tier: str
    serviceable: bool
    lat: float
    lon: float
