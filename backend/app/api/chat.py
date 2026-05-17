"""Chat API — EM-only conversational assistant."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import AuthContext, get_auth_context, require_em
from app.services.chat import ChatMessage, chat_with_em, list_style_presets

router = APIRouter()


async def _em_only(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    return await require_em(auth)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    style: str | None = Field(default="standard")
    style_instructions: str | None = Field(default=None)


class ChatResponse(BaseModel):
    reply: str
    style: str | None = None


@router.get("/styles")
async def styles(_: AuthContext = Depends(_em_only)) -> dict:
    """List preset reply styles for the picker."""
    return {"styles": list_style_presets()}


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, auth: AuthContext = Depends(_em_only)) -> ChatResponse:
    reply = await chat_with_em(
        payload.messages,
        em_member_id=auth.member_id,
        style=payload.style,
        style_instructions=payload.style_instructions,
    )
    return ChatResponse(reply=reply, style=payload.style)
