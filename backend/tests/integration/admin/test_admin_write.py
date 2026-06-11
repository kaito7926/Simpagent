from __future__ import annotations

from sqlalchemy import select

from app.models.account import User
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
