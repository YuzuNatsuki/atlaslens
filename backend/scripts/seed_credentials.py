"""Generate `data/atlascorp/credentials.yaml` with bcrypt password hashes.

5 members, all sharing the demo password `atlaslens2026`. Re-run any time to
refresh hashes after editing the email mapping.
"""

from __future__ import annotations

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

DEFAULT_PASSWORD = "atlaslens2026"


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    accounts_yaml = []
    for acc in ACCOUNTS:
        accounts_yaml.append(
            {
                "member_id": acc["member_id"],
                "email": acc["email"],
                "name": acc["name"],
                "password_hash": _hash(DEFAULT_PASSWORD),
            }
        )
    path = DATA_DIR / "credentials.yaml"
    path.write_text(
        yaml.safe_dump(
            {"default_password_hint": DEFAULT_PASSWORD, "accounts": accounts_yaml},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    print(f"Seeded {path}")
    print(f"Demo password for all accounts: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    main()
