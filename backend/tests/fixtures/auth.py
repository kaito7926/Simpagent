from __future__ import annotations

from dataclasses import dataclass

DEFAULT_ORIGIN = "http://localhost:3000"
DEFAULT_BAD_ORIGIN = "http://evil.example.test"
DEFAULT_CSRF = "csrf-placeholder"


@dataclass(slots=True)
class LoginPayload:
    email: str
    password: str
