import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.main import app
from app.core.config import settings
from app.middleware import rate_limit as rate_limit_module


@pytest.fixture(autouse=True)
def configure_app(monkeypatch):
    settings.API_KEYS = "test_key,rapid_test,pro_test,ultra_test,burst_test"
    rate_limit_module.tokens.clear()
    app.router.on_startup.clear()

    async def fake_log_usage(api_key, endpoint, status_code):
        return None

    async def fake_get_pincode_info(pincode):
        if pincode == "560001":
            return {
                "pincode": "560001",
                "office_name": "Bangalore GPO",
                "district": "Bengaluru",
                "state": "Karnataka",
                "tier": "Urban",
                "serviceable": True,
                "lat": 12.9716,
                "lon": 77.5946,
            }
        if pincode == "560034":
            return {
                "pincode": "560034",
                "office_name": "HSR Layout",
                "district": "Bengaluru",
                "state": "Karnataka",
                "tier": "Urban",
                "serviceable": True,
                "lat": 12.9116,
                "lon": 77.6474,
            }
        return None

    async def fake_check_serviceability(origin, dest, payment_method="COD"):
        return {
            "distance_km": 12.5,
            "zone": "Local",
            "estimated_days": 1,
            "risk": "low",
            "recommended_action": "SHIP" if payment_method == "PREPAID" else "CONFIRM_CUSTOMER",
            "action_reason": "Mocked serviceability decision.",
            "disclaimer": "Mocked disclaimer.",
        }

    async def fake_get_nearby_pincodes(pincode, radius):
        return {"pincodes": ["560001", "560034"]}

    async def fake_get_usage_summary(api_key):
        return {
            "api_key": api_key,
            "plan": "free",
            "credits_remaining": 92,
            "credits_total": 100,
            "usage_this_month": 8,
        }

    monkeypatch.setattr("app.api.v1.endpoints.get_pincode_info", fake_get_pincode_info)
    monkeypatch.setattr("app.api.v1.endpoints.check_serviceability", fake_check_serviceability)
    monkeypatch.setattr("app.api.v1.endpoints.get_nearby_pincodes", fake_get_nearby_pincodes)
    monkeypatch.setattr("app.api.v1.endpoints.get_usage_summary", fake_get_usage_summary)
    monkeypatch.setattr("app.middleware.usage_tracking.log_usage", fake_log_usage)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_healthz_no_auth(client):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_pincode_requires_auth(client):
    response = await client.get("/v1/pincode/560001")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_pincode_rejects_wrong_key(client):
    response = await client.get("/v1/pincode/560001", headers={"X-API-Key": "wrong_key"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_pincode_accepts_valid_x_api_key(client):
    response = await client.get("/v1/pincode/560001", headers={"X-API-Key": "test_key"})
    assert response.status_code in {200, 404}
    assert response.status_code not in {401, 500}


@pytest.mark.asyncio
async def test_pincode_accepts_valid_x_rapidapi_key(client):
    response = await client.get("/v1/pincode/560001", headers={"X-RapidAPI-Key": "rapid_test"})
    assert response.status_code == 200
    assert response.json()["pincode"] == "560001"


@pytest.mark.asyncio
async def test_serviceability_returns_expected_fields(client):
    response = await client.post(
        "/v1/logistics/serviceability",
        headers={"X-API-Key": "test_key"},
        json={
            "origin_pincode": "110001",
            "destination_pincode": "560001",
            "payment_method": "COD",
        },
    )
    assert response.status_code == 200
    body = response.json()
    for field in [
        "distance_km",
        "zone",
        "estimated_days",
        "risk",
        "recommended_action",
        "action_reason",
        "disclaimer",
    ]:
        assert field in body


@pytest.mark.asyncio
async def test_whatsapp_check_returns_success(client):
    response = await client.post(
        "/v1/whatsapp/check",
        headers={"X-API-Key": "test_key"},
        json={"message": "560034 COD 1499", "origin_pincode": "110001"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["metadata"]["pincode"] == "560034"
    assert body["metadata"]["origin_pincode"] == "110001"


@pytest.mark.asyncio
async def test_rate_limit_returns_429_after_burst(client):
    headers = {"X-API-Key": "burst_test"}
    statuses = []
    for _ in range(6):
        response = await client.get("/v1/pincode/560001", headers=headers)
        statuses.append(response.status_code)
    assert statuses[:5] == [200, 200, 200, 200, 200]
    assert statuses[5] == 429


@pytest.mark.asyncio
async def test_usage_endpoint_returns_credits(client):
    response = await client.get("/v1/usage", headers={"X-API-Key": "pro_test"})
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "api_key": "pro_...test",
        "plan": "free",
        "credits_remaining": 92,
        "credits_total": 100,
        "usage_this_month": 8,
    }
