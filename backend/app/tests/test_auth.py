import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_signup_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": "testuser@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "testuser@example.com"
    assert "id" in data


async def test_signup_existing_user(client: AsyncClient):
    # First signup
    await client.post(
        "/api/v1/auth/signup",
        json={"email": "duplicate@example.com", "password": "password123"},
    )
    # Second signup
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": "duplicate@example.com", "password": "password123"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "A user with this email address already exists."


async def test_login_user(client: AsyncClient):
    # Create user
    await client.post(
        "/api/v1/auth/signup",
        json={"email": "login@example.com", "password": "password123"},
    )

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_invalid_credentials(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistent@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect email or password"
