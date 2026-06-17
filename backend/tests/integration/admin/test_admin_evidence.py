from __future__ import annotations

from sqlalchemy import select

from app.models.evidence import SecurityEvent
from app.services.gateway_evidence import GatewayEvidenceService
from tests.integration.search._helpers import create_user, issue_token


async def test_admin_users_requires_admin_role_and_scope(client, db_session, settings) -> None:
    user = await create_user(
        db_session,
        email="ordinary@example.test",
        scopes=["chat:read", "chat:write"],
        role="user",
    )
    await db_session.commit()

    token = issue_token(user=user, scopes=["chat:read", "chat:write"], settings=settings)
    response = await client.get(
        "/api/admin/users",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Correlation-Id": "corr-admin-users-denied",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "admin_role_required"

    await db_session.rollback()
    denial = (
        await db_session.execute(
            select(SecurityEvent).where(SecurityEvent.correlation_id == "corr-admin-users-denied")
        )
    ).scalar_one()
    assert denial.event_type == "admin_access_denied"


async def test_admin_endpoints_return_bounded_evidence_for_admin(client, db_session, settings) -> None:
    admin = await create_user(
        db_session,
        email="admin-reader@example.test",
        scopes=["chat:read", "admin:read"],
        role="admin",
    )
    ordinary = await create_user(
        db_session,
        email="recent-user@example.test",
        scopes=["chat:read"],
        role="user",
    )
    await db_session.commit()

    token = issue_token(user=admin, scopes=["chat:read", "admin:read"], settings=settings)

    users_response = await client.get(
        "/api/admin/users?limit=10&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    events_response = await client.get(
        "/api/admin/security-events?limit=10&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    tools_response = await client.get(
        "/api/admin/tool-executions?limit=10&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    metrics_response = await client.get(
        "/api/admin/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert users_response.status_code == 200
    users_payload = users_response.json()
    assert users_payload["items"]
    assert any(item["id"] == str(ordinary.id) for item in users_payload["items"])
    assert "password_hash" not in users_response.text

    assert events_response.status_code == 200
    assert "items" in events_response.json()

    assert tools_response.status_code == 200
    assert "items" in tools_response.json()

    assert metrics_response.status_code == 200
    metrics_payload = metrics_response.json()
    assert metrics_payload["users_total"] >= 2


async def test_gateway_only_evidence_is_separate_from_security_event_rows(
    client,
    db_session,
    settings,
) -> None:
    admin = await create_user(
        db_session,
        email="gateway-admin@example.test",
        scopes=["chat:read", "admin:read"],
        role="admin",
    )
    await db_session.commit()

    gateway_page = GatewayEvidenceService.from_kong_config("kong/kong.yml").list_evidence(
        limit=10,
        offset=0,
    )
    token = issue_token(user=admin, scopes=["chat:read", "admin:read"], settings=settings)
    events_response = await client.get(
        "/api/admin/security-events?limit=100&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert events_response.status_code == 200
    security_event_payload = events_response.json()
    assert gateway_page.items
    assert any(item.evidence_type == "rate_limit" for item in gateway_page.items)
    assert any(item.evidence_type == "request_size" for item in gateway_page.items)
    assert all(item.source == "kong_config" for item in gateway_page.items)
    assert all(
        item["event_type"] not in {"gateway_rate_limited", "gateway_request_too_large"}
        for item in security_event_payload["items"]
    )
    assert "security_event" not in gateway_page.model_dump_json()
