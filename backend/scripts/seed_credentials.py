"""Generate `data/atlascorp/credentials.yaml` with bcrypt password hashes.

The plaintext password is NEVER hard-coded. Provide it via the
`DEMO_PASSWORD` environment variable (or `--password` flag). The script
writes only the hashes — the plain value is never persisted.

Usage:
    DEMO_PASSWORD='...' python backend/scripts/seed_credentials.py
    # or
    python backend/scripts/seed_credentials.py --password '...'
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import bcrypt
import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "atlascorp"

ACCOUNTS = [
    {"member_id": "em001", "email": "tanaka.ken@atlaslens.dev", "name": "田中 健"},
    {"member_id": "mem001", "email": "sato.misaki@atlaslens.dev", "name": "佐藤 美咲"},
    {"member_id": "mem002", "email": "suzuki.ryo@atlaslens.dev", "name": "鈴木 亮"},
    {"member_id": "mem003", "email": "yamamoto.yuka@atlaslens.dev", "name": "山本 由香"},
    {"member_id": "mem004", "email": "watanabe.sho@atlaslens.dev", "name": "渡辺 翔"},
]


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--password",
        default=os.environ.get("DEMO_PASSWORD"),
        help="Plaintext password to hash. Defaults to the DEMO_PASSWORD env var.",
    )
    args = parser.parse_args()

    password = (args.password or "").strip()
    if not password:
        print(
            "ERROR: provide a password via --password or the DEMO_PASSWORD env var.",
            file=sys.stderr,
        )
        sys.exit(2)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    accounts_yaml = []
    for acc in ACCOUNTS:
        accounts_yaml.append(
            {
                "member_id": acc["member_id"],
                "email": acc["email"],
                "name": acc["name"],
                "password_hash": _hash(password),
            }
        )
    path = DATA_DIR / "credentials.yaml"
    # We intentionally omit `default_password_hint` so the plaintext
    # is never written to disk.
    path.write_text(
        yaml.safe_dump(
            {"accounts": accounts_yaml},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    print(f"Seeded {path} ({len(accounts_yaml)} accounts; plaintext discarded)")


if __name__ == "__main__":
    main()
