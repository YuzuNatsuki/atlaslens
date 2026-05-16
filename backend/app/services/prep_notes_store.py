"""Prep notes storage — Cosmos when configured, file fallback otherwise."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from app.core.config import get_settings
from app.core.cosmos_client import cosmos_configured


def get_current_prep(member_id: str) -> dict:
    if cosmos_configured():
        from app.services import cosmos_repo

        doc = cosmos_repo.get_prep_for(member_id)
        if doc is None:
            return {"member_id": member_id, "notes": "", "updated_at": None}
        return {
            "member_id": doc.get("member_id", member_id),
            "notes": doc.get("notes", ""),
            "updated_at": doc.get("updated_at"),
        }
    path = _path_for(member_id)
    if not path.exists():
        return {"member_id": member_id, "notes": "", "updated_at": None}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        "member_id": member_id,
        "notes": raw.get("notes", ""),
        "updated_at": raw.get("updated_at"),
    }


def save_prep(member_id: str, notes: str) -> dict:
    if cosmos_configured():
        from app.services import cosmos_repo

        return cosmos_repo.upsert_prep(member_id, notes)
    path = _path_for(member_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "member_id": member_id,
        "notes": notes,
        "updated_at": date.today().isoformat(),
    }
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return payload


def _path_for(member_id: str) -> Path:
    return get_settings().data_dir / "prep_notes" / f"{member_id}.yaml"
