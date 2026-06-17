from __future__ import annotations

from sqlalchemy import select

from app.models.account import User
from app.models.domain import AgentRuntimeSetting
from app.models.evidence import SecurityEvent
from app.schemas.auth import ADMIN_SCOPES
from tests.integration.search._helpers import create_user, issue_token


async def test_admin_scope_matrix_distinguishes_read_and_write(client, db_session, settings) -> None:
    target = await create_user(
        db_session,
        email="matrix-target@example.test",
        scopes=["chat:read", "chat:write"],
        role="user",
    )
    admin_reader = await create_user(
        db_session,
        email="admin-reader@example.test",
        scopes=["admin:read"],
        role="admin",
    )
    admin_writer = await create_user(
        db_session,
        email="admin-writer@example.test",
        scopes=["admin:write"],
        role="admin",
    )
    scoped_user = await create_user(
        db_session,
        email="scoped-user@example.test",
        scopes=["admin:read", "admin:write"],
        role="user",
    )
    await db_session.commit()

    reader_token = issue_token(user=admin_reader, scopes=["admin:read"], settings=settings)
    writer_token = issue_token(user=admin_writer, scopes=["admin:write"], settings=settings)
    scoped_user_token = issue_token(
        user=scoped_user,
        scopes=["admin:read", "admin:write"],
        settings=settings,
    )

    read_response = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert read_response.status_code == 200

    denied_write_response = await client.patch(
        f"/api/admin/users/{target.id}",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"is_active": False},
    )
    assert denied_write_response.status_code == 403
    assert denied_write_response.json()["error"]["code"] == "admin_scope_required"

    denied_read_response = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {writer_token}"},
    )
    assert denied_read_response.status_code == 403
    assert denied_read_response.json()["error"]["code"] == "admin_scope_required"

    allowed_write_response = await client.patch(
        f"/api/admin/users/{target.id}",
        headers={
            "Authorization": f"Bearer {writer_token}",
            "X-Correlation-Id": "corr-admin-write-matrix",
        },
        json={"is_active": False},
    )
    assert allowed_write_response.status_code == 200
    assert allowed_write_response.json()["changed_fields"] == ["is_active"]
    assert allowed_write_response.json()["user"]["is_active"] is False

    non_admin_response = await client.patch(
        f"/api/admin/users/{target.id}",
        headers={"Authorization": f"Bearer {scoped_user_token}"},
        json={"is_active": True},
    )
    assert non_admin_response.status_code == 403
    assert non_admin_response.json()["error"]["code"] == "admin_role_required"

    await db_session.rollback()
    await db_session.refresh(target)
    updated_target = (await db_session.execute(select(User).where(User.id == target.id))).scalar_one()
    assert updated_target.is_active is False

    admin_event = (
        await db_session.execute(
            select(SecurityEvent).where(SecurityEvent.correlation_id == "corr-admin-write-matrix")
        )
    ).scalar_one()
    assert admin_event.event_type == "admin_user_access_updated"


async def test_admin_write_promotes_role_bundle_and_invalidates_stale_target_token(client, db_session, settings) -> None:
    admin = await create_user(
        db_session,
        email="promoter@example.test",
        scopes=["admin:read", "admin:write"],
        role="admin",
    )
    target = await create_user(
        db_session,
        email="promoted@example.test",
        scopes=["chat:read", "chat:write", "tool:websearch", "tool:python"],
        role="user",
    )
    await db_session.commit()

    admin_token = issue_token(user=admin, scopes=["admin:read", "admin:write"], settings=settings)
    stale_target_token = issue_token(
        user=target,
        scopes=["chat:read", "chat:write", "tool:websearch", "tool:python"],
        settings=settings,
    )

    response = await client.patch(
        f"/api/admin/users/{target.id}",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Correlation-Id": "corr-admin-promote",
        },
        json={"role": "admin"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["changed_fields"] == ["role", "scopes"]
    assert payload["user"]["role"] == "admin"
    assert payload["user"]["scopes"] == sorted(ADMIN_SCOPES)

    stale_me = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {stale_target_token}"},
    )
    assert stale_me.status_code == 401
    assert stale_me.json()["error"]["code"] == "stale_token"

    await db_session.rollback()
    await db_session.refresh(target)
    promoted_user = (await db_session.execute(select(User).where(User.id == target.id))).scalar_one()
    assert promoted_user.role == "admin"

    promotion_event = (
        await db_session.execute(
            select(SecurityEvent).where(SecurityEvent.correlation_id == "corr-admin-promote")
        )
    ).scalar_one()
    assert promotion_event.event_type == "admin_user_access_updated"


async def test_admin_write_blocks_self_mutation(client, db_session, settings) -> None:
    admin = await create_user(
        db_session,
        email="self-guard@example.test",
        scopes=["admin:write"],
        role="admin",
    )
    await db_session.commit()

    token = issue_token(user=admin, scopes=["admin:write"], settings=settings)
    response = await client.patch(
        f"/api/admin/users/{admin.id}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Correlation-Id": "corr-admin-self-denied",
        },
        json={"is_active": False},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "admin_self_mutation_forbidden"

    await db_session.rollback()
    denial_event = (
        await db_session.execute(
            select(SecurityEvent).where(SecurityEvent.correlation_id == "corr-admin-self-denied")
        )
    ).scalar_one()
    assert denial_event.event_type == "admin_write_denied"


