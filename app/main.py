

import os
import logging
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from app.api.v1.endpoints import router as v1_router
from app.middleware.api_key import api_key_auth
from app.middleware.rate_limit import rate_limiter

import asyncio
import asyncpg
import csv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI(
    title="India Logistics Intelligence API",
    version="1.0.0",
    description="Reduce RTO by validating pincodes, calculating distances, and checking serviceability before shipping.",
    openapi_tags=[
        {"name": "Pincode", "description": "Pincode validation and lookup"},
        {"name": "Logistics", "description": "Serviceability and distance calculation"},
        {"name": "WhatsApp", "description": "WhatsApp bot integration"}
    ]
)

# Serve static files (minimal UI)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

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
            # Split and run each statement (skip comments and empty)
            stmts = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
            for stmt in stmts:
                try:
                    await conn.execute(stmt)
                except Exception as stmt_err:
                    logging.error(f"Migration statement failed: {stmt}\nError: {stmt_err}")
                    raise
            logging.info("Migration completed: pincodes table created.")
        else:
            logging.info("pincodes table exists. No migration needed.")
        await conn.close()
    except Exception as e:
        logging.error(f"DB migration failed: {e}")
        raise

# --- Startup Data Ingestion Logic ---
PINCODE_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw", "all_india_pincode.csv")

def ingest_pincode_data_if_needed():
    """
    On startup, if pincodes table is empty, load CSV and insert data. Fail-fast if CSV missing.
    """
    # Use SQLAlchemy sync engine for ingestion
    url = DB_URL.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(url)
    with engine.connect() as conn:
        # Check if pincodes table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables WHERE table_name = 'pincodes'
            );
        """))
        if not result.scalar():
            logging.error("pincodes table does not exist for ingestion!")
            raise RuntimeError("pincodes table missing before ingestion.")
        # Check row count
        count = conn.execute(text("SELECT COUNT(*) FROM pincodes")).scalar()
        if count > 0:
            logging.info(f"Pincode data already present: {count} rows.")
            return
        # Fail-fast if CSV missing
        if not os.path.exists(PINCODE_CSV):
            logging.error(f"CSV file not found: {PINCODE_CSV}")
            raise SystemExit(1)
        logging.info("Pincode table empty, running ingestion...")
        inserted, skipped = 0, 0
        with open(PINCODE_CSV, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    # UPSERT logic (idempotent)
                    stmt = text('''
                        INSERT INTO pincodes (pincode, office_name, district, state, tier, serviceable, lat, lon, location)
                        VALUES (:pincode, :office_name, :district, :state, :tier, :serviceable, :lat, :lon, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)
                        ON CONFLICT (pincode) DO UPDATE SET
                            office_name=EXCLUDED.office_name,
                            district=EXCLUDED.district,
                            state=EXCLUDED.state,
                            tier=EXCLUDED.tier,
                            serviceable=EXCLUDED.serviceable,
                            lat=EXCLUDED.lat,
                            lon=EXCLUDED.lon,
                            location=EXCLUDED.location
                    ''')
                    conn.execute(stmt, {
                        "pincode": row["pincode"],
                        "office_name": row["office_name"],
                        "district": row["district"],
                        "state": row["state"],
                        "tier": row["tier"],
                        "serviceable": str(row["serviceable"]).lower() in ("true", "1", "yes"),
                        "lat": float(row["lat"]),
                        "lon": float(row["lon"]),
                    })
                    inserted += 1
                except Exception as e:
                    logging.error(f"DB error for pincode {row.get('pincode')}: {e}")
                    skipped += 1
        conn.commit()
        logging.info(f"Inserted/Updated: {inserted}, Skipped: {skipped}")

@app.on_event("startup")
async def startup_event():
    await run_startup_migrations()
    # Synchronously check and ingest data if needed
    ingest_pincode_data_if_needed()

# Healthcheck endpoint: always 200, supports GET and HEAD, no DB/Redis
from fastapi.responses import JSONResponse
from fastapi import Response

@app.api_route("/healthz", methods=["GET", "HEAD"], tags=["Health"])
async def healthz():
    return JSONResponse(content={"status": "ok"}, status_code=200)

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
