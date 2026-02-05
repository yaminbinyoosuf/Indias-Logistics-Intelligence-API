
from sqlalchemy.future import select
from sqlalchemy import text
from app.db.models import Pincode
from app.db.session import SessionLocal
from app.core.cache import cache_get, cache_set
from app.utils.geo import classify_zone, score_risk, estimate_eta
from app.core.decision_rules import get_recommended_action, get_seller_safe_disclaimer
import json

PINCODE_CACHE_VERSION = "v1"
SERVICEABILITY_CACHE_VERSION = "v1"

async def get_pincode_info(pincode: str):
    cache_key = f"{PINCODE_CACHE_VERSION}:pincode:{pincode}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)
    async with SessionLocal() as session:
        result = await session.execute(select(Pincode).where(Pincode.pincode == pincode))
        pin = result.scalar_one_or_none()
        if not pin:
            return None
        data = {
            "pincode": pin.pincode,
            "office_name": pin.office_name,
            "district": pin.district,
            "state": pin.state,
            "tier": pin.tier,
            "serviceable": pin.serviceable,
            "lat": pin.lat,
            "lon": pin.lon
        }
        await cache_set(cache_key, json.dumps(data), expire=60*60*24*30)  # 30 days
        return data

async def check_serviceability(origin: str, dest: str, payment_method: str = "COD"):
    """
    Check serviceability between two pincodes.
    Includes decision rules to recommend shipping action.
    """
    cache_key = f"{SERVICEABILITY_CACHE_VERSION}:serviceability:{origin}:{dest}:{payment_method}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)
    
    async with SessionLocal() as session:
        # Get both pincodes
        result = await session.execute(select(Pincode).where(Pincode.pincode.in_([origin, dest])))
        pins = {p.pincode: p for p in result.scalars()}
        
        # If either pincode missing, apply decision rules and return
        if origin not in pins or dest not in pins:
            recommended_action, reason = get_recommended_action(
                pincode_valid=False,
                serviceable=False,
                tier="Unknown",
                zone="Unknown",
                risk="high",
                distance_km=0,
                payment_method=payment_method
            )
            data = {
                "distance_km": 0,
                "zone": "Unknown",
                "estimated_days": 0,
                "risk": "high",
                "recommended_action": recommended_action.value,
                "action_reason": reason,
                "disclaimer": get_seller_safe_disclaimer()
            }
            await cache_set(cache_key, json.dumps(data), expire=60*60*24)
            return data
        
        orig = pins[origin]
        dst = pins[dest]
        
        # Calculate distance using PostGIS
        q = text("""
            SELECT ST_Distance(
                ST_SetSRID(ST_MakePoint(:lon1, :lat1), 4326)::geography,
                ST_SetSRID(ST_MakePoint(:lon2, :lat2), 4326)::geography
            ) / 1000 AS km
        """)
        res = await session.execute(q, {"lon1": orig.lon, "lat1": orig.lat, "lon2": dst.lon, "lat2": dst.lat})
        distance_km = float(res.scalar_one())
        
        zone = classify_zone(orig, dst, distance_km)
        risk = score_risk(orig, dst, distance_km, zone)
        eta = estimate_eta(zone)
        
        # Apply decision rules
        recommended_action, reason = get_recommended_action(
            pincode_valid=True,
            serviceable=dst.serviceable,  # Check destination serviceability
            tier=dst.tier,
            zone=zone,
            risk=risk,
            distance_km=distance_km,
            payment_method=payment_method
        )
        
        data = {
            "distance_km": round(distance_km, 2),
            "zone": zone,
            "estimated_days": eta,
            "risk": risk,
            "recommended_action": recommended_action.value,
            "action_reason": reason,
            "disclaimer": get_seller_safe_disclaimer()
        }
        await cache_set(cache_key, json.dumps(data), expire=60*60*24)  # 24h
        return data

async def get_nearby_pincodes(pincode: str, radius: float):
    cache_key = f"{PINCODE_CACHE_VERSION}:nearby:{pincode}:{radius}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)
    async with SessionLocal() as session:
        # Get center pincode
        result = await session.execute(select(Pincode).where(Pincode.pincode == pincode))
        center = result.scalar_one_or_none()
        if not center:
            raise ValueError("Invalid pincode")
        # Find all pincodes within radius (km)
        q = text("""
            SELECT pincode FROM pincodes
            WHERE ST_DWithin(
                location,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :meters
            )
        """)
        res = await session.execute(q, {"lon": center.lon, "lat": center.lat, "meters": radius * 1000})
        pincodes = [row[0] for row in res.fetchall() if row[0] != pincode]
        data = {"pincodes": pincodes}
        await cache_set(cache_key, json.dumps(data), expire=60*60*24*7)  # 7 days
        return data
