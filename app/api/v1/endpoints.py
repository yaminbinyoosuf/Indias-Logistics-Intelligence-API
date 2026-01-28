from fastapi import APIRouter, Depends, HTTPException, Query, Header
from app.schemas.pincode import PincodeResponse
from app.schemas.logistics import ServiceabilityRequest, ServiceabilityResponse, NearbyPincodesResponse
from app.db.crud import (
    get_pincode_info,
    check_serviceability,
    get_nearby_pincodes
)

router = APIRouter()


@router.get(
    "/pincode/{pincode}",
    response_model=PincodeResponse,
    tags=["Pincode"],
    summary="Validate and lookup Indian pincode",
    responses={
        200: {"description": "Pincode found"},
        404: {"description": "Pincode not found"}
    },
    description="Returns office name, district, state, lat/lon, tier, and serviceability for a given Indian pincode.",
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "curl",
                "source": "curl -H 'X-API-Key: test_key' http://localhost:8000/v1/pincode/560001"
            }
        ]
    }
)
async def pincode_lookup(pincode: str, x_api_key: str = Header(..., alias="X-API-Key")):
    result = await get_pincode_info(pincode)
    if not result:
        raise HTTPException(status_code=404, detail="Pincode not found")
    return result


@router.post(
    "/logistics/serviceability",
    response_model=ServiceabilityResponse,
    tags=["Logistics"],
    summary="Check serviceability and calculate distance",
    description="Returns distance, zone, ETA, and risk for origin/destination pincodes.",
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "curl",
                "source": "curl -X POST -H 'Content-Type: application/json' -H 'X-API-Key: test_key' -d '{\"origin_pincode\": \"110001\", \"destination_pincode\": \"560001\"}' http://localhost:8000/v1/logistics/serviceability"
            }
        ]
    }
)
async def logistics_serviceability(payload: ServiceabilityRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    return await check_serviceability(payload.origin_pincode, payload.destination_pincode)


@router.get(
    "/pincode/nearby",
    response_model=NearbyPincodesResponse,
    tags=["Pincode"],
    summary="Find nearby pincodes within radius (km)",
    description="Returns a list of pincodes within the given radius (km) of the specified pincode.",
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "curl",
                "source": "curl -H 'X-API-Key: test_key' 'http://localhost:8000/v1/pincode/nearby?pincode=560001&radius=5'"
            }
        ]
    }
)
async def nearby_pincodes(pincode: str = Query(...), radius: float = Query(...), x_api_key: str = Header(..., alias="X-API-Key")):
    return await get_nearby_pincodes(pincode, radius)