async def test_admin_can_read_and_toggle_guardrail_safety_agent(client, db_session, settings) -> None:
    admin_reader = await create_user(
        db_session,
        email="guardrail-reader@example.test",
        scopes=["admin:read"],
        role="admin",
    )
    admin_writer = await create_user(
        db_session,
        email="guardrail-writer@example.test",
        scopes=["admin:write"],
        role="admin",
    )
    non_admin = await create_user(
        db_session,
        email="guardrail-user@example.test",
        scopes=["admin:read", "admin:write"],
        role="user",
    )
    await db_session.commit()

    reader_token = issue_token(user=admin_reader, scopes=["admin:read"], settings=settings)
    writer_token = issue_token(user=admin_writer, scopes=["admin:write"], settings=settings)
    non_admin_token = issue_token(user=non_admin, scopes=["admin:read", "admin:write"], settings=settings)

    read_response = await client.get(
        "/api/admin/orchestration",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert read_response.status_code == 200
    assert read_response.json() == {
        "guardrail_safety_enabled": True,
    }

    denied_response = await client.patch(
        "/api/admin/orchestration/guardrail",
        headers={"Authorization": f"Bearer {non_admin_token}"},
        json={"enabled": False},
    )
    assert denied_response.status_code == 403
    assert denied_response.json()["error"]["code"] == "admin_role_required"

    write_response = await client.patch(
        "/api/admin/orchestration/guardrail",
        headers={
            "Authorization": f"Bearer {writer_token}",
            "X-Correlation-Id": "corr-admin-guardrail-off",
        },
        json={"enabled": False},
    )
    assert write_response.status_code == 200
    assert write_response.json() == {
        "guardrail_safety_enabled": False,
    }

    await db_session.rollback()
    setting = await db_session.scalar(
        select(AgentRuntimeSetting).where(AgentRuntimeSetting.key == "guardrail_safety_agent")
    )
    assert setting is not None
    assert setting.enabled is False

    event = (
        await db_session.execute(
            select(SecurityEvent).where(SecurityEvent.correlation_id == "corr-admin-guardrail-off")
        )
    ).scalar_one()
    assert event.event_type == "guardrail_safety_toggled"


async def test_overview_and_orchestration_enforce_read_write_split_and_record_denials(
    client,
    db_session,
    settings,
) -> None:
    admin_reader = await create_user(
        db_session,
        email="overview-reader@example.test",
        scopes=["admin:read"],
        role="admin",
    )
    admin_writer = await create_user(
        db_session,
        email="overview-writer@example.test",
        scopes=["admin:write"],
        role="admin",
    )
    ordinary_user = await create_user(
        db_session,
        email="overview-user@example.test",
        scopes=["admin:read", "admin:write"],
        role="user",
    )
    await db_session.commit()

    reader_token = issue_token(user=admin_reader, scopes=["admin:read"], settings=settings)
    writer_token = issue_token(user=admin_writer, scopes=["admin:write"], settings=settings)
    ordinary_token = issue_token(
        user=ordinary_user,
        scopes=["admin:read", "admin:write"],
        settings=settings,
    )

    metrics_response = await client.get(
        "/api/admin/metrics",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert metrics_response.status_code == 200
    assert metrics_response.json()["users_total"] >= 3

    orchestration_response = await client.get(
        "/api/admin/orchestration",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert orchestration_response.status_code == 200
    assert set(orchestration_response.json()) == {"guardrail_safety_enabled"}

    denied_metrics_response = await client.get(
        "/api/admin/metrics",
        headers={
            "Authorization": f"Bearer {writer_token}",
            "X-Correlation-Id": "corr-admin-metrics-write-only-denied",
        },
    )
    assert denied_metrics_response.status_code == 403
    assert denied_metrics_response.json()["error"]["code"] == "admin_scope_required"

    denied_orchestration_response = await client.get(
        "/api/admin/orchestration",
        headers={
            "Authorization": f"Bearer {ordinary_token}",
            "X-Correlation-Id": "corr-admin-orchestration-user-denied",
        },
    )
    assert denied_orchestration_response.status_code == 403
    assert denied_orchestration_response.json()["error"]["code"] == "admin_role_required"

    denied_guardrail_write = await client.patch(
        "/api/admin/orchestration/guardrail",
        headers={
            "Authorization": f"Bearer {reader_token}",
            "X-Correlation-Id": "corr-admin-guardrail-read-only-denied",
        },
        json={"enabled": False},
    )
    assert denied_guardrail_write.status_code == 403
    assert denied_guardrail_write.json()["error"]["code"] == "admin_scope_required"

    await db_session.rollback()
    denial_events = (
        await db_session.execute(
            select(SecurityEvent).where(
                SecurityEvent.correlation_id.in_(
                    [
                        "corr-admin-metrics-write-only-denied",
                        "corr-admin-orchestration-user-denied",
                        "corr-admin-guardrail-read-only-denied",
                    ]
                )
            )
        )
    ).scalars().all()
    assert {event.correlation_id for event in denial_events} == {
        "corr-admin-metrics-write-only-denied",
        "corr-admin-orchestration-user-denied",
        "corr-admin-guardrail-read-only-denied",
    }
    assert all(event.event_type == "admin_access_denied" for event in denial_events)
    assert all("token" not in str(event.event_metadata).lower() for event in denial_events)
