"""
WhatsApp bot message parser and response formatter.

INPUT FORMAT (simple, seller-friendly):
"560034 COD 1499"
"560034 PREPAID 1499"
"560034"  (defaults to COD, no value check)

PARSING:
1. Extract pincode
2. Extract payment method (COD/PREPAID)
3. Extract order value (optional, for future COD limit checks)

OUTPUT:
Human-readable WhatsApp message with emojis.
"""

import re
from typing import Optional, Tuple

class WhatsAppBotParser:
    """Parse WhatsApp message into order details."""
    
    @staticmethod
    def parse_message(message: str) -> Tuple[Optional[str], str, Optional[float]]:
        """
        Parse seller's WhatsApp message.
        
        Input: "560034 COD 1499" or "560034" or "560034 PREPAID"
        
        Returns:
            (pincode, payment_method, order_value)
        
        pincode: 6-digit pincode
        payment_method: "COD" or "PREPAID" (default: "COD")
        order_value: order amount in INR (optional, default: None)
        """
        message = message.strip().upper()
        
        # Split by spaces
        parts = message.split()
        
        if not parts:
            return None, "COD", None
        
        # First part should be pincode (6 digits)
        pincode = parts[0]
        if not re.match(r'^\d{6}$', pincode):
            return None, "COD", None
        
        # Payment method (COD/PREPAID), default COD
        payment_method = "COD"
        if len(parts) > 1 and parts[1] in ["COD", "PREPAID"]:
            payment_method = parts[1]
        
        # Order value (optional)
        order_value = None
        if len(parts) > 2:
            try:
                order_value = float(parts[2])
            except ValueError:
                pass
        
        return pincode, payment_method, order_value


class WhatsAppResponseFormatter:
    """Format API response into WhatsApp-friendly message."""
    
    @staticmethod
    def format_response(
        recommended_action: str,
        action_reason: str,
        distance_km: float,
        zone: str,
        estimated_days: int,
        risk: str,
    ) -> str:
        """
        Convert API response to human-readable WhatsApp message.
        
        Actions:
        - SHIP → ✅
        - CONFIRM_CUSTOMER → ⚠️
        - PREPAID_ONLY → 💳
        - DO_NOT_SHIP → ❌
        """
        
        action_emoji = {
            "SHIP": "✅",
            "CONFIRM_CUSTOMER": "⚠️",
            "PREPAID_ONLY": "💳",
            "DO_NOT_SHIP": "❌"
        }.get(recommended_action, "❓")
        
        # Build message
        message = f"{action_emoji} {recommended_action}\n\n"
        message += f"📍 Zone: {zone}\n"
        message += f"📏 Distance: {distance_km:.0f}km\n"
        message += f"⏱️ ETA: ~{estimated_days} days\n"
        message += f"⚡ Risk: {risk}\n\n"
        message += f"💡 Action: {action_reason}\n\n"
        message += "⚠️ This tool checks logistics only.\n"
        message += "Not responsible for buyer intent/COD refusal."
        
        return message
    
    @staticmethod
    def format_error(error_type: str, error_detail: str = "") -> str:
        """Format error messages."""
        if error_type == "invalid_pincode":
            return (
                "❌ INVALID PINCODE\n\n"
                f"'{error_detail}' is not a valid Indian pincode.\n"
                "Please check and try again.\n\n"
                "Format: 6 digits (e.g., 560034)"
            )
        elif error_type == "invalid_format":
            return (
                "❌ INVALID FORMAT\n\n"
                "Usage: <pincode> [COD/PREPAID] [amount]\n\n"
                "Examples:\n"
                "560034\n"
                "560034 COD\n"
                "560034 PREPAID 1499"
            )
        elif error_type == "no_credits":
            return (
                "❌ OUT OF CREDITS\n\n"
                "You have 0 credits remaining.\n"
                "Please upgrade your plan to continue."
            )
        else:
            return "❌ Error processing request. Please try again."
