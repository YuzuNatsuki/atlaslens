"""Chat API — EM-only Agentic conversational assistant."""

import contextlib

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import AuthContext, get_auth_context, require_em
from app.services import agent_memory, chat_history
from app.services.chat import ChatMessage, chat_with_em, list_style_presets

router = APIRouter()


async def _em_only(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    return await require_em(auth)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    style: str | None = Field(default="standard")
    style_instructions: str | None = Field(default=None)


class ToolCallTrace(BaseModel):
    name: str
    arguments: dict
    result_preview: str
    elapsed_ms: int


class ChatResponse(BaseModel):
    reply: str
    style: str | None = None
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)


class StoredChatMessage(BaseModel):
    role: str
    content: str
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)


class ChatHistoryResponse(BaseModel):
    messages: list[StoredChatMessage] = Field(default_factory=list)
    style: str = "standard"
    style_instructions: str | None = None
    updated_at: str | None = None


@router.get("/history", response_model=ChatHistoryResponse)
async def get_history(auth: AuthContext = Depends(_em_only)) -> ChatHistoryResponse:
    session = chat_history.get_session(auth.member_id)
    if session is None:
        return ChatHistoryResponse()
    return ChatHistoryResponse(
        messages=[
            StoredChatMessage(
                role=m["role"],
                content=m.get("content") or "",
                tool_calls=[
                    ToolCallTrace(**tc) for tc in (m.get("tool_calls") or [])
                ],
            )
            for m in session.get("messages") or []
            if m.get("role") in ("user", "assistant")
        ],
        style=session.get("style") or "standard",
        style_instructions=session.get("style_instructions"),
        updated_at=session.get("updated_at"),
    )


@router.delete("/history", status_code=204)
async def delete_history(auth: AuthContext = Depends(_em_only)) -> None:
    chat_history.clear_session(auth.member_id)


@router.get("/styles")
async def styles(_: AuthContext = Depends(_em_only)) -> dict:
    return {"styles": list_style_presets()}


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, auth: AuthContext = Depends(_em_only)) -> ChatResponse:
    result = await chat_with_em(
        payload.messages,
        em_member_id=auth.member_id,
        style=payload.style,
        style_instructions=payload.style_instructions,
    )
    stored_messages = [
        {"role": m.role, "content": m.content}
        for m in payload.messages
        if m.role in ("user", "assistant")
    ]
    stored_messages.append(
        {
            "role": "assistant",
            "content": result["reply"],
            "tool_calls": result.get("tool_calls") or [],
        }
    )
    chat_history.save_session(
        auth.member_id,
        messages=stored_messages,
        style=payload.style,
        style_instructions=payload.style_instructions,
    )

    # Record the EM's latest question into shared agent memory so other agents
    # (Daily Pulse, growth summary critic, …) know what the EM cares about.
    last_user = next(
        (m for m in reversed(payload.messages) if m.role == "user"),
        None,
    )
    if last_user and last_user.content.strip():
        with contextlib.suppress(Exception):
            agent_memory.record_topic(
                auth.member_id, topic=last_user.content.strip()
            )

    return ChatResponse(**result)
