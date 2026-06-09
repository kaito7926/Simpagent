from __future__ import annotations

import argparse
import getpass
from datetime import UTC, datetime

from app.core.config import Settings
from app.db.repositories.provisioning import ProvisioningError, ProvisioningRepository
from app.db.session import create_session_factory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap the first SimpAgent production admin account.")
    parser.add_argument("--email", required=True, help="Email address for the first admin account.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = Settings()
    session_factory = create_session_factory(settings)

    async def runner() -> int:
        async with session_factory() as session:
            repo = ProvisioningRepository(session)
            password: str | None = None
            try:
                if await repo.bootstrap_password_required(email=args.email):
                    first = getpass.getpass("Nhập mật khẩu cho quản trị viên đầu tiên: ")
                    second = getpass.getpass("Nhập lại mật khẩu: ")
                    if first != second:
                        print("Xác nhận mật khẩu không khớp.")
                        return 1
                    password = first
                result = await repo.bootstrap_admin(
                    settings=settings,
                    email=args.email,
                    now=datetime.now(UTC),
                    password=password,
                )
            except ProvisioningError as exc:
                print(str(exc))
                return 1
            except ValueError as exc:
                print(str(exc))
                return 1

        action = "created" if result.status == "created" else "promoted"
        print(f"Admin bootstrap {action} for {result.email}.")
        return 0

    import asyncio

    return asyncio.run(runner())


if __name__ == "__main__":
    raise SystemExit(main())
