"""EM Chat — Agentic. Backed by Azure OpenAI function calling.

The agent autonomously decides which AtlasLens tools to call based on the EM's
question, and returns both the final reply and a transcript of tool invocations
so the UI can show the reasoning step-by-step.

Style picker semantics from the previous version are preserved.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel

from app.core.azure_clients import get_openai_client
from app.core.config import get_settings
from app.services import agent_memory
from app.services.agent_tools import TOOL_DEFINITIONS, dispatch
from app.services.data_loader import DataLoader


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ToolCallTrace(BaseModel):
    name: str
    arguments: dict
    result_preview: str  # first ~400 chars so the UI can show it
    elapsed_ms: int


BASE_PROMPT = """\
あなたは AtlasLens の EM 向け AI エージェントです。Microsoft Azure 上の Foundry で
動作し、必要に応じてツールを能動的に呼んでアトラス株式会社の最新データを引きます。

基本原則（すべてのスタイルに共通・必ず守る）：
- 質問を受けたら、答えるのに必要な情報を考え、最適なツールを 1 つ以上呼ぶ。
- ツールの戻り値が不足していれば、別のツールを追加で呼んで補強する。
- 推測ではなくツールで取った事実を根拠にする。参照元は member_id / 日付 / ツール名。
- メンバーの感情や性格は推測しない。観測可能な行動だけ言及する。
- 評価ではなく支援を意図する。攻撃的・断定的な言い回しは避ける。
- 情報が足りないときは「データには含まれていません」と素直に伝える。
- 日本語の自然な敬体で答える。

