"""
Credit and usage tracking system for sellers.

Simple model:
- Each API call consumes 1 credit
- Seller is blocked if credits = 0
- Usage is logged per seller for future billing integration

No complex billing logic yet. Just hooks.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

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


async def deduct_credit(api_key: str, amount: float = 1.0) -> bool:
    """
    Deduct credit from seller.
    Return True if successful, False if insufficient credits.
    """
    from app.db.session import SessionLocal
    from sqlalchemy import update

    async with SessionLocal() as session:
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
        result = await session.execute(
            select(SellerCredit).where(SellerCredit.api_key == api_key)
        )
        seller = result.scalar_one_or_none()
        return seller.credits_remaining if seller else 0.0
