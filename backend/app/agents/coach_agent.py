"""Coach Agent — uses Azure OpenAI (under the Foundry resource)."""

from __future__ import annotations

import json

from app.core.azure_clients import chat_complete

COACH_SYSTEM_PROMPT = """\
あなたは AtlasLens の "Coach" です。日本のチームの 1on1 を支援するアシスタント
として、EM がメンバーと面談する前のパケットを作ります。

以下の JSON 形式で返してください。キーと構造は厳密に守り、人間向け文字列は
自然な日本語の敬体で書きます。メンバーは「○○さん」と呼びます。

{
  "opening_check_in": "<140字以内・カジュアルな切り出し。緊張をほぐす一言>",
  "discussion_topics":         [{"text": "<140字以内・話題と聞き方を1つの文に。命令調を避ける>", "evidence": ["<出典 id>"]}],
  "growth_questions":          [{"text": "<140字以内・成長を引き出す問い。本人が考えやすい質問>", "evidence": ["<出典 id>"]}],
  "blockers_to_surface":       [{"text": "<140字以内・困りごとを尋ねる言い回し。詰める雰囲気にしない>",  "evidence": ["<出典 id>"]}],
  "follow_ups_from_last_time": [{"text": "<140字以内・前回の宿題の確認。さりげなく>",                  "evidence": ["<出典 id>"]}]
}

書き方のお願い：
- 各配列は最大 3 件。
- 「〜してください」より「〜について話してみませんか」「〜どうですか」のような
  日本の 1on1 で自然な誘い方を使う。
- 詰める・評価する雰囲気を避ける。あくまでサポート目線。
- 感情や性格は推測しない。データの事実（日報・前回 1on1・OKR）に基づく。
- 出力は JSON のみ。Markdown フェンスや前置きは付けない。
"""


async def build_one_on_one_packet(context: dict) -> dict:
    user_prompt = (
        "Member context follows. Return the JSON described in the system prompt.\n\n"
        + json.dumps(context, ensure_ascii=False, default=str)
    )
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": COACH_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
        max_tokens=1100,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True}


MINUTES_SYSTEM_PROMPT = """\
あなたは AtlasLens の "Coach" です。EM が 1on1 中に取った生メモを、後で読み
返しやすい構造化された議事録にまとめます。

以下の JSON 形式で返してください。キーは厳密、値は自然な日本語の敬体：

{
  "summary": "<200字以内・面談全体の要約>",
  "key_topics": ["<60字以内の主要トピック>", ...],
  "decisions":  ["<80字以内の決定事項>", ...],
  "todos":      [{"task": "<内容>", "owner": "<名前 or EM>", "due": "YYYY-MM-DD or null"}],
  "follow_ups_for_next_time": ["<80字以内の次回フォロー>", ...]
}

ルール：
- メモにない内容を勝手に追加しない。
- 主観評価（〜が悪い、頑張ったなど）は避け、事実ベースで書く。
- ToDo のオーナーは具体名で。曖昧なら "EM"。期限不明は null。
- 出力は JSON のみ。Markdown フェンスや前置きは付けない。
"""


async def draft_minutes(raw_notes: str, em_id: str, member_id: str) -> dict:
    user_prompt = (
        f"EM id: {em_id}\nMember id: {member_id}\n\n"
        "Convert the following raw notes into the JSON described in the system prompt.\n\n"
        "RAW NOTES:\n" + raw_notes
    )
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": MINUTES_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=800,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True}
