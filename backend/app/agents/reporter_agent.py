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
あなたは AtlasLens の "Reporter" です。朝会前に 30 秒でチームの状況を
つかめるよう、1 日分の日報を要約します。

入力 (reports[]) には各メンバーの `member_name` (例: "田中 健") と
`member_id` (例: "mem001") が同梱されています。出力のキーには
**必ず `member_name` をそのまま** 使ってください。`member_id` を出力に
使うのは禁止です。

以下の JSON 形式で返してください。すべて日本語の敬体で、簡潔に。

{
  "tldr": ["<80字以内・今日の見どころを 3 つ>", ...],
  "highlights": {
    "<member_name の値>": "<100字以内・今日の主な動き>"
  },
  "blockers_to_surface": {
    "<member_name の値>": "<100字以内・気がかりな点。ない場合はキーごと省略>"
  },
  "themes": ["<80字以内・チーム横断で見える傾向>", ...]
}

ルール：
- tldr はちょうど 3 件。
- highlights は日報を出したメンバー全員ぶん。キーは必ず member_name
  (例: "田中 健")。"mem001" のような ID を出力に書いてはいけません。
- 「○○さん」のような敬称や役職は付けず、member_name の文字列をそのまま使う。
- blockers_to_surface は本人がブロッカーを書いた人だけ。空ならキー自体を省略。
- themes は 2〜3 件。複数メンバーに共通する話題があれば挙げる。
- 評価ではなく事実を伝える。「遅れている」「頑張った」など主観は使わない。
- 出力は JSON のみ。
"""


async def summarize_day(
    reports: list[dict],
    member_index: dict[str, str],
    *,
    memory_block: str | None = None,
) -> dict:
    payload = {"reports": reports, "members": member_index}
    user_prompt = (
        "Summarize today's team status as JSON.\n\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
    )
    system_messages: list[dict] = [
        {"role": "system", "content": TEAM_SUMMARY_SYSTEM_PROMPT},
    ]
    if memory_block:
        system_messages.append({"role": "system", "content": memory_block})
    raw = await chat_complete(
        messages=system_messages + [{"role": "user", "content": user_prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
        max_tokens=700,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True}


RANGE_SUMMARY_SYSTEM_PROMPT = """\
あなたは AtlasLens の "Reporter" です。複数日（数日〜数週間）の日報を
横断的に把握できるよう、期間サマリーを作ります。単日サマリーと違い、
1 日のスナップショットではなく「期間内に見えた変化・繰り返し・兆候」を捉えます。

入力 (reports[]) には各日の日報が `member_name`, `member_id`, `report_date`,
`yesterday`, `today`, `blockers` の構造で並んでいます。出力のキーには **必ず
`member_name` をそのまま** 使ってください。`member_id` を出力に使うのは禁止です。

以下の JSON 形式で返してください。すべて日本語の敬体で、簡潔に。

{
  "tldr": ["<期間全体の見どころを 3 件、各 100字以内>", ...],
  "themes": ["<期間横断で複数メンバーに見えるテーマを 2〜4 件、各 100字以内>", ...],
  "by_member": {
    "<member_name の値>": {
      "summary": "<その期間のその人の動きを 150字以内で要約>",
      "trend": "<良化 / 停滞 / 悪化 / 不変 のいずれか>",
      "evidence_dates": ["YYYY-MM-DD", ...]
    }
  },
  "risk_signals": [
    {
      "member_name": "<member_name>",
      "kind": "<retention / friction / capacity / engagement / health のいずれか>",
      "summary": "<具体的な兆候と根拠を 150字以内で>",
      "evidence_dates": ["YYYY-MM-DD", ...]
    }
  ],
  "recommended_actions": [
    "<今週中に取れる具体的アクションを 3〜5 件。〜してください 調>"
  ]
}

ルール：
- tldr はちょうど 3 件。
- by_member は期間内に 1 件でも日報を書いた人を全員カバー。
- trend は本人が書いた事実のみから判断（昇格・評価の主観を投影しない）。
- risk_signals は「兆候があるとき」のみ列挙。なければ空配列。
  - retention: 退職検討・外部選考に関する記述
  - friction: 特定メンバーとの不和や、過剰な遠慮の記述
  - capacity: 過負荷・残業・余裕のなさの記述
  - engagement: 1on1 未設定 / 評価軸見えない / 取り残されている記述
  - health: 体調・休暇・バーンアウト兆候の記述
- evidence_dates は本人が当該記述を書いた日報の日付（実在するもののみ）。
- recommended_actions は監視ではなく対話の促し。「監視を強化」のような表現は禁止。
- 評価・感情の推測は禁止。本人が書いた事実のみを根拠にする。
- 出力は JSON のみ。
"""


async def summarize_range(
    reports: list[dict],
    member_index: dict[str, str],
    *,
    memory_block: str | None = None,
) -> dict:
    payload = {"reports": reports, "members": member_index}
    user_prompt = (
        "Summarize the team over the given range as JSON.\n\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
    )
    system_messages: list[dict] = [
        {"role": "system", "content": RANGE_SUMMARY_SYSTEM_PROMPT},
    ]
    if memory_block:
        system_messages.append({"role": "system", "content": memory_block})
    raw = await chat_complete(
        messages=system_messages + [{"role": "user", "content": user_prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
        max_tokens=1600,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True}
