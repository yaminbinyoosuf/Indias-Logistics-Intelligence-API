"""
Credit and usage tracking system for sellers.

Simple model:
- Each API call consumes 1 credit
- Seller is blocked if credits = 0
- Usage is logged per seller for future billing integration

No complex billing logic yet. Just hooks.
"""

from calendar import monthrange
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy import func

Base = declarative_base()


class SellerCredit(Base):
    """Track credits per seller (API key)."""
    __tablename__ = "seller_credits"
    
    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(128), unique=True, index=True, nullable=False)
    credits_remaining = Column(Float, default=0, nullable=False)
    credits_total = Column(Float, default=0, nullable=False)
    plan = Column(String(50), default="free")  # free, pro, ultra
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UsageLog(Base):
    """Log each API call for audit and future billing."""
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(128), index=True, nullable=False)
    endpoint = Column(String(255), nullable=False)
    credits_consumed = Column(Float, default=1.0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    response_status = Column(Integer, nullable=True)  # 200, 404, etc.


# Default credits per plan
PLAN_CREDITS = {
    "free": 100,  # 100 checks/month
    "pro": 5000,  # 5000 checks/month
    "ultra": 50000,  # 50000 checks/month
}


def get_plan_for_api_key(api_key: str) -> str:
    if api_key.startswith("ultra_"):
        return "ultra"
    if api_key.startswith("pro_"):
        return "pro"
    return "free"


async def ensure_seller_credit(api_key: str) -> SellerCredit:
    """Ensure a seller credit record exists for the given API key."""
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        result = await session.execute(
            select(SellerCredit).where(SellerCredit.api_key == api_key)
        )
        seller = result.scalar_one_or_none()
        if seller:
            return seller

        plan = get_plan_for_api_key(api_key)
        total = PLAN_CREDITS[plan]
        seller = SellerCredit(
            api_key=api_key,
            credits_remaining=total,
            credits_total=total,
            plan=plan,
        )
        session.add(seller)
        await session.commit()
        await session.refresh(seller)
        return seller


async def deduct_credit(api_key: str, amount: float = 1.0) -> bool:
    """
    Deduct credit from seller.
    Return True if successful, False if insufficient credits.
    """
    from app.db.session import SessionLocal
    async with SessionLocal() as session:
        await ensure_seller_credit(api_key)
        # Check current credits
        result = await session.execute(
            select(SellerCredit).where(SellerCredit.api_key == api_key)
        )
        seller = result.scalar_one_or_none()
        
        if not seller or seller.credits_remaining < amount:
            return False
        
        # Deduct
        seller.credits_remaining -= amount
        await session.commit()
        return True


async def log_usage(api_key: str, endpoint: str, status_code: int = 200):
    """Log API usage for audit."""
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        await ensure_seller_credit(api_key)
        log = UsageLog(
            api_key=api_key,
            endpoint=endpoint,
            credits_consumed=1.0,
            response_status=status_code
        )
        session.add(log)
        await session.commit()


async def get_credits_remaining(api_key: str) -> float:
    """Get remaining credits for a seller."""
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        await ensure_seller_credit(api_key)
        result = await session.execute(
            select(SellerCredit).where(SellerCredit.api_key == api_key)
        )
        seller = result.scalar_one_or_none()
        return seller.credits_remaining if seller else 0.0


async def get_usage_summary(api_key: str) -> dict:
    """Return plan, quota, and current-month usage for an API key."""
    from app.db.session import SessionLocal

    seller = await ensure_seller_credit(api_key)

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day = monthrange(now.year, now.month)[1]
    month_end = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)

    async with SessionLocal() as session:
        result = await session.execute(
            select(func.count(UsageLog.id)).where(
                UsageLog.api_key == api_key,
                UsageLog.timestamp >= month_start,
                UsageLog.timestamp <= month_end,
            )
        )
        usage_this_month = int(result.scalar_one() or 0)

    credits_remaining = max(int(seller.credits_total - usage_this_month), 0)
    return {
        "api_key": api_key,
        "plan": seller.plan,
        "credits_remaining": credits_remaining,
        "credits_total": int(seller.credits_total),
        "usage_this_month": usage_this_month,
    }
