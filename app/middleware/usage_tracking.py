import asyncio
import logging

from fastapi import Request

from app.core.usage import log_usage

EXEMPT_LOG_PATHS = {"/", "/docs", "/openapi.json", "/redoc", "/healthz"}
EXEMPT_LOG_PREFIXES = ("/static",)


async def usage_tracker(request: Request, call_next):
    response = await call_next(request)

    path = request.url.path
    if path in EXEMPT_LOG_PATHS or any(path.startswith(prefix) for prefix in EXEMPT_LOG_PREFIXES):
        return response

    if 200 <= response.status_code < 300:
        api_key = request.headers.get("X-RapidAPI-Key") or request.headers.get("X-API-Key")
        if api_key:
            asyncio.create_task(_log_usage_safe(api_key, path, response.status_code))

    return response


async def _log_usage_safe(api_key: str, endpoint: str, status_code: int):
    try:
        await log_usage(api_key, endpoint, status_code)
    except Exception as exc:
        logging.warning(f"Usage tracking failed for {endpoint}: {exc}")
