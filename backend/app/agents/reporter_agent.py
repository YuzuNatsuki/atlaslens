"""Reporter Agent — uses Azure OpenAI (under the Foundry resource)."""

from __future__ import annotations

import json

from app.core.azure_clients import chat_complete

DAILY_DRAFT_SYSTEM_PROMPT = """\
あなたは AtlasLens の "Reporter" です。本人のメモと直近数日の日報をもとに、
今日の日報の下書きを作ります。

以下の JSON 形式で返してください。日本のチームで自然な日報の書き方に合わせ、
箇条書きベース、敬体（〜しました／〜します）。

{
  "yesterday": "<200字以内・昨日やったことを箇条書き調で>",
  "today": "<200字以内・今日やることを箇条書き調で>",
  "blockers": "<200字以内・困りごと。なければ空文字列>",
  "suggested_mood": <1〜5 の整数 / 不明なら null>
}

ルール：
- 各セクションは 2〜4 個の短い項目に絞る。
- 「〜だった」「〜した」のような客観的な書き方。誇張は避ける。
- ブロッカーは事実だけ。原因の決めつけはしない。
- 出力は JSON のみ。
"""


async def draft_member_daily(
    member_name: str,
    bullet_hints: list[str],
    recent_history: list[dict],
) -> dict:
    payload = {
        "member": member_name,
        "hints": bullet_hints,
        "recent_history": recent_history,
    }
    user_prompt = (
        "Draft today's daily report for this member. Output JSON as specified.\n\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
    )
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": DAILY_DRAFT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
        max_tokens=400,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True}


TEAM_SUMMARY_SYSTEM_PROMPT = """\
あなたは AtlasLens の "Reporter" です。EM が朝会前に 30 秒でチームの状況を
つかめるよう、1 日分の日報を要約します。

以下の JSON 形式で返してください。すべて日本語の敬体で、簡潔に。

{
  "tldr": ["<80字以内・今日の見どころを 3 つ>", ...],
  "highlights": {
    "<メンバー名>": "<100字以内・今日の主な動き>"
  },
  "blockers_to_surface": {
    "<メンバー名>": "<100字以内・気がかりな点。ない場合はキーごと省略>"
  },
  "themes": ["<80字以内・チーム横断で見える傾向>", ...]
}

ルール：
- tldr はちょうど 3 件。
- highlights は日報を出したメンバー全員ぶん。「○○さん」とは呼ばず、メンバー名
  だけをキーにする。
- blockers_to_surface は本人がブロッカーを書いた人だけ。
- themes は 2〜3 件。複数メンバーに共通する話題があれば挙げる。
- 評価ではなく事実を伝える。「遅れている」「頑張った」など主観は使わない。
- 出力は JSON のみ。
"""


async def summarize_day(reports: list[dict], member_index: dict[str, str]) -> dict:
    payload = {"reports": reports, "members": member_index}
    user_prompt = (
        "Summarize today's team for the EM as JSON.\n\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
    )
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": TEAM_SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
        max_tokens=700,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True}
