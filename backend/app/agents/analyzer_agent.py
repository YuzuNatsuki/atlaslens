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
エンジニアリングマネージャー（EM）向けのアシスタントとして、メンバーの直近の
状態を整理して伝えます。EM がメンバーの状況を素早く把握し、見落としていた
ことに「気づき」を得られるよう、事実とその背景・推論を丁寧に書いてください。

以下の JSON 形式で返してください。キーと構造は厳密に守り、人間向け文字列は
すべて自然な日本語の敬体で書きます。

{
  "highlights":         [{"text": "<150〜300字目安・できていることを具体的に、事実と背景・解釈をセットで>", "evidence": ["<参照元 id>"]}],
  "risks":              [{"text": "<150〜300字目安・注意したい点を中立的に、なぜそう判断したかも添えて>", "evidence": ["<参照元 id>"]}],
  "growth_signals":     [{"text": "<150〜300字目安・成長の兆しを、何がどう伸びていると見えるかの根拠付きで>", "evidence": ["<参照元 id>"]}],
  "suggested_questions":[{"text": "<120〜200字目安・対話の切り口（1on1 で確認したい論点）を、なぜそれを聞くべきかの背景もセットで>", "evidence": ["<参照元 id>"]}]
}

書き方のお願い：
- 各配列は最大 3 件まで。情報量の多いもの・EM に取って判断に効くものを選ぶ。
- **1 項目につき必ず次の 3 段を含める**：
  ① 観察された事実（いつの日報・1on1・OKR のどこに何があったか具体的に）
  ② 解釈や考えられる背景（事実から読み取れること、推測ではなく観察に基づく解釈）
  ③ 「そう判断した理由」または「EM への示唆」（なぜ取り上げたか、次にどう向き合うとよいか）
- 個人を攻撃する言い方は避ける。「〜できていない」より「〜が遅れ気味に見える」
  「〜の確認余地あり」のような中立・観察ベースの表現を使う。
- 感情や性格は推測しない。日報・1on1・OKR・会議の事実だけ拾う。
- 評価ではなく支援を意図する。例：「メンタリング機会を増やすと良いかもしれません。
  というのは、直近 2 週間の日報で技術面の相談が増えており…」のように、提案と根拠を併記。
- evidence は与えられたデータの id (daily-..., 1on1-..., g-..., mtg-...) を該当箇所ごとに。
  1 項目に複数の参照元がある場合はすべて配列に含めること（根拠の網羅性を重視）。
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
            max_tokens=2200,
        )

    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            result["_source"] = source
        return result
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True, "_source": source}
