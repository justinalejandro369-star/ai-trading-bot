"""
backend/app/api/routes/chat.py
Chat endpoint for the contextual chatbot widget.
Accepts user messages with dashboard context, returns LLM responses.

RELEVANT FILES: app/chat/engine.py, app/chat/context_builder.py, app/core/rate_limit.py
"""
import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.chat.context_builder import build_system_prompt
from app.chat.engine import generate_chat_response
from app.core.rate_limit import limiter

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """Incoming chat message with dashboard context."""
    message: str = Field(..., min_length=1, max_length=2000)
    context: dict = Field(default_factory=dict)  # { active_tab, symbol?, signals?, portfolio?, backtest? }
    history: list[dict] = Field(default_factory=list, max_length=10)  # Last N messages for continuity
    model: str | None = Field(None, max_length=100)  # Optional model override (e.g. "deepseek/deepseek-r1:free")


class ChatResponse(BaseModel):
    """Chat response from the LLM."""
    reply: str


@router.post("/message", response_model=ChatResponse)
@limiter.limit("10/minute")
async def send_chat_message(
    request: Request,
    body: ChatMessage,
) -> ChatResponse:
    """
    Process a chat message and return an LLM response.

    The system prompt is dynamically built from:
    1. Base trading assistant persona
    2. Active tab context (chart, signals, portfolio, backtest, education)
    3. Relevant knowledge base sections matched by keywords
    4. Conversation history for continuity

    Rate limited to 10 requests/minute per user.
    """
    active_tab = body.context.get("active_tab", "chart")

    # Build context-aware system prompt
    system_prompt = build_system_prompt(
        active_tab=active_tab,
        page_context=body.context,
        user_message=body.message,
    )

    # Generate LLM response with optional model override
    reply = await generate_chat_response(
        system_prompt=system_prompt,
        user_message=body.message,
        history=body.history,
        model_override=body.model,
    )

    log.info("chat: tab=%s, msg_len=%d, reply_len=%d", active_tab, len(body.message), len(reply))
    return ChatResponse(reply=reply)
