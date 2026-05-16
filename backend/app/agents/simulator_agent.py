"""Simulator Agent — uses Azure OpenAI (under the Foundry resource).

The primary path for Org Impact Simulator will be a Foundry Prompt Flow endpoint
(see infra/prompt_flow/org_impact). This file is the direct-LLM fallback that
keeps the API working when the Prompt Flow endpoint is not configured.
"""

from __future__ import annotations

import json

from app.core.azure_clients import chat_complete

SIMULATOR_SYSTEM_PROMPT = """\
あなたはエンジニアリングマネージャーを支援するアシスタントです。
チーム構造の変更案を受け取って、その影響を分析し、JSONで結果を返します。

出力は以下のキーを持つJSONオブジェクトです。全ての日本語フィールドはJapaneseで簡潔に書きます。

- summary: EMへの要約。240文字以内。
- overall_risk_level: low / medium / high のいずれか。
- communication_impacts: 最大4件。各要素は次のキー: pair, change, evidence。
  - pair: 影響を受ける二人のメンバー名を「佐藤 と 渡辺」のように書く。
  - change: 80文字以内で変化を説明。
  - evidence: 80文字以内で根拠を説明。
- knowledge_risks: 最大4件。各要素は次のキー: area, current_owners, risk_after_change, evidence。
  - area: スキル領域の名称。
  - current_owners: 現状の担当メンバー名の配列。
  - risk_after_change: 80文字以内のリスク説明。
  - evidence: 80文字以内の根拠説明。
- workload_shifts: 最大4件。各要素は次のキー: member, before, after, magnitude。
  - member: 入力データのmember id。
  - before: 50文字以内の現状負荷の説明。
  - after: 50文字以内の変更後の負荷の説明。
  - magnitude: low / medium / high のいずれか。
- timeline_recommendation: 最大3フェーズ。各要素は次のキー: phase, weeks, actions。
  - phase: 短いフェーズラベル。
  - weeks: 整数。
  - actions: 各80文字以内の日本語アクション項目の配列。

入力で渡される文脈（スキル、会議、目標）に基づいて分析してください。
"""


async def simulate(change: dict, org_context: dict) -> dict:
    payload = {"proposed_change": change, "org_context": org_context}
    # Inline system prompt into user content — Azure Prompt Shield is over-eager
    # with structured "Return JSON" system prompts here.
    user_prompt = (
        SIMULATOR_SYSTEM_PROMPT
        + "\n\n以下が入力データです。指示通りに JSON で出力してください。\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
    )
    raw = await chat_complete(
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
        max_tokens=1300,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True}
