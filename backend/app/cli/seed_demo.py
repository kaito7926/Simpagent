from __future__ import annotations

import argparse
from datetime import UTC, datetime

from app.core.config import Settings
from app.db.session import create_session_factory
from app.db.repositories.provisioning import ProvisioningError, ProvisioningRepository


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description="Seed development-only demo accounts for SimpAgent.")


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    settings = Settings()

    if not settings.demo_seed_enabled:
        print("Demo seed disabled. No changes applied.")
        return 0

    if settings.app_env != "development":
        print("Demo seed refused because APP_ENV is not development.")
        return 1

    session_factory = create_session_factory(settings)

    async def runner() -> int:
        async with session_factory() as session:
            repo = ProvisioningRepository(session)
            try:
                result = await repo.ensure_demo_accounts(settings=settings, now=datetime.now(UTC))
            except ProvisioningError as exc:
                print(str(exc))
                return 1

        if result.status == "noop":
            print("Demo seed disabled. No changes applied.")
            return 0

        print(
            "Demo accounts are ready. "
            f"Created: {result.created}, updated: {result.updated}, sessions revoked: {result.revoked_families}."
        )
        return 0

    import asyncio

    return asyncio.run(runner())


if __name__ == "__main__":
    raise SystemExit(main())
