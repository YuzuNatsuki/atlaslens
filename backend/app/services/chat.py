"""Chat assistant — EM-only. Conversational, grounded on AtlasCorp data."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel

from app.core.azure_clients import chat_complete
from app.services.data_loader import DataLoader


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


SYSTEM_PROMPT = """\
あなたは AtlasLens の EM 用 AI アシスタントです。Microsoft Azure 上の Foundry で
動作し、AtlasCorp というチーム (5 名) の最新データ (プロフィール / OKR / 日報 /
1on1 / 議事録) にアクセスできます。

EM（マネージャー）からの質問に、以下を守って答えてください：

- 日本語の自然な敬体（ですます調）で、簡潔に。長文は避け、要点を箇条書きに。
- 推測ではなく与えられたデータを根拠にする。出典は member_id / 日付で示す。
- メンバーの感情や性格は推測しない。観測可能な行動だけ言及する。
- 比較や評価をするときは、攻撃的でない言い回しを選ぶ
  （例: ×「Aさんは遅れている」→ ○「Aさんの目標進捗は X% で、計画より少し
  ゆっくりに見えます」）。
- 情報が足りないときは「データには含まれていません」と素直に伝え、追加で見るべき
  ファイル/メンバーを提案する。
- 1on1 や評価に役立つフォローアップ質問があれば最後に 1–2 個だけ添える。
"""


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


async def chat_with_em(
    history: list[ChatMessage],
    *,
    em_member_id: str,
) -> str:
    loader = DataLoader()
    context_blob = _context_snapshot(loader)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
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
        temperature=0.4,
        max_tokens=900,
    )
