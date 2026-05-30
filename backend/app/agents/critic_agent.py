"""Critic Agent — reviews a Simulator draft and proposes refinements.

This makes the Simulator multi-agent: Plan → Act (run Prompt Flow) →
Critique (this module) → Refine (synthesizer or full re-run). The Critic
checks coverage (did we miss obvious workload shifts? knowledge owners?),
consistency (does the timeline reflect the risks?), and tone (Japanese
team-lead-friendly phrasing).
"""

from __future__ import annotations

import json
import re

from app.core.azure_clients import chat_complete

CRITIC_PROMPT = """\
あなたは「Critic」エージェントです。前段の Simulator が出した組織改編の影響予測
JSON を読み、欠落・不整合・トーンの問題を客観的に指摘します。読み手がその
出力を見たときに、判断材料として十分か・根拠と推論が整理されているか、の
観点で見てください。

評価軸：
1. coverage: 重要な観点（報告・相談ライン／業務属人化／担当業務量／実施ステップ）
   の網羅性。判断に効くポイントが拾えているか。
2. consistency: timeline_recommendation が communication_impacts / knowledge_risks /
   workload_shifts と整合しているか（例：リスクとして挙げた領域が実施ステップで
   ケアされているか）。
3. evidence: 各主張に具体的な根拠（メンバー名・スキル・会議参加）が示され、
   「なぜそう判断したか」が読み取れるか。
4. tone: 日本語の敬体で、断定や評価ではなく観察・配慮の言い回しになっているか。
5. realism: 推奨アクションが実行可能で具体的か。日本企業の組織運営に馴染むか。

出力は JSON のみ。Markdown フェンスは禁止。

{
  "verdict": "good" / "needs_refinement",
  "missing_aspects": ["<200字以内の指摘・なぜそれが必要かの理由も添える>"],   // verdict=good なら空配列
  "inconsistencies": ["<200字以内の指摘>"],
  "tone_issues": ["<200字以内の指摘>"],
  "suggested_refinements": ["<200字以内・具体的な改善依頼。何をどう直すかと、その理由>"]
}
"""


REFINER_PROMPT = """\
あなたは Simulator の出力をさらに磨き直すアシスタントです。
前段の Critic から指摘事項を受け取り、元の JSON 全体を改訂して返してください。

ルール：
- 元の JSON の構造（summary / overall_risk_level / communication_impacts /
  knowledge_risks / workload_shifts / timeline_recommendation）を保つ。
- 個別の項目は最大件数を守る（comms/knowledge/workload 各 4 件、timeline 3 フェーズ）。
- Critic が指摘した missing_aspects と suggested_refinements を反映する。
- 改訂後の各項目は、観察された事実 → 解釈 → そう判断した理由、の流れが読み取れる
  ように厚みを持たせる。1 項目あたりの文字数は元の出力と同程度〜やや多めを目安に。
- 日本語の敬体で、配慮のある言い回しに整える。
- 出力は JSON のみ。Markdown フェンスは禁止。
"""


def _extract_json(text: str):
    cleaned = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


async def critique(impact: dict) -> dict:
    """Have the Critic agent score a Simulator output."""
    user_content = (
        "Simulator の出力 JSON を評価してください。\n\n"
        + json.dumps(impact, ensure_ascii=False, default=str)
    )
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": CRITIC_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=1200,
    )
    parsed = _extract_json(raw)
    return parsed or {"verdict": "good", "missing_aspects": [], "inconsistencies": [], "tone_issues": [], "suggested_refinements": []}


async def refine(original_impact: dict, critique_result: dict) -> dict:
    """Refine the Simulator output based on Critic feedback."""
    user_content = (
        "元の Simulator JSON:\n"
        + json.dumps(original_impact, ensure_ascii=False, default=str)
        + "\n\nCritic の指摘:\n"
        + json.dumps(critique_result, ensure_ascii=False, default=str)
        + "\n\n上記の指摘を反映して、改訂版の JSON を返してください。"
    )
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": REFINER_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
        max_tokens=3000,
    )
    parsed = _extract_json(raw)
    return parsed or original_impact
