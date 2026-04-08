# India Logistics Intelligence API

Reduce RTO (Return to Origin) losses by validating Indian pincodes, checking courier serviceability, and getting shipping decisions before you dispatch.

## Features
- Validate any Indian pincode with enrichment data
- Check COD and prepaid serviceability between origin and destination
- Get distance, zone, ETA, and risk scoring
- Decision output: `SHIP`, `CONFIRM_CUSTOMER`, `PREPAID_ONLY`, `DO_NOT_SHIP`
- WhatsApp bot flow for fast seller checks
- Find pincodes within a radius for ONDC and courier coverage use cases
- API key auth, Redis caching, rate limiting, and usage visibility

## Quick Start

### Via RapidAPI
Subscribe on RapidAPI, copy your API key, and call the endpoints with either `X-RapidAPI-Key` or `X-API-Key`.

### Run Locally
```bash
git clone https://github.com/yaminbinyoosuf/Indias-Logistics-Intelligence-API
cd Indias-Logistics-Intelligence-API
cp .env.example .env
docker-compose up --build
```

API: `http://localhost:8000`  
Docs: `http://localhost:8000/docs`

## API Reference

### GET /v1/pincode/{pincode}
Headers: `X-RapidAPI-Key: YOUR_KEY`

### POST /v1/logistics/serviceability
Headers: `X-RapidAPI-Key: YOUR_KEY`

```json
{
  "origin_pincode": "110001",
  "destination_pincode": "560001",
  "payment_method": "COD"
}
```

### POST /v1/whatsapp/check
Headers: `X-RapidAPI-Key: YOUR_KEY`

```json
{
  "message": "560034 COD 1499",
  "origin_pincode": "110001"
}
```

### GET /v1/pincode/nearby?pincode=560001&radius=10
Headers: `X-RapidAPI-Key: YOUR_KEY`

### GET /v1/usage
Headers: `X-RapidAPI-Key: YOUR_KEY`

## Pricing

| Plan | Calls/month | Price |
|------|-------------|-------|
| Free | 100 | $0 |
| Pro | 5,000 | $9/mo |
| Ultra | 50,000 | $29/mo |

## Local Verification

```bash
curl http://localhost:8000/healthz
curl -H "X-API-Key: test_key" http://localhost:8000/v1/pincode/560001
curl -H "X-RapidAPI-Key: test_key" http://localhost:8000/v1/usage
pytest tests/
```

## Deployment

### Render.com
1. Push this repository to GitHub.
2. Create a new Blueprint deploy in Render and point it to this repo.
3. Render will read `render.yaml`, create Postgres and Redis, and build the API image.
4. Set `API_KEYS` manually in the Render dashboard before first production traffic.

### RapidAPI
1. Deploy the API publicly on Render.
2. Import `https://your-render-service.onrender.com/openapi.json` into RapidAPI.
3. Configure auth to forward `X-RapidAPI-Key` to the backend.
4. Add example requests for `/v1/pincode/{pincode}`, `/v1/logistics/serviceability`, `/v1/whatsapp/check`, and `/v1/usage`.
