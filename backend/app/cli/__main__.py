from __future__ import annotations

import argparse

from pathlib import Path

from . import bootstrap_admin, init_dev_secrets, seed_demo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SimpAgent operator and development CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap-admin", help="Create or promote the first admin account.")
    bootstrap.add_argument("--email", required=True, help="Email address for the first admin account.")

    init_dev = subparsers.add_parser("init-dev-secrets", help="Create development-only secret files if missing.")
    init_dev.add_argument(
        "--secrets-dir",
        type=str,
        default=str(init_dev_secrets.DEFAULT_SECRETS_DIR),
        help="Directory where development secret files are created if missing.",
    )

    subparsers.add_parser("seed-demo", help="Seed development-only demo accounts.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "bootstrap-admin":
        return bootstrap_admin.main(["--email", args.email])
    if args.command == "init-dev-secrets":
        return init_dev_secrets.main(["--secrets-dir", str(Path(args.secrets_dir))])
    if args.command == "seed-demo":
        return seed_demo.main([])

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
