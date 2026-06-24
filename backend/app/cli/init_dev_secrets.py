from __future__ import annotations

import argparse
import base64
import secrets
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

DEFAULT_SECRETS_DIR = Path("/run/secrets")


def _write_if_missing(path: Path, content: str, *, binary: bool = False) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        path.write_bytes(content.encode("utf-8"))
    else:
        path.write_text(content, encoding="utf-8")
    return True


def _generate_rsa_pair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


def _generate_message_encryption_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")


def init_dev_secrets(*, secrets_dir: Path) -> dict[str, bool]:
    private_path = secrets_dir / "jwt_private_key"
    public_path = secrets_dir / "jwt_public_key"
    refresh_path = secrets_dir / "refresh_hmac_key"
    csrf_path = secrets_dir / "csrf_hmac_key"
    message_encryption_path = secrets_dir / "message_encryption_key"
    python_capability_path = secrets_dir / "python_capability_secret"

    created = {
        "jwt_private_key": False,
        "jwt_public_key": False,
        "refresh_hmac_key": False,
        "csrf_hmac_key": False,
        "message_encryption_key": False,
        "python_capability_secret": False,
    }

    if not private_path.exists() or not public_path.exists():
        private_pem, public_pem = _generate_rsa_pair()
        created["jwt_private_key"] = _write_if_missing(private_path, private_pem)
        created["jwt_public_key"] = _write_if_missing(public_path, public_pem)

    created["refresh_hmac_key"] = _write_if_missing(refresh_path, secrets.token_urlsafe(48))
    created["csrf_hmac_key"] = _write_if_missing(csrf_path, secrets.token_urlsafe(48))
    created["message_encryption_key"] = _write_if_missing(message_encryption_path, _generate_message_encryption_key())
    created["python_capability_secret"] = _write_if_missing(python_capability_path, secrets.token_urlsafe(48))
    return created


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize development-only secret files for SimpAgent.")
    parser.add_argument(
        "--secrets-dir",
        type=Path,
        default=DEFAULT_SECRETS_DIR,
        help="Directory where development secret files are created if missing.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    created = init_dev_secrets(secrets_dir=args.secrets_dir)
    changed = [name for name, was_created in created.items() if was_created]
    if changed:
        print("Initialized development secret files:")
        for name in changed:
            print(f"- {name}")
    else:
        print("Development secret files already exist. No changes made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
