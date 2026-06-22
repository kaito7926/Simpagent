from __future__ import annotations

import base64
import os
from pathlib import Path

from alembic import op
import sqlalchemy as sa

from app.security.message_encryption import MessageEncryptor

# revision identifiers, used by Alembic.
revision = "0005_encrypt_message_content"
down_revision = "0004_agent_runtime_settings"
branch_labels = None
depends_on = None


def _encryptor() -> MessageEncryptor:
    value = os.getenv("SIMPAGENT_MESSAGE_ENCRYPTION_KEY")
    if not value:
        file_path = os.getenv("SIMPAGENT_MESSAGE_ENCRYPTION_KEY_FILE")
        if file_path:
            candidate = Path(file_path)
            if candidate.exists():
                value = candidate.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError("SIMPAGENT_MESSAGE_ENCRYPTION_KEY or SIMPAGENT_MESSAGE_ENCRYPTION_KEY_FILE is required.")
    padding = "=" * ((4 - len(value) % 4) % 4)
    key = base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))
    return MessageEncryptor(key)


def upgrade() -> None:
    bind = op.get_bind()
    encryptor = _encryptor()
    rows = bind.execute(sa.text("SELECT id, content FROM messages")).mappings().all()
    for row in rows:
        content = row["content"]
        if content is None or MessageEncryptor.is_encrypted(content):
            continue
        bind.execute(
            sa.text("UPDATE messages SET content = :content WHERE id = :id"),
            {"id": row["id"], "content": encryptor.encrypt(content)},
        )


def downgrade() -> None:
    bind = op.get_bind()
    encryptor = _encryptor()
    rows = bind.execute(sa.text("SELECT id, content FROM messages")).mappings().all()
    for row in rows:
        content = row["content"]
        if content is None or not MessageEncryptor.is_encrypted(content):
            continue
        bind.execute(
            sa.text("UPDATE messages SET content = :content WHERE id = :id"),
            {"id": row["id"], "content": encryptor.decrypt(content)},
        )
