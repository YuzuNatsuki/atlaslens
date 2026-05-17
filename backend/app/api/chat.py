"""Chat API — EM-only conversational assistant."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import AuthContext, get_auth_context, require_em
from app.services.chat import ChatMessage, chat_with_em

router = APIRouter()


async def _em_only(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    return await require_em(auth)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, auth: AuthContext = Depends(_em_only)) -> ChatResponse:
    reply = await chat_with_em(payload.messages, em_member_id=auth.member_id)
    return ChatResponse(reply=reply)
