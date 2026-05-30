"""Skill Growth Summary — per-member retrospective on what's growing.

This is the member-facing AI benefit: the user opens MyDashboard and asks
"AI, summarise where I'm growing vs stuck". Inputs are only the member's own
daily reports + goals (career canvas included). Output is shaped as JSON so
the React UI can render structured sections.

Persisted via `artefact_store` (kind=`skill-growth`, key=`<member_id>:<YYYY-MM-DD>`)
so each generation survives container restarts and the user can flip back
through historical summaries.
"""

from __future__ import annotations

import json
import logging
from datetime import date as date_type
from datetime import timedelta
from typing import Any

from app.core.azure_clients import chat_complete
from app.services.artefact_store import (
    get_artefact,
    list_artefacts,
    save_artefact,
)
from app.services.data_loader import DataLoader

log = logging.getLogger(__name__)

ARTEFACT_KIND = "skill-growth"
DEFAULT_WINDOW_DAYS = 30

SYSTEM_PROMPT = """\
あなたは AtlasLens の "Career Coach Reporter" です。
メンバー本人の直近 N 日分の日報と、本人が書いた目標（OKR + キャリアキャンバス）
だけを材料に、本人向けの振り返りを作ります。

以下の JSON 形式で返してください。すべて日本語の敬体で、簡潔に。

{
  "tldr": "<120字以内・直近期間で起きた変化を一文で>",
  "growing": [
    {
      "area": "<スキル名 / 領域>",
      "evidence": "<日付付きで1〜2件・具体的に>",
      "next_step": "<60字以内・次の一歩>"
    }
  ],
  "stuck": [
    {
      "area": "<伸び悩んでいる領域>",
      "evidence": "<日付付きで根拠>",
      "suggested_action": "<60字以内・本人がとれる具体行動>"
    }
  ],
  "career_alignment": "<140字以内・本人が書いたキャリア目標と最近の動きがどう繋がっているか。
                       目標が空ならその旨だけ書く>",
  "recommended_focus": ["<1週間で意識すると良い具体的なフォーカス>", ...]
}

ルール：
- growing / stuck はそれぞれ 1〜3 件。なければ空配列で良い。
- evidence は必ず日報の日付 (YYYY-MM-DD) を1つ以上含める。
- 評価/格付けはしない。事実と提案だけ。
- 入力にない情報を捏造しない。日報が少ない場合はその旨を tldr に書く。
- 出力は JSON のみ。
"""


def _artefact_key(member_id: str, today: date_type) -> str:
    return f"{member_id}:{today.isoformat()}"


def _build_payload(member_id: str, window_days: int) -> dict[str, Any]:
    loader = DataLoader()
    profile = loader.get_profile(member_id)
    today = date_type.today()
    since = today - timedelta(days=window_days)
    reports = loader.load_daily_reports(member_id, since=since)
    goals = loader.load_goals(member_id)
    return {
        "member": {
            "id": member_id,
            "name": profile.name if profile else member_id,
            "title": profile.title if profile else "",
            "skills": profile.skills if profile else [],
            "interests": profile.interests if profile else [],
        },
        "window_days": window_days,
        "today": today.isoformat(),
        "daily_reports": [
            {
                "date": r.report_date.isoformat(),
                "yesterday": r.yesterday,
                "today": r.today,
                "blockers": r.blockers,
            }
            for r in reports
        ],
        "goals": [g.model_dump(mode="json") for g in goals],
    }, len(reports)


async def generate_summary(
    member_id: str,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    force: bool = False,
) -> dict[str, Any]:
    """Return a freshly generated (or cached) Skill Growth Summary."""
    today = date_type.today()
    key = _artefact_key(member_id, today)

    if not force:
        cached = get_artefact(ARTEFACT_KIND, key)
        if cached is not None:
            return {
                "member_id": member_id,
                "key": key,
                "summary": cached["payload"],
                "generated_at": cached.get("generated_at"),
                "report_count": cached.get("report_count"),
                "window_days": cached.get("window_days", window_days),
                "from_cache": True,
            }

    payload, report_count = _build_payload(member_id, window_days)
    user_prompt = (
        "本人向けの Skill Growth Summary を JSON で返してください。\n\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
    )
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
        max_tokens=900,
    )
    try:
        summary = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("skill-growth: JSON parse failed for %s", member_id)
        summary = {"raw": raw, "parse_error": True}

    saved = save_artefact(
        ARTEFACT_KIND,
        key,
        summary,
        extra={
            "report_count": report_count,
            "window_days": window_days,
            "model": "gpt-4o",
            "member_id": member_id,
        },
    )
    return {
        "member_id": member_id,
        "key": key,
        "summary": summary,
        "generated_at": saved.get("generated_at"),
        "report_count": report_count,
        "window_days": window_days,
        "from_cache": False,
    }


def latest_summary(member_id: str) -> dict[str, Any] | None:
    """Return today's stored summary for the member without invoking the LLM."""
    today = date_type.today()
    key = _artefact_key(member_id, today)
    cached = get_artefact(ARTEFACT_KIND, key)
    if cached is None:
        return None
    return {
        "member_id": member_id,
        "key": key,
        "summary": cached["payload"],
        "generated_at": cached.get("generated_at"),
        "report_count": cached.get("report_count"),
        "window_days": cached.get("window_days"),
        "from_cache": True,
    }


def list_summaries(member_id: str, *, limit: int = 10) -> list[dict[str, Any]]:
    """Return historical Skill Growth Summary metadata for a member, newest first."""
    rows = list_artefacts(ARTEFACT_KIND, limit=limit * 4)
    out: list[dict[str, Any]] = []
    prefix = f"{member_id}:"
    for r in rows:
        key = r.get("key") or ""
        if not key.startswith(prefix):
            continue
        out.append(
            {
                "key": key,
                "date": key.split(":", 1)[1] if ":" in key else key,
                "generated_at": r.get("generated_at"),
                "report_count": r.get("report_count"),
                "window_days": r.get("window_days"),
            }
        )
        if len(out) >= limit:
            break
    return out


def get_summary_by_key(member_id: str, key: str) -> dict[str, Any] | None:
    """Fetch a stored summary, checking that the key belongs to this member."""
    if not key.startswith(f"{member_id}:"):
        return None
    cached = get_artefact(ARTEFACT_KIND, key)
    if cached is None:
        return None
    return {
        "member_id": member_id,
        "key": key,
        "summary": cached["payload"],
        "generated_at": cached.get("generated_at"),
        "report_count": cached.get("report_count"),
        "window_days": cached.get("window_days"),
        "from_cache": True,
    }
