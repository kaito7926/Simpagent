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
    poll_loki_lines,
    register_and_login_user,
    require_smoke,
    submit_search_turn,
    unique_correlation_id,
    unique_email,
)


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_centralized_logging_captures_backend_and_kong_entries_for_admin_and_search_flows() -> None:
    require_smoke()

    async with httpx.AsyncClient(base_url=PUBLIC_BASE_URL, timeout=25.0, follow_redirects=True) as client:
        user_email = unique_email("log-smoke-user")
        user_password = "MatKhauBaoMatLogSmoke123"
        user_token = await register_and_login_user(
            client,
            email=user_email,
            password=user_password,
        )
        admin_token = await login(
            client,
            email=DEMO_ADMIN_EMAIL,
            password=DEMO_ADMIN_PASSWORD,
            correlation_id=unique_correlation_id("corr-log-admin-login"),
        )

        user_record = await find_admin_user_by_email(
            client,
            access_token=admin_token,
            email=user_email,
        )
        target_user_id = str(user_record["id"])

        search_correlation_id = unique_correlation_id("corr-log-search")
        admin_write_correlation_id = unique_correlation_id("corr-log-admin")
        conversation_id = uuid4()

        search_payload = await submit_search_turn(
            client,
            access_token=user_token,
            conversation_id=conversation_id,
            correlation_id=search_correlation_id,
            prompt="latest open source security updates",
        )
        assert_search_contract(search_payload)

        admin_write_response = await client.patch(
            f"/api/admin/users/{target_user_id}",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Correlation-Id": admin_write_correlation_id,
            },
            json={"is_active": False},
        )
        assert admin_write_response.status_code == 200
        assert admin_write_response.json()["changed_fields"] == ["is_active"]

    backend_access_lines = await poll_loki_lines(
        f'{{service="backend"}} |= "{search_correlation_id}" |= "\\"event\\":\\"http_request\\"" |= "{conversation_id}"'
    )
    assert any('"status_code":200' in line for line in backend_access_lines)

    backend_tool_lines = await poll_loki_lines(
        f'{{service="backend"}} |= "{search_correlation_id}" |= "\\"event\\":\\"tool_execution\\""'
    )
    assert any('"tool_name":"google_search"' in line for line in backend_tool_lines)

    backend_security_lines = await poll_loki_lines(
        f'{{service="backend"}} |= "{admin_write_correlation_id}" |= "\\"event\\":\\"security_event\\""'
    )
    assert any('"event_type":"admin_user_access_updated"' in line for line in backend_security_lines)

    kong_search_lines = await poll_loki_lines(f'{{service="kong"}} |= "{conversation_id}"')
    assert kong_search_lines

    kong_admin_lines = await poll_loki_lines(f'{{service="kong"}} |= "{target_user_id}"')
    assert kong_admin_lines
