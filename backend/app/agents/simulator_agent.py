"""Simulator Agent — uses Azure OpenAI (under the Foundry resource).

The primary path for Org Impact Simulator will be a Foundry Prompt Flow endpoint
(see infra/prompt_flow/org_impact). This file is the direct-LLM fallback that
keeps the API working when the Prompt Flow endpoint is not configured.
"""

from __future__ import annotations

import json

from app.core.azure_clients import chat_complete

SIMULATOR_SYSTEM_PROMPT = """\
あなたは日本のエンジニアリングチームを支援する EM 向けアシスタントです。
チーム構造の変更案を受け取り、その影響を 4 つの観点で分析し、JSON で返します。

文体：自然な日本語の敬体（〜です／〜ます）。事実ベース。評価ではなく観察。

出力 JSON：

- summary: EM 向けの要約（240文字以内）。良し悪しを断定せず、注意点と前向きな
  期待を両方含める。
- overall_risk_level: low / medium / high のいずれか（控えめに見積もる）。
- communication_impacts: 最大 4 件
  - pair: 影響を受ける二人のメンバー名（例：「佐藤 と 渡辺」）
  - change: 80文字以内。「コミュニケーションが減る／増える」のような中立な記述
  - evidence: 80文字以内。会議参加数や役割の根拠
- knowledge_risks: 最大 4 件
  - area: スキル領域の名称（例：「SRE」「決済 API」「フロントエンドの a11y」）
  - current_owners: そのスキルを持つメンバー名の配列
  - risk_after_change: 80文字以内。「単一障害点化の懸念」「ペアプロが失われる」など
  - evidence: 80文字以内
- workload_shifts: 最大 4 件
  - member: 入力データの member id（例: mem001）
  - before: 50文字以内（現状の主な業務）
  - after: 50文字以内（変更後の主な業務）
  - magnitude: low / medium / high
- timeline_recommendation: 最大 3 フェーズ
  - phase: 短いラベル（例：「準備」「実行」「定着」）
  - weeks: 整数
  - actions: 各 80文字以内の日本語アクション（具体的な動詞で始める）

ルール：
- 評価より配慮。「○○さんが負担増」より「○○さんの稼働が増える見込み」と書く。
- 与えられた context にあるスキル・会議参加・OKR から根拠を引く。推測は最小限。
- JSON のみ出力。Markdown フェンスは付けない。
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
