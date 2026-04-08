from fastapi import Request
from fastapi.responses import JSONResponse
import time
import logging
from app.core.config import settings

# In-memory token bucket (use Redis for distributed)
rate_limits = {
    "free": {"rate": 1, "burst": 5},
    "pro": {"rate": 10, "burst": 20},
    "ultra": {"rate": 50, "burst": 100}
}
tokens = {}

async def rate_limiter(request: Request, call_next):
    # Exempt /healthz from rate limiting
    if request.url.path in {"/", "/docs", "/openapi.json", "/redoc", "/healthz"} or request.url.path.startswith("/static"):
        return await call_next(request)

    api_key = request.headers.get("X-RapidAPI-Key") or request.headers.get("X-API-Key", "free")
    plan = "free"
    if api_key.startswith("pro_"):
        plan = "pro"
    elif api_key.startswith("ultra_"):
        plan = "ultra"
    now = int(time.time())
    bucket = tokens.setdefault(api_key, {"tokens": rate_limits[plan]["burst"], "last": now})
    elapsed = now - bucket["last"]
    # Token refill
    bucket["tokens"] = min(rate_limits[plan]["burst"], bucket["tokens"] + elapsed * rate_limits[plan]["rate"])
    bucket["last"] = now
    if bucket["tokens"] < 1:
        logging.warning(f"Rate limit exceeded for key {api_key}")
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please slow down."},
            headers={
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Plan": plan,
            },
        )
    bucket["tokens"] -= 1
    remaining = max(int(bucket["tokens"]), 0)
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Plan"] = plan
    return response
