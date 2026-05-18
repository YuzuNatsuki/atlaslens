"""Analyzer Agent — hosted on Azure AI Foundry Agent Service.

Primary path: Foundry Agent Service (managed agent, thread+run shown in the
Foundry Portal). Fallback: direct chat completion. The fallback exists so
local dev or environments without the Foundry RBAC propagation still work,
but the production trace is the Foundry one.
"""

from __future__ import annotations

import json
import logging

from app.core import foundry_agents
from app.core.azure_clients import chat_complete
from app.models.schemas import DailyReport, Goal, MemberProfile, OneOnOne

logger = logging.getLogger(__name__)

ANALYZER_SYSTEM_PROMPT = """\
あなたは AtlasLens の "Analyzer" です。日本のエンジニアリングチームを支援する
EM 向けのアシスタントとして、メンバーの直近の状態を要約します。

以下の JSON 形式で返してください。キーと構造は厳密に守り、人間向け文字列は
すべて自然な日本語の敬体で書きます。

{
  "highlights":         [{"text": "<120字以内・できていることを具体的に>", "evidence": ["<出典 id>"]}],
  "risks":              [{"text": "<120字以内・気がかりな点を中立的に>", "evidence": ["<出典 id>"]}],
  "growth_signals":     [{"text": "<120字以内・伸びている兆候>", "evidence": ["<出典 id>"]}],
  "suggested_questions":[{"text": "<100字以内・1on1 で聞きたい質問>", "evidence": ["<出典 id>"]}]
}

書き方のお願い：
- 各配列は最大 3 件まで。情報量の多いものを選ぶ。
- 個人を攻撃する言い方は避ける。「〜できていない」より「〜が遅れ気味に見える」
  「〜の確認余地あり」のような中立・観察ベースの表現を使う。
- 感情や性格は推測しない。日報・1on1・OKR・会議の事実だけ拾う。
- 評価ではなく支援を意図する。例：「メンタリング機会を増やすと良いかも」など。
- evidence は与えられたデータの id (daily-..., 1on1-..., g-..., mtg-...)。
- 出力は JSON のみ。Markdown フェンスや前置きは付けない。
"""


async def analyze_member(
    profile: MemberProfile,
    goals: list[Goal],
    daily_reports: list[DailyReport],
    one_on_ones: list[OneOnOne],
) -> dict:
    payload = {
        "profile": {
            "id": profile.id,
            "name": profile.name,
            "role": profile.role.value,
            "title": profile.title,
            "skills": profile.skills,
        },
        "goals": [
            {
                "id": g.id,
                "objective": g.objective,
                "status": g.status,
                "progress_pct": g.progress_pct,
                "key_results": g.key_results,
            }
            for g in goals
        ],
        "recent_daily_reports": [
            {
                "id": d.id,
                "date": d.report_date.isoformat(),
                "yesterday": d.yesterday,
                "today": d.today,
                "blockers": d.blockers,
            }
            for d in daily_reports[-7:]
        ],
        "recent_one_on_ones": [
            {
                "id": o.id,
                "held_at": o.held_at.isoformat(),
                "topics": o.topics,
                "notes": o.notes,
                "todos": o.todos,
            }
            for o in one_on_ones[-2:]
        ],
    }
    user_prompt = (
        "Member context follows. Return the JSON described in the system prompt.\n\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
    )

    raw = ""
    source = "fallback_chat"
    if foundry_agents.is_available():
        try:
            raw = await foundry_agents.run_agent(
                name="atlaslens-analyzer",
                instructions=ANALYZER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            source = "foundry_agent"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Foundry analyzer run failed, falling back: %s", exc)

    if not raw:
        raw = await chat_complete(
            messages=[
                {"role": "system", "content": ANALYZER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            max_tokens=900,
        )

    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            result["_source"] = source
        return result
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True, "_source": source}
