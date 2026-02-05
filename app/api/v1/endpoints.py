from fastapi import APIRouter, Depends, HTTPException, Query, Header
from app.schemas.pincode import PincodeResponse
from app.schemas.logistics import ServiceabilityRequest, ServiceabilityResponse, NearbyPincodesResponse
from app.db.crud import (
    get_pincode_info,
    check_serviceability,
    get_nearby_pincodes
)
from app.utils.whatsapp_bot import WhatsAppBotParser, WhatsAppResponseFormatter
import logging

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
    description="Returns distance, zone, ETA, risk, and RECOMMENDED ACTION for origin/destination pincodes.",
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "curl",
                "source": "curl -X POST -H 'Content-Type: application/json' -H 'X-API-Key: test_key' -d '{\"origin_pincode\": \"110001\", \"destination_pincode\": \"560001\", \"payment_method\": \"COD\"}' http://localhost:8000/v1/logistics/serviceability"
            }
        ]
    }
)
async def logistics_serviceability(payload: ServiceabilityRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    payment_method = getattr(payload, 'payment_method', 'COD')
    return await check_serviceability(payload.origin_pincode, payload.destination_pincode, payment_method)


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


@router.post(
    "/whatsapp/check",
    tags=["WhatsApp"],
    summary="WhatsApp bot: parse message and return shipping decision",
    description="Input: seller message like '560034 COD 1499'. Output: human-readable decision.",
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "curl",
                "source": "curl -X POST -H 'Content-Type: application/json' -H 'X-API-Key: test_key' -d '{\"message\": \"560034 COD\"}' http://localhost:8000/v1/whatsapp/check"
            }
        ]
    }
)
async def whatsapp_check(
    message: dict,  # {"message": "560034 COD 1499"}
    x_api_key: str = Header(..., alias="X-API-Key")
):
    """
    Parse WhatsApp message and return shipping decision.
    
    Input message format:
    "560034" - pincode only (default COD)
    "560034 COD" - pincode + payment method
    "560034 COD 1499" - pincode + payment method + order value
    """
    try:
        msg_text = message.get("message", "").strip()
        
        # Parse message
        pincode, payment_method, order_value = WhatsAppBotParser.parse_message(msg_text)
        
        if not pincode:
            return {
                "success": False,
                "reply": WhatsAppResponseFormatter.format_error("invalid_format", msg_text)
            }
        
        # Get pincode info to check if valid
        pincode_info = await get_pincode_info(pincode)
        
        if not pincode_info:
            return {
                "success": False,
                "reply": WhatsAppResponseFormatter.format_error("invalid_pincode", pincode)
            }
        
        # Check serviceability (origin = pincode, destination = pincode)
        # This is simplified; a real seller would have their own origin
        serviceability = await check_serviceability(pincode, pincode, payment_method)
        
        # Format response
        reply = WhatsAppResponseFormatter.format_response(
            recommended_action=serviceability["recommended_action"],
            action_reason=serviceability["action_reason"],
            distance_km=0,  # Same location
            zone="Local",  # Same pincode
            estimated_days=1,
            risk="low"
        )
        
        return {
            "success": True,
            "reply": reply,
            "metadata": {
                "pincode": pincode,
                "payment_method": payment_method,
                "order_value": order_value
            }
        }
    
    except Exception as e:
        logging.error(f"WhatsApp bot error: {e}")
        return {
            "success": False,
            "reply": WhatsAppResponseFormatter.format_error("invalid_format")
        }

