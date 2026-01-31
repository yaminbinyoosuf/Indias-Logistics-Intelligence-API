from fastapi import Request, HTTPException
from app.core.config import settings
from app.core.security import verify_api_key

async def api_key_auth(request: Request, call_next):
    # Allow unauthenticated access to docs and openapi
    if request.url.path in ["/docs", "/openapi.json", "/redoc"]:
        return await call_next(request)
        import logging
        api_key = (
            request.headers.get("X-API-Key")
            or request.headers.get("X-RapidAPI-Key")
        )
        logging.warning(f"[API-KEY-MW] Incoming headers: {dict(request.headers)}")
        logging.warning(f"[API-KEY-MW] Extracted API key: '{api_key}' (valid: {settings.API_KEYS})")
        valid_keys = [k.strip() for k in settings.API_KEYS.split(",")]
        if not api_key or api_key not in valid_keys:
            logging.warning(f"[API-KEY-MW] Invalid or missing API key for path {request.url.path}")
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    response = await call_next(request)
    return response
