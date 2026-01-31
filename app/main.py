

import os
import logging
import time
import uuid
from fastapi import FastAPI, Request
from app.api.v1.endpoints import router as v1_router
from app.middleware.api_key import api_key_auth
from app.middleware.rate_limit import rate_limiter

import asyncio
import asyncpg

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


# --- Startup DB migration runner ---
MIGRATION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations", "001_init.sql")
DB_URL = os.getenv("DATABASE_URL")

async def run_startup_migrations():
    if not DB_URL:
        logging.error("DATABASE_URL is not set. Cannot run migrations.")
        raise RuntimeError("DATABASE_URL is not set.")
    # Convert SQLAlchemy URL to asyncpg URL if needed
    url = DB_URL.replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(url)
        # Ensure PostGIS extension exists
        await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        # Check if pincodes table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'pincodes'
            );
        """)
        if not table_exists:
            logging.info("pincodes table not found. Running migrations/001_init.sql...")
            with open(MIGRATION_FILE, "r", encoding="utf-8") as f:
                sql = f.read()
            # Split and run each statement
            for stmt in [s.strip() for s in sql.split(';') if s.strip()]:
                await conn.execute(stmt)
            logging.info("Migration completed: pincodes table created.")
        else:
            logging.info("pincodes table exists. No migration needed.")
        await conn.close()
    except Exception as e:
        logging.error(f"DB migration failed: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    await run_startup_migrations()

# Healthcheck endpoint with DB/table readiness
@app.get("/healthz", tags=["Health"])
async def healthz():
    try:
        url = DB_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(url)
        # Check if pincodes table exists and is readable
        ready = await conn.fetchval("SELECT 1 FROM information_schema.tables WHERE table_name = 'pincodes'")
        if not ready:
            await conn.close()
            return {"status": "error", "detail": "pincodes table missing"}
        # Try a simple query
        await conn.fetchval("SELECT 1 FROM pincodes LIMIT 1")
        await conn.close()
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"/healthz DB check failed: {e}")
        return {"status": "error", "detail": str(e)}

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
