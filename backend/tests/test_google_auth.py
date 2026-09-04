import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from app.main import app
from app.core.config import settings
from app.core.database import init_db


@pytest.mark.asyncio
async def test_google_auth_missing_credential():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/google", json={"credential": "   "})
        assert resp.status_code == 400
        assert "credential token is required" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_google_auth_token_rejected_by_google():
    transport = ASGITransport(app=app)
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(status_code=400, json=lambda: {"error_description": "Invalid Value"})
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/google", json={"credential": "fake_invalid_jwt_token"})
            assert resp.status_code == 400
            assert "Invalid Google token" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_google_auth_unverified_email():
    transport = ASGITransport(app=app)
    mock_google_user = {
        "aud": settings.GOOGLE_CLIENT_ID,
        "email": "unverified@example.com",
        "email_verified": False,
        "name": "Unverified User"
    }
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(status_code=200, json=lambda: mock_google_user)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/google", json={"credential": "valid_token_unverified_email"})
            assert resp.status_code == 400
            assert "not verified" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_google_auth_success_new_workspace():
    await init_db()
    transport = ASGITransport(app=app)
    mock_google_user = {
        "aud": settings.GOOGLE_CLIENT_ID,
        "email": "developer.amrut@gmail.com",
        "email_verified": True,
        "name": "Amrut Dongre",
        "picture": "https://lh3.googleusercontent.com/a/default-user"
    }
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(status_code=200, json=lambda: mock_google_user)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/google", json={"credential": "valid_google_id_token"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "token" in data
            assert data["user"]["email"] == "developer.amrut@gmail.com"
            assert data["user"]["full_name"] == "Amrut Dongre"
            assert data["user"]["tier"] == "free"
