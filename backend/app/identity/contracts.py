from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class VerifiedIdentity:
    issuer: str
    subject: str
    email: str | None
    email_verified: bool
    authentication_method: str


class IdentityProvider(Protocol):
    async def authenticate(self, request: object) -> VerifiedIdentity: ...
