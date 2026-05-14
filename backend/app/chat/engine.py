"""
backend/app/chat/engine.py
LLM chat response generator. Wraps ChatOpenAI with OpenRouter.
Pure async function — no DB, no FastAPI imports.

RELEVANT FILES: app/chat/context_builder.py, app/api/routes/chat.py, app/core/config.py
"""
import logging

from app.core.config import settings

__all__ = ["generate_chat_response"]

log = logging.getLogger(__name__)


async def generate_chat_response(
    system_prompt: str,
    user_message: str,
    history: list[dict] | None = None,
    model_override: str | None = None,
) -> str:
    """
    Generate a chat response using OpenRouter via LangChain's ChatOpenAI.

    Args:
        system_prompt: System prompt with persona + context + knowledge.
        user_message: The user's current message.
        history: Optional list of {"role": "user"|"assistant", "content": str} dicts
                 for conversation continuity (last 5 messages max).
        model_override: Optional model ID to use instead of the default OPENROUTER_MODEL.
                       Allows users to pick a model from the chat widget.

    Returns:
        LLM response string, or a fallback message if LLM is unavailable or errors.
    """
    if not settings.openrouter_api_key:
        return "Chat is not available — no OpenRouter API key configured. Set OPENROUTER_API_KEY in your .env file."

    try:
        # Deferred imports — no crash if langchain not installed when llm_enabled=False
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # noqa: PLC0415
        from langchain_openai import ChatOpenAI  # noqa: PLC0415

        model = model_override or settings.openrouter_model

        llm = ChatOpenAI(
            model=model,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.4,
            max_tokens=500,
            default_headers={
                "HTTP-Referer": settings.frontend_url,
                "X-Title": "Trading Bot",
            },
        )

        # Build message list: system + history + current user message
        messages = [SystemMessage(content=system_prompt)]

        # Add conversation history (last 5 exchanges for context continuity)
        if history:
            for msg in history[-10:]:  # Max 10 messages (5 exchanges)
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=user_message))

        response = await llm.ainvoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        return content.strip()

    except Exception as exc:
        log.warning("generate_chat_response: failed: %s", exc)
        return "Sorry, I couldn't generate a response right now. Please try again in a moment."
