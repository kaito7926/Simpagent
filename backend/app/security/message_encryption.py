from __future__ import annotations

import base64
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.types import Text, TypeDecorator

from app.core.config import Settings


ENCRYPTED_MESSAGE_PREFIX = "enc-v1"
MESSAGE_ENCRYPTION_AAD = b"simpagent.messages.content.v1"
MESSAGE_ENCRYPTION_NONCE_BYTES = 12


class MessageEncryptionError(ValueError):
    pass


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}".encode("ascii"))


class MessageEncryptor:
    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise MessageEncryptionError("Message encryption key must be 32 bytes.")
        self._cipher = AESGCM(key)

    @staticmethod
    def is_encrypted(value: str) -> bool:
        return value.startswith(f"{ENCRYPTED_MESSAGE_PREFIX}:")

    def encrypt(self, plaintext: str) -> str:
        nonce = secrets.token_bytes(MESSAGE_ENCRYPTION_NONCE_BYTES)
        ciphertext = self._cipher.encrypt(
            nonce,
            plaintext.encode("utf-8"),
            MESSAGE_ENCRYPTION_AAD,
        )
        return f"{ENCRYPTED_MESSAGE_PREFIX}:{_b64url_encode(nonce)}:{_b64url_encode(ciphertext)}"

    def decrypt(self, payload: str) -> str:
        if not self.is_encrypted(payload):
            return payload
        try:
            prefix, encoded_nonce, encoded_ciphertext = payload.split(":", 2)
            if prefix != ENCRYPTED_MESSAGE_PREFIX:
                raise MessageEncryptionError("Unsupported encrypted message prefix.")
            plaintext = self._cipher.decrypt(
                _b64url_decode(encoded_nonce),
                _b64url_decode(encoded_ciphertext),
                MESSAGE_ENCRYPTION_AAD,
            )
            return plaintext.decode("utf-8")
        except (InvalidTag, UnicodeDecodeError, ValueError) as exc:
            raise MessageEncryptionError("Invalid encrypted message content.") from exc


_current_encryptor: MessageEncryptor | None = None


def configure_message_encryptor(settings: Settings) -> None:
    global _current_encryptor
    _current_encryptor = MessageEncryptor(settings.message_encryption_key_value)


def get_message_encryptor() -> MessageEncryptor:
    global _current_encryptor
    if _current_encryptor is None:
        _current_encryptor = MessageEncryptor(Settings().message_encryption_key_value)
    return _current_encryptor


class EncryptedText(TypeDecorator[str]):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return get_message_encryptor().encrypt(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return get_message_encryptor().decrypt(value)
