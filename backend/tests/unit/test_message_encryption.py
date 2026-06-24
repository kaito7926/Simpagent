from __future__ import annotations

import pytest

from app.core.config import Settings
from app.security.message_encryption import (
    EncryptedText,
    MessageEncryptionError,
    MessageEncryptor,
    configure_message_encryptor,
)


def test_message_encryptor_roundtrips_with_versioned_envelope(settings) -> None:
    encryptor = MessageEncryptor(settings.message_encryption_key_value)
    plaintext = "Chat transcript must stay encrypted at rest."

    ciphertext = encryptor.encrypt(plaintext)

    assert ciphertext != plaintext
    assert MessageEncryptor.is_encrypted(ciphertext) is True
    assert encryptor.decrypt(ciphertext) == plaintext


def test_message_encryptor_preserves_legacy_plaintext_reads(settings) -> None:
    encryptor = MessageEncryptor(settings.message_encryption_key_value)

    assert encryptor.decrypt("legacy plaintext row") == "legacy plaintext row"


def test_encrypted_text_type_encrypts_on_bind_and_decrypts_on_read(settings) -> None:
    configure_message_encryptor(settings)
    encrypted_text = EncryptedText()

    stored_value = encrypted_text.process_bind_param("hello secure storage", dialect=None)

    assert isinstance(stored_value, str)
    assert stored_value != "hello secure storage"
    assert encrypted_text.process_result_value(stored_value, dialect=None) == "hello secure storage"


def test_invalid_encrypted_payload_raises_safe_error(settings) -> None:
    encryptor = MessageEncryptor(settings.message_encryption_key_value)

    with pytest.raises(MessageEncryptionError):
        encryptor.decrypt("enc-v1:not-base64:still-not-base64")


def test_message_encryption_key_must_decode_to_32_bytes() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://postgres:postgres@db:5432/app",
        allowed_origins=["http://localhost:3000"],
        jwt_private_key="secret",
        jwt_public_key="secret",
        refresh_hmac_key="refresh-refresh-refresh-refresh",
        csrf_hmac_key="csrf-csrf-csrf-csrf-csrf-csrf-csrf",
        message_encryption_key="YQ",
    )

    with pytest.raises(ValueError, match="32 bytes"):
        _ = settings.message_encryption_key_value
