import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.security import verify_api_key

PUBLIC_EXACT_PATHS = {"/", "/docs", "/openapi.json", "/redoc", "/healthz"}
PUBLIC_PREFIX_PATHS = ("/static",)


async def api_key_auth(request: Request, call_next):
    path = request.url.path
    if path in PUBLIC_EXACT_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIX_PATHS):
        return await call_next(request)

    api_key = request.headers.get("X-RapidAPI-Key") or request.headers.get("X-API-Key")
    logging.warning(f"[API-KEY-MW] Incoming headers: {dict(request.headers)}")
    logging.warning(f"[API-KEY-MW] Extracted API key: '{api_key}' (valid: {settings.API_KEYS})")

    if not api_key or not verify_api_key(api_key, settings.API_KEYS):
        logging.warning(f"[API-KEY-MW] Invalid or missing API key for path {path}")
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API key"},
        )

    request.state.api_key = api_key
    response = await call_next(request)
    return response
