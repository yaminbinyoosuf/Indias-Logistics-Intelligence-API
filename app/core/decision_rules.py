"""
India-specific RTO decision rules engine.

Rules determine shipping actions based on:
- Pincode validity
- Serviceability
- Zone classification
- Risk assessment
- Payment method (COD vs prepaid)

IMPORTANT: Rules are deterministic, explicit, and configurable.
No ML. No magic numbers without comments.
"""

from enum import Enum
from typing import Optional

class RecommendedAction(str, Enum):
    SHIP = "SHIP"
    CONFIRM_CUSTOMER = "CONFIRM_CUSTOMER"
    PREPAID_ONLY = "PREPAID_ONLY"
    DO_NOT_SHIP = "DO_NOT_SHIP"


def get_recommended_action(
    pincode_valid: bool,
    serviceable: bool,
    tier: str,  # "Urban", "Semi-Urban", "Rural"
    zone: str,  # "Metro", "Local", "Regional", "National", "Special"
    risk: str,  # "low", "medium", "high"
    distance_km: float,
    payment_method: str = "COD",  # "COD" or "PREPAID"
) -> tuple[RecommendedAction, str]:
    """
    Determine shipping action and reasoning.
    
    Returns:
        (RecommendedAction, reason_string)
    
    LOGIC (in priority order):
    1. Invalid pincode → DO_NOT_SHIP (always)
    2. Non-serviceable → DO_NOT_SHIP (always)
    3. Special zone + COD → PREPAID_ONLY (high logistics risk)
    4. Rural + long distance + COD → PREPAID_ONLY (low capacity + buyer hesitation)
    5. High risk + COD → CONFIRM_CUSTOMER (buyer contact required)
    6. Medium risk + COD → CONFIRM_CUSTOMER (risk-aware shipping)
    7. Low risk → SHIP (safe to proceed)
    """

    # Rule 1: Invalid pincode = stop
    if not pincode_valid:
        return (
            RecommendedAction.DO_NOT_SHIP,
            "Pincode does not exist in India Post database."
        )

    # Rule 2: Non-serviceable = stop
    if not serviceable:
        return (
            RecommendedAction.DO_NOT_SHIP,
            "Destination is not serviceable. Check with your courier partner."
        )

    # Rule 3: Special zones (NE, J&K, islands) + COD = risky, require prepaid
    if zone == "Special" and payment_method == "COD":
        return (
            RecommendedAction.PREPAID_ONLY,
            f"Special zone ({zone}) + COD = high cash handling risk. Accept prepaid only."
        )

    # Rule 4: Rural + long distance + COD = lower last-mile penetration
    # Distance threshold: >500km is "long distance" for rural areas
    if tier == "Rural" and distance_km > 500 and payment_method == "COD":
        return (
            RecommendedAction.PREPAID_ONLY,
            f"Remote rural area ({distance_km:.0f}km) + COD = low delivery success rate. Request prepaid."
        )

    # Rule 5: High risk + COD = require customer confirmation
    if risk == "high" and payment_method == "COD":
        return (
            RecommendedAction.CONFIRM_CUSTOMER,
            f"High logistics risk ({zone} zone, {tier} tier). Confirm customer via call/OTP before dispatch."
        )

    # Rule 6: Medium risk + COD = recommend confirmation
    if risk == "medium" and payment_method == "COD":
        return (
            RecommendedAction.CONFIRM_CUSTOMER,
            f"Medium logistics risk ({zone} zone). Recommended: call customer to confirm address & payment."
        )

    # Rule 7: Low risk or prepaid = safe to ship
    if risk == "low" or payment_method == "PREPAID":
        return (
            RecommendedAction.SHIP,
            f"Serviceable area, {risk} logistics risk. Safe to ship."
        )

    # Fallback (should not reach here)
    return (
        RecommendedAction.CONFIRM_CUSTOMER,
        "Uncertain case. Please review order details."
    )


def get_seller_safe_disclaimer() -> str:
    """
    Disclaimer to protect seller from false confidence.
    Must be shown with every decision.
    """
    return (
        "⚠️ DISCLAIMER:\n"
        "This tool reduces LOGISTICS-driven RTO only.\n"
        "It does NOT account for:\n"
        "• Buyer intent / change of mind\n"
        "• COD payment refusal\n"
        "• Address/phone quality issues\n"
        "• Packaging/operational failures\n\n"
        "Use as a pre-shipment check, not a guarantee."
    )
