from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from tests.smoke._helpers import (
    DEMO_ADMIN_EMAIL,
    DEMO_ADMIN_PASSWORD,
    PUBLIC_BASE_URL,
    assert_search_contract,
    find_admin_user_by_email,
    login,
    register_and_login_user,
    require_smoke,
    submit_search_turn,
    unique_correlation_id,
    unique_email,
)


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_public_stack_admin_flow_covers_search_evidence_and_role_changes() -> None:
    require_smoke()

    async with httpx.AsyncClient(base_url=PUBLIC_BASE_URL, timeout=25.0, follow_redirects=True) as client:
        user_email = unique_email("admin-smoke-user")
        user_password = "MatKhauBaoMatAdminSmoke123"
        user_token = await register_and_login_user(
            client,
            email=user_email,
            password=user_password,
        )

        search_correlation_id = unique_correlation_id("corr-smk-search")
        denied_correlation_id = unique_correlation_id("corr-smk-deny")
        promote_correlation_id = unique_correlation_id("corr-smk-promote")
        conversation_id = uuid4()

        search_payload = await submit_search_turn(
            client,
            access_token=user_token,
            conversation_id=conversation_id,
            correlation_id=search_correlation_id,
            prompt="latest public cloud security headlines",
        )
        assert_search_contract(search_payload)

        denied_response = await client.get(
            "/api/admin/users",
            headers={
                "Authorization": f"Bearer {user_token}",
                "X-Correlation-Id": denied_correlation_id,
            },
        )
        assert denied_response.status_code == 403
        assert denied_response.json()["error"]["code"] == "admin_role_required"

        admin_token = await login(
            client,
            email=DEMO_ADMIN_EMAIL,
            password=DEMO_ADMIN_PASSWORD,
            correlation_id=unique_correlation_id("corr-smk-admin-login"),
        )

        user_record = await find_admin_user_by_email(
            client,
            access_token=admin_token,
            email=user_email,
        )

        users_response = await client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"limit": 100, "offset": 0},
        )
        assert users_response.status_code == 200
        assert any(item["email"] == user_email for item in users_response.json()["items"])

        events_response = await client.get(
            "/api/admin/security-events",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"limit": 100, "offset": 0},
        )
        assert events_response.status_code == 200
        assert any(
            item["correlation_id"] == denied_correlation_id
            and item["event_type"] == "admin_access_denied"
            for item in events_response.json()["items"]
        )

        tools_response = await client.get(
            "/api/admin/tool-executions",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"limit": 100, "offset": 0},
        )
        assert tools_response.status_code == 200
        assert any(
            item["correlation_id"] == search_correlation_id
            and item["tool_name"] == "google_search"
            for item in tools_response.json()["items"]
        )

        metrics_response = await client.get(
            "/api/admin/metrics",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert metrics_response.status_code == 200
        metrics_payload = metrics_response.json()
        assert metrics_payload["users_total"] >= 2
        assert metrics_payload["security_events_total"] >= 1
        assert metrics_payload["tool_executions_total"] >= 1

        orchestration_response = await client.get(
            "/api/admin/orchestration",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert orchestration_response.status_code == 200
        assert orchestration_response.json()["trusted_supervisor_enabled"] is False

        trusted_supervisor_response = await client.patch(
            "/api/admin/orchestration/trusted-supervisor",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Correlation-Id": unique_correlation_id("corr-smk-supervisor"),
            },
            json={"enabled": True},
        )
        assert trusted_supervisor_response.status_code == 200
        assert trusted_supervisor_response.json()["trusted_supervisor_enabled"] is True

        promote_response = await client.patch(
            f"/api/admin/users/{user_record['id']}",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Correlation-Id": promote_correlation_id,
            },
            json={"role": "admin"},
        )
        assert promote_response.status_code == 200
        assert promote_response.json()["changed_fields"] == ["role", "scopes"]
        assert promote_response.json()["user"]["role"] == "admin"

        stale_me = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert stale_me.status_code == 401
        assert stale_me.json()["error"]["code"] == "stale_token"
