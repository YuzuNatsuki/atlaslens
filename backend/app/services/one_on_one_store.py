"""1on1 storage — Cosmos when configured, markdown file fallback otherwise."""

from __future__ import annotations

from datetime import datetime

import yaml

from app.core.config import get_settings
from app.core.cosmos_client import cosmos_configured
from app.models.schemas import OneOnOne


def save_one_on_one(record: OneOnOne) -> OneOnOne:
    if cosmos_configured():
        from app.services import cosmos_repo

        return cosmos_repo.upsert_one_on_one(record)
    return _save_file(record)


def make_one_on_one_id(em_id: str, member_id: str, held_at: datetime) -> str:
    return f"1on1-{member_id}-{held_at.date().isoformat()}-{em_id}"


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items if item.strip())


def _save_file(record: OneOnOne) -> OneOnOne:
    settings = get_settings()
    folder = settings.data_dir / "one_on_ones" / record.member_id
    folder.mkdir(parents=True, exist_ok=True)
    held_date = record.held_at.date().isoformat()
    path = folder / f"{held_date}.md"
    front = {
        "id": record.id,
        "em_id": record.em_id,
        "held_at": record.held_at.isoformat(),
        "topics": list(record.topics),
    }
    body = "\n".join(
        [
            "---",
            yaml.safe_dump(front, allow_unicode=True, sort_keys=False).rstrip(),
            "---",
            "",
            "## ノート",
            "",
            record.notes,
            "",
            "## ToDo",
            "",
            _bullets(record.todos),
            "",
            "## フォローアップ",
            "",
            _bullets(record.follow_ups),
            "",
        ]
    )
    path.write_text(body, encoding="utf-8")
    return record