回答の長さ・構成・トーンは、後述する『回答スタイル』の指示に厳密に従ってください。
スタイル指示と上記の基本原則が矛盾する場合のみ基本原則を優先し、それ以外は
スタイルが指定する書式（短さ、見出しの有無、口調）を最優先で尊重します。
"""


STYLE_PRESETS: dict[str, dict[str, str | float]] = {
    "standard": {
        "label": "標準（バランス型）",
        "instructions": (
            "回答スタイルは『標準』。次の 3 段構成で答えてください：\n"
            "1. 観察された事実（参照元 id と日付つきで具体的に）\n"
            "2. 解釈・考えられる背景（事実から何が読み取れるか）\n"
            "3. そう判断した理由と、EM が取り得る次のアクション候補\n"
            "見出しや箇条書きを適度に使い、文章量は 200〜500 字目安。"
            "最後に 1〜2 個のフォローアップ質問を添える。"
        ),
        "temperature": 0.4,
    },
    "concise": {
        "label": "短く一言",
        "instructions": (
            "回答スタイルは『短く一言』。**1〜3 文の平文のみ**で答えてください。"
            "結論だけを短く伝え、見出し・箇条書き・絵文字は一切使わない。"
            "詳細な事実列挙や 3 段構成は省略し、もっとも重要な一言にまとめる。"
            "必要なら参照元を末尾に括弧書きで 1 件だけ添える。"
            "フォローアップ質問は付けない。"
            "（基本原則の『事実根拠』だけは守りつつ、長さは厳密に 1〜3 文に絞ってください）"
        ),
        "temperature": 0.3,
    },
    "bullet": {
        "label": "箇条書きのみ",
        "instructions": (
            "回答スタイルは『箇条書きのみ』。前置きや要約は書かず、要点を箇条書きだけで"
            "並べる。各項目は 30 字以内、最大 5 件。見出しや段落は使わない。"
        ),
        "temperature": 0.3,
    },
    "coaching": {
        "label": "問いかけ型（気づきを引き出す）",
        "instructions": (
            "回答スタイルは『問いかけ型』。まず直接的な答えを 1 つに絞って簡潔に書き、"
            "次に EM 自身に考えてもらう問いを 2〜3 個返してください。"
            "答えは決めつけず、選択肢を示す。問いは具体的で、データに即したものにする。"
            "文章量は 200〜400 字目安。"
        ),
        "temperature": 0.6,
    },
    "analytical": {
        "label": "分析重視（根拠付き）",
        "instructions": (
            "回答スタイルは『分析重視』。次の順で組み立ててください：\n"
            "1. 結論（データに基づく一文）\n"
            "2. 観察された事実（日付・参照元 id・ツール名を明示）\n"
            "3. 解釈と、そう判断した理由（推論の経路）\n"
            "4. EM が次に取り得るアクション\n"
            "見出しで節を分け、各節は丁寧に書く。文章量は気にせず必要なだけ"
            "（500〜900 字目安）。観察された事実と解釈・推論を明確に分けて書く。"
        ),
        "temperature": 0.2,
    },
    "casual": {
        "label": "カジュアル（雑談調）",
        "instructions": (
            "回答スタイルは『カジュアル』。Slack の DM で話しかけるように、"
            "肩肘張らない柔らかな言い回しで答えてください。"
            "段落 2〜3 個、各段落 1〜2 文程度の短さに収める。"
            "**見出しや凝った箇条書きは使わない**（必要なら『・』を 2〜3 行だけ）。"
            "「〜ですね」「〜してみるとよさそうです」のような提案調で締める。"
            "敬語は崩しすぎない。絵文字は最大 1 個まで。文章量は 100〜250 字目安。"
        ),
        "temperature": 0.7,
    },
}


def list_style_presets() -> list[dict[str, str]]:
    return [
        {"key": key, "label": str(preset.get("label", key))}
        for key, preset in STYLE_PRESETS.items()
    ]


def _resolve_style(
    style: str | None, style_instructions: str | None
) -> tuple[str, float]:
    if style == "custom" and style_instructions:
        return (
            f"回答スタイルは『カスタム』。EM が指定した指示に従ってください：\n{style_instructions.strip()}",
            0.5,
        )
    preset = STYLE_PRESETS.get(style or "standard", STYLE_PRESETS["standard"])
    addendum = str(preset.get("instructions", ""))
    temperature = float(preset.get("temperature", 0.4))
    if style_instructions:
        addendum += (
            "\n\n追加で次の指示も加味してください（プリセットと矛盾する場合はこちらを優先）：\n"
            + style_instructions.strip()
        )
    return addendum, temperature


def _bootstrap_context() -> str:
    """A lightweight team snapshot so the agent has names handy without a tool call."""
    loader = DataLoader()
    profiles = loader.load_profiles()
    return json.dumps(
        {
            "members": [
                {"id": p.id, "name": p.name, "role": p.role.value, "team_id": p.team_id}
                for p in profiles
            ]
        },
        ensure_ascii=False,
    )


MAX_TOOL_ITERATIONS = 4


async def chat_with_em(
    history: list[ChatMessage],
    *,
    em_member_id: str,
    style: str | None = "standard",
    style_instructions: str | None = None,
) -> dict[str, Any]:
    """Run the agentic chat loop.

    Returns {reply: str, tool_calls: list[ToolCallTrace], style: str}.
    """
    settings = get_settings()
    client = get_openai_client()
    style_addendum, temperature = _resolve_style(style, style_instructions)

    loader = DataLoader()
    member_index = {p.id: p.name for p in loader.load_profiles()}
    memory_block = agent_memory.format_for_prompt(
        em_member_id, member_index=member_index
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": BASE_PROMPT + "\n\n" + style_addendum},
        {
            "role": "system",
            "content": (
                f"EM の member_id は {em_member_id}。チーム一覧 (id/name) は次の通り。"
                f"より深い情報は適切なツールを呼んで取得してください。\n\n"
                + _bootstrap_context()
            ),
        },
    ]
    if memory_block:
        messages.append(
            {
                "role": "system",
                "content": (
                    memory_block
                    + "\n\n上記は他の AtlasLens エージェントも参照する共有メモリです。"
                    "EM が注目しているメンバーに該当する話題なら、回答の中で必ず触れてください。"
                ),
            }
        )
    for msg in history[-10:]:
        messages.append({"role": msg.role, "content": msg.content})

    trace: list[ToolCallTrace] = []
    import time

    for _ in range(MAX_TOOL_ITERATIONS):
        response = await client.chat.completions.create(
            model=settings.azure_openai_chat_deployment,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            temperature=temperature,
            max_tokens=900,
        )
        choice = response.choices[0]
        msg = choice.message

        if msg.tool_calls:
            # Append assistant message with tool_calls.
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )
            for tc in msg.tool_calls:
                t0 = time.monotonic()
                result = await dispatch(tc.function.name, tc.function.arguments)
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                trace.append(
                    ToolCallTrace(
                        name=tc.function.name,
                        arguments=args,
                        result_preview=result[:400],
                        elapsed_ms=elapsed_ms,
                    )
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )
            # Loop again so the model can read the tool results.
            continue

        # No tool calls — assistant produced the final reply.
        return {
            "reply": msg.content or "",
            "tool_calls": [t.model_dump() for t in trace],
            "style": style,
        }

    return {
        "reply": "（ツール呼び出しが上限に達しました。質問を簡潔にして再度試してください）",
        "tool_calls": [t.model_dump() for t in trace],
        "style": style,
    }
