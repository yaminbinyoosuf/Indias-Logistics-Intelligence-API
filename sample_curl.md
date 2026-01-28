# Sample curl requests

# 1. Validate pincode
curl -H "X-API-Key: <your-key>" http://localhost:8000/v1/pincode/560001

# 2. Serviceability
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: <your-key>" \
  -d '{"origin_pincode": "110001", "destination_pincode": "560001"}' \
  http://localhost:8000/v1/logistics/serviceability

# 3. Nearby pincodes
curl -H "X-API-Key: <your-key>" "http://localhost:8000/v1/pincode/nearby?pincode=560001&radius=5"
