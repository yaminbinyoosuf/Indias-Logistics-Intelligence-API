
from fastapi import FastAPI, Request
from app.api.v1.endpoints import router as v1_router
from app.middleware.api_key import api_key_auth
from app.middleware.rate_limit import rate_limiter
import logging
import time
import uuid

app = FastAPI(
    title="India Logistics Intelligence API",
    version="1.0.0",
    description="Reduce RTO by validating pincodes, calculating distances, and checking serviceability before shipping.",
    openapi_tags=[
        {"name": "Pincode", "description": "Pincode validation and lookup"},
        {"name": "Logistics", "description": "Serviceability and distance calculation"}
    ]
)

app.include_router(v1_router, prefix="/v1")

# Structured logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    endpoint = request.url.path
    method = request.method
    response = None
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logging.info(f"[req_id={request_id}] {method} {endpoint} {response.status_code} {process_time:.2f}ms")
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logging.error(f"[req_id={request_id}] {method} {endpoint} ERROR {process_time:.2f}ms: {e}")
        raise

# Healthcheck endpoint
@app.get("/healthz", tags=["Health"])
async def healthz():
    return {"status": "ok"}

# OpenAPI endpoint for RapidAPI import
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi():
    return app.openapi()

# Middleware (order matters: API key first, then rate limit)
app.middleware("http")(api_key_auth)
app.middleware("http")(rate_limiter)

# Global HTTPException handler for clean JSON
from fastapi.responses import JSONResponse
from fastapi import HTTPException

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
