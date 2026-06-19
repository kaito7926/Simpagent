from __future__ import annotations

import pytest

from app.core.config import Settings


@pytest.mark.asyncio
async def test_register_accepts_generic_response(client) -> None:
    response = await client.post(
        "/api/auth/register",
        headers={"Origin": "http://localhost:3000"},
        json={"email": "student@example.com", "password": "matkhau-bao-mat-123"},
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "accepted"


@pytest.mark.asyncio
async def test_register_requires_invite_code_when_configured(client, app) -> None:
    configured = Settings(
        app_env="development",
        database_url="postgresql+psycopg://postgres:postgres@postgres-test:5432/simpagent_test",
        allowed_origins=["http://localhost:3000"],
        registration_invite_code="expected-invite",
    )
    app.state.settings = configured

    denied = await client.post(
        "/api/auth/register",
        headers={"Origin": "http://localhost:3000"},
        json={
            "email": "invite-denied@example.com",
            "password": "matkhau-bao-mat-123",
            "invite_code": "wrong-invite",
        },
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "registration_invite_required"

    accepted = await client.post(
        "/api/auth/register",
        headers={"Origin": "http://localhost:3000"},
        json={
            "email": "invite-accepted@example.com",
            "password": "matkhau-bao-mat-123",
            "invite_code": "expected-invite",
        },
    )
    assert accepted.status_code == 202
