import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_read_root(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "Welcome" in response.json()["message"]


async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
