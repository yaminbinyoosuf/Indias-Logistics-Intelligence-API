# India Logistics Intelligence API

Production-ready FastAPI backend to reduce e-commerce RTO by validating pincodes, calculating distances, and checking serviceability before shipping.

## Features
- Indian pincode validation & enrichment
- Distance & zone calculation (PostGIS)
- Nearby pincodes for ONDC sellers
- API key auth, rate limiting, Redis caching
- Dockerized, deployable to Render/Railway

## Local Setup

```bash
git clone <repo>
cd india-logistics-api
docker-compose up --build
# In another terminal, run data ingestion:
docker-compose exec api python scripts/ingest_pincode_data.py
```

## Deployment
- Push to Render or Railway (Postgres + Redis add-ons)
- Set DATABASE_URL and REDIS_URL env vars

## RapidAPI Integration
- Import OpenAPI spec
- Set up API key header: `X-API-Key`
- Use sample curl requests

## Pricing Plan
See pricing_plan.md
