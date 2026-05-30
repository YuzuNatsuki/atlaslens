"""Critic / Refiner for AtlasLens JSON summaries.

Generalises the Org Simulator's Plan → Act → Critique → Refine loop to any
JSON summary an AtlasLens agent produces. Two summaries use it today:

- Daily Pulse range summary (期間サマリー)
- Skill Growth Summary (M9, 成長サマリー)

Design notes:
- The Critic returns ``verdict in {"good", "needs_refinement"}`` plus a
  list of typed issues. Refinement only fires when verdict is the latter,
  so well-formed summaries don't pay the extra round-trip.
- The Refiner is given the original payload + the critic report and asked
  to keep the schema identical. We never let it invent fields.
- Both prompts are domain-aware (we tell the critic *what* kind of summary
  it's reviewing) so the criteria stay tight.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.azure_clients import chat_complete

log = logging.getLogger(__name__)


# Per-summary criteria. Used to scope the critic and the refiner.
SCHEMA_PROFILES: dict[str, dict[str, str]] = {
    "team-summary-range": {
        "label": "日報の期間サマリー (複数日横断)",
        "schema_hint": (
            "{tldr: string[3], themes: string[2..4], "
            "by_member: { <name>: {summary, trend, evidence_dates[]} }, "
            "risk_signals[] {member_name, kind in {retention, friction, capacity, engagement, health}, "
            "summary, evidence_dates[]}, recommended_actions[3..5]}"
        ),
        "criteria": (
            "1. coverage: 日報を出した全員が by_member に登場しているか。\n"
            "2. evidence: trend / risk_signals に evidence_dates が必ず付いているか。\n"
            "3. consistency: trend と by_member.summary、recommended_actions が矛盾していないか。\n"
            "4. tone: 評価ではなく観察 (敬体・配慮あり)。「監視」「遅れている」など主観の禁止語が出ていないか。\n"
            "5. specificity: recommended_actions が具体的アクション (誰に / 何を / いつまで) になっているか。"
        ),
    },
    "skill-growth": {
        "label": "本人向けの Skill Growth Summary",
        "schema_hint": (
            "{tldr: string, growing[]{area, evidence, next_step}, "
            "stuck[]{area, evidence, suggested_action}, career_alignment: string, "
            "recommended_focus: string[]}"
        ),
        "criteria": (
            "1. evidence: growing / stuck の evidence に必ず日報日付 (YYYY-MM-DD) が含まれているか。\n"
            "2. specificity: next_step / suggested_action が 60 字以内で具体的な行動になっているか。\n"
            "3. tone: 評価・格付けではなく本人視点の観察と提案になっているか。\n"
            "4. career_alignment: 本人が書いたキャリア目標と最近の動きの関係が読み取れるか。\n"
            "5. honesty: 入力に無い情報を捏造していないか。日報が少ない場合は tldr に明記されているか。"
        ),
    },
}


def _critic_prompt(profile: dict[str, str]) -> str:
    return f"""\
あなたは AtlasLens の "Critic" エージェントです。
前段のエージェントが生成した「{profile["label"]}」の JSON を読み、評価軸に沿って客観的に
不足や不整合を指摘します。Critic 自身が JSON を直接書き換えることはしません。

想定スキーマ: {profile["schema_hint"]}

評価軸:
{profile["criteria"]}

出力は JSON のみ。Markdown フェンスは禁止。次の形式に従う：

{{
  "verdict": "good" or "needs_refinement",
  "missing_aspects": ["<200字以内の指摘・なぜ必要かの理由も書く>", ...],   // verdict=good なら空配列
  "inconsistencies": ["<200字以内・どこと何が矛盾しているか>", ...],
  "tone_issues": ["<200字以内・該当文と、どう直すべきかの方向性>", ...],
  "suggested_refinements": ["<200字以内・refiner への具体的な依頼>", ...]
}}
"""


def _refiner_prompt(profile: dict[str, str]) -> str:
    return f"""\
あなたは AtlasLens の Refiner です。前段の Critic からの指摘事項を反映して、
「{profile["label"]}」の JSON を改訂してください。

ルール：
- 元の JSON のキーセットと構造を維持する。新しいトップレベルキーを追加しない。
- 想定スキーマ: {profile["schema_hint"]}
- evidence や evidence_dates は本人が書いた事実のみ。新しい日付を捏造しない。
- 配列の件数上限は元の指示に従う (例: tldr ちょうど 3 件、recommended_actions 3〜5 件)。
- 日本語の敬体。「監視」「遅れている」など主観表現は避け、観察と配慮で書く。
- 出力は JSON のみ。Markdown フェンスは禁止。
"""


def _extract_json(text: str) -> Any | None:
    cleaned = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


async def critique(kind: str, summary: dict[str, Any]) -> dict[str, Any]:
    """Score a summary. Returns a critic report with verdict + issues."""
    profile = SCHEMA_PROFILES.get(kind)
    if profile is None:
        return {
            "verdict": "good",
            "missing_aspects": [],
            "inconsistencies": [],
            "tone_issues": [],
            "suggested_refinements": [],
            "_skipped": f"unknown summary kind: {kind}",
        }
    user_content = (
        f"レビュー対象の {profile['label']} JSON:\n"
        + json.dumps(summary, ensure_ascii=False, default=str)
    )
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": _critic_prompt(profile)},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=1000,
    )
    parsed = _extract_json(raw)
    if not isinstance(parsed, dict):
        return {
            "verdict": "good",
            "missing_aspects": [],
            "inconsistencies": [],
            "tone_issues": [],
            "suggested_refinements": [],
            "_parse_error": True,
        }
    parsed.setdefault("verdict", "good")
    for key in ("missing_aspects", "inconsistencies", "tone_issues", "suggested_refinements"):
        parsed.setdefault(key, [])
    return parsed


async def refine(
    kind: str,
    summary: dict[str, Any],
    critic_report: dict[str, Any],
) -> dict[str, Any]:
    """Produce a refined version of the summary, preserving schema."""
    profile = SCHEMA_PROFILES.get(kind)
    if profile is None:
        return summary
    user_content = (
        "元の JSON:\n"
        + json.dumps(summary, ensure_ascii=False, default=str)
        + "\n\nCritic の指摘:\n"
        + json.dumps(critic_report, ensure_ascii=False, default=str)
        + "\n\n指摘を反映した改訂版 JSON のみを返してください。"
    )
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": _refiner_prompt(profile)},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
        max_tokens=2400,
    )
    parsed = _extract_json(raw)
    if isinstance(parsed, dict):
        return parsed
    return summary


async def critique_and_maybe_refine(
    kind: str,
    summary: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Convenience: critique → refine when needed.

    Returns ``(final_summary, critic_report, refined)``. ``refined`` is True
    when the Refiner actually replaced the original.
    """
    if not isinstance(summary, dict) or summary.get("parse_error"):
        return summary, {"verdict": "good", "_skipped": "parse_error"}, False

    try:
        report = await critique(kind, summary)
    except Exception as exc:  # noqa: BLE001
        log.warning("summary_critic.critique failed (%s): %s", kind, exc)
        return summary, {"verdict": "good", "_error": str(exc)}, False

    if report.get("verdict") != "needs_refinement":
        return summary, report, False

    try:
        refined = await refine(kind, summary, report)
    except Exception as exc:  # noqa: BLE001
        log.warning("summary_critic.refine failed (%s): %s", kind, exc)
        return summary, report, False

    if isinstance(refined, dict) and refined:
        return refined, report, True
    return summary, report, False
