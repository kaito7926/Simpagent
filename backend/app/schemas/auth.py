from __future__ import annotations

from uuid import UUID

from email_validator import validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator


STANDARD_USER_SCOPES = ["chat:read", "chat:write", "tool:python", "tool:websearch"]
ADMIN_SCOPES = [*STANDARD_USER_SCOPES, "admin:read", "admin:write"]
KNOWN_ROLES = {"user", "admin"}
KNOWN_SCOPES = set(ADMIN_SCOPES)


class _NormalizedEmailModel(BaseModel):
    @field_validator("email", check_fields=False)
    @classmethod
    def normalize_email_value(cls, value: str) -> str:
        return validate_email(value, check_deliverability=False, test_environment=True).normalized


class RegisterRequest(_NormalizedEmailModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(min_length=1, max_length=1024)


class RegisterAcceptedResponse(BaseModel):
    status: str = "accepted"
    message: str = "If this address can be registered, you can continue to sign in."


class LoginRequest(_NormalizedEmailModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(min_length=1, max_length=1024)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUserResponse(_NormalizedEmailModel):
    id: UUID
    email: str
    role: str
    scopes: list[str]
    is_active: bool

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in KNOWN_ROLES:
            raise ValueError("Unknown role")
        return value

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, value: list[str]) -> list[str]:
        unknown = sorted(set(value) - KNOWN_SCOPES)
        if unknown:
            raise ValueError(f"Unknown scopes: {', '.join(unknown)}")
        return sorted(dict.fromkeys(value))
