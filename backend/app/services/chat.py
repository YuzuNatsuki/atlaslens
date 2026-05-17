"""Chat assistant — EM-only. Conversational, grounded on AtlasCorp data.

The reply style is steerable: callers pick a preset (`standard`, `concise`,
`coaching`, `casual`, `analytical`, `bullet`) or send a free-form `style_instructions`
string to write their own persona.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel

from app.core.azure_clients import chat_complete
from app.services.data_loader import DataLoader


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


BASE_PROMPT = """\
あなたは AtlasLens の EM 用 AI アシスタントです。Microsoft Azure 上の Foundry で
動作し、AtlasCorp というチーム (5 名) の最新データ (プロフィール / OKR / 日報 /
1on1 / 議事録) にアクセスできます。

守ること（スタイルにかかわらず常に有効）：
- 推測ではなく与えられたデータを根拠にする。出典は member_id / 日付で示せると良い。
- メンバーの感情や性格は推測しない。観測可能な行動だけ言及する。
- 評価ではなく支援を意図する。攻撃的・断定的な言い回しは避ける。
- 情報が足りないときは「データには含まれていません」と素直に伝え、追加で見るべき
  ファイル/メンバーを提案する。
- 日本語の自然な敬体で書く。
"""

STYLE_PRESETS: dict[str, dict[str, str | float]] = {
    "standard": {
        "label": "標準（バランス型）",
        "instructions": (
            "回答スタイルは『標準』。見出しや箇条書きを適度に使い、要点を整理しつつ"
            "短めの説明を添えてください。最後に 1〜2 個のフォローアップ質問があれば添える。"
        ),
        "temperature": 0.4,
    },
    "concise": {
        "label": "短く一言",
        "instructions": (
            "回答スタイルは『短く一言』。1〜3 文の平文だけで答えてください。"
            "見出し、箇条書き、絵文字は使わない。フォローアップ質問は付けない。"
        ),
        "temperature": 0.3,
    },
    "bullet": {
        "label": "箇条書きのみ",
        "instructions": (
            "回答スタイルは『箇条書きのみ』。前置きや要約は書かず、要点を箇条書きだけで"
            "並べる。各項目は 30 字以内、最大 5 件。"
        ),
        "temperature": 0.3,
    },
    "coaching": {
        "label": "コーチング（質問を返す）",
        "instructions": (
            "回答スタイルは『コーチング』。直接的な答えを 1 つに絞ったら、すぐに EM 自身に"
            "考えてもらう問いを 2〜3 個返してください。答えは決めつけず、選択肢を示す。"
        ),
        "temperature": 0.6,
    },
    "analytical": {
        "label": "分析レポート（出典付き）",
        "instructions": (
            "回答スタイルは『分析レポート』。データに基づく結論を最初に書き、続けて根拠"
            "（日付・出典 id）を明示する。観察された事実と推論を明確に分けて書く。"
        ),
        "temperature": 0.2,
    },
    "casual": {
        "label": "カジュアル（雑談調）",
        "instructions": (
            "回答スタイルは『カジュアル』。Slack DM のように肩肘張らない言い回しで答える。"
            "短め・親しみやすく、ただし敬語は崩しすぎない。絵文字は最大 1 個まで。"
        ),
        "temperature": 0.7,
    },
}


def _context_snapshot(loader: DataLoader) -> str:
    """Compact snapshot of the whole team — gives the model grounded context."""
    profiles = loader.load_profiles()
    snapshot = {
        "members": [
            {
                "id": p.id,
                "name": p.name,
                "role": p.role.value,
                "title": p.title,
                "manager_id": p.manager_id,
                "skills": p.skills,
            }
            for p in profiles
        ],
        "per_member": [],
    }
    for p in profiles:
        if p.role.value == "em":
            continue
        goals = loader.load_goals(p.id)
        dailies = loader.load_daily_reports(p.id)
        one_on_ones = loader.load_one_on_ones(p.id)
        snapshot["per_member"].append(
            {
                "member_id": p.id,
                "name": p.name,
                "goals": [
                    {
                        "id": g.id,
                        "objective": g.objective,
                        "status": g.status,
                        "progress_pct": g.progress_pct,
                    }
                    for g in goals
                ],
                "recent_daily_reports": [
                    {
                        "date": d.report_date.isoformat(),
                        "today": d.today,
                        "blockers": d.blockers,
                    }
                    for d in dailies[-5:]
                ],
                "last_one_on_one": (
                    {
                        "date": one_on_ones[-1].held_at.date().isoformat(),
                        "topics": one_on_ones[-1].topics,
                        "notes": one_on_ones[-1].notes[:240],
                    }
                    if one_on_ones
                    else None
                ),
            }
        )
    return json.dumps(snapshot, ensure_ascii=False, default=str)


def _resolve_style(
    style: str | None,
    style_instructions: str | None,
) -> tuple[str, float]:
    """Pick the style addendum + temperature based on caller hints."""
    if style == "custom" and style_instructions:
        return (
            f"回答スタイルは『カスタム』。EM 自身が指定した指示に従ってください：\n{style_instructions.strip()}",
            0.5,
        )
    preset = STYLE_PRESETS.get(style or "standard", STYLE_PRESETS["standard"])
    instructions = str(preset.get("instructions", ""))
    temperature = float(preset.get("temperature", 0.4))
    if style_instructions:
        instructions += (
            "\n\n追加で次の指示も加味してください（プリセットと矛盾する場合はこちらを優先）：\n"
            + style_instructions.strip()
        )
    return instructions, temperature


async def chat_with_em(
    history: list[ChatMessage],
    *,
    em_member_id: str,
    style: str | None = "standard",
    style_instructions: str | None = None,
) -> str:
    loader = DataLoader()
    context_blob = _context_snapshot(loader)
    style_addendum, temperature = _resolve_style(style, style_instructions)

    messages = [
        {"role": "system", "content": BASE_PROMPT + "\n\n" + style_addendum},
        {
            "role": "system",
            "content": (
                f"以下が現在のチームの最新スナップショットです (EM: {em_member_id}):\n\n"
                + context_blob
            ),
        },
    ]
    # Keep only the last 10 turns to stay within token budget.
    for msg in history[-10:]:
        messages.append({"role": msg.role, "content": msg.content})

    return await chat_complete(
        messages=messages,
        temperature=temperature,
        max_tokens=900,
    )


def list_style_presets() -> list[dict[str, str]]:
    """Return preset metadata for the frontend's style picker."""
    return [
        {"key": key, "label": str(preset.get("label", key))}
        for key, preset in STYLE_PRESETS.items()
    ]
