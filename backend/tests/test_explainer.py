"""
Tests for the LLM signal explainer (app.analysis.explainer).

All tests mock LangChain/OpenAI — no real API calls are made.
Tests verify:
  1. Graceful disable when llm_enabled=False
  2. Graceful disable when openai_api_key=""
  3. Prompt template renders correct verified indicator values
  4. Returns "" on LangChain error (no exception propagation)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.analysis.explainer import generate_explanation, _build_prompt_values
from app.analysis.indicators import IndicatorSet


def _make_indicator_set(
    symbol="AAPL",
    interval="1D",
    rsi_14=32.5,
    macd_val=0.12,
    macd_signal=0.08,
    macd_hist=0.04,
    bb_upper=155.0,
    bb_lower=140.0,
    bb_pct=0.15,
    adx_14=28.3,
    atr_14=2.5,
    ema_50=148.0,
    ema_200=145.0,
    vol_sma_20=50_000_000.0,
    close=143.0,
    volume=60_000_000.0,
) -> IndicatorSet:
    return IndicatorSet(
        symbol=symbol,
        interval=interval,
        rsi_14=rsi_14,
        macd_val=macd_val,
        macd_signal=macd_signal,
        macd_hist=macd_hist,
        bb_upper=bb_upper,
        bb_lower=bb_lower,
        bb_pct=bb_pct,
        adx_14=adx_14,
        atr_14=atr_14,
        ema_50=ema_50,
        ema_200=ema_200,
        vol_sma_20=vol_sma_20,
        close=close,
        volume=volume,
    )


@pytest.mark.asyncio
async def test_generate_explanation_disabled_llm_enabled_false():
    """Returns empty string when llm_enabled=False — no LangChain calls."""
    ind = _make_indicator_set()
    mock_settings = MagicMock()
    mock_settings.llm_enabled = False
    mock_settings.openai_api_key = "sk-fake-key"

    with patch("app.analysis.explainer.settings", mock_settings):
        result = await generate_explanation("AAPL", "BUY", 75, ind, ["RSI oversold (32.5)"])

    assert result == ""


@pytest.mark.asyncio
async def test_generate_explanation_disabled_no_api_key():
    """Returns empty string when openai_api_key="" — no LangChain calls."""
    ind = _make_indicator_set()
    mock_settings = MagicMock()
    mock_settings.llm_enabled = True
    mock_settings.openai_api_key = ""

    with patch("app.analysis.explainer.settings", mock_settings):
        result = await generate_explanation("AAPL", "BUY", 75, ind, [])

    assert result == ""


@pytest.mark.asyncio
async def test_generate_explanation_calls_langchain_when_enabled():
    """When LLM enabled, calls LangChain chain and returns content."""
    ind = _make_indicator_set()
    mock_settings = MagicMock()
    mock_settings.llm_enabled = True
    mock_settings.openai_api_key = "sk-fake-key"

    fake_response = MagicMock()
    fake_response.content = "RSI at 32.5 signals oversold conditions. MACD above signal line confirms bullish momentum. ATR-based volatility at 1.7% of price."

    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=fake_response)

    mock_llm_instance = MagicMock()
    mock_prompt_instance = MagicMock()
    mock_prompt_instance.__or__ = MagicMock(return_value=mock_chain)

    mock_chat_openai_cls = MagicMock(return_value=mock_llm_instance)
    mock_prompt_template_cls = MagicMock(return_value=mock_prompt_instance)

    import sys
    # Inject mock modules so deferred imports inside function resolve to mocks
    mock_langchain_openai = MagicMock()
    mock_langchain_openai.ChatOpenAI = mock_chat_openai_cls
    mock_langchain_core_prompts = MagicMock()
    mock_langchain_core_prompts.PromptTemplate = mock_prompt_template_cls

    with (
        patch("app.analysis.explainer.settings", mock_settings),
        patch.dict(sys.modules, {
            "langchain_openai": mock_langchain_openai,
            "langchain_core.prompts": mock_langchain_core_prompts,
        }),
    ):
        result = await generate_explanation(
            "AAPL", "BUY", 75, ind, ["RSI oversold (32.5)", "MACD above signal line"]
        )

    assert "RSI" in result
    assert result != ""


@pytest.mark.asyncio
async def test_generate_explanation_returns_empty_on_langchain_error():
    """Returns "" without raising if LangChain raises an exception."""
    import sys
    ind = _make_indicator_set()
    mock_settings = MagicMock()
    mock_settings.llm_enabled = True
    mock_settings.openai_api_key = "sk-fake-key"

    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(side_effect=RuntimeError("API connection failed"))

    mock_llm_instance = MagicMock()
    mock_prompt_instance = MagicMock()
    mock_prompt_instance.__or__ = MagicMock(return_value=mock_chain)

    mock_langchain_openai = MagicMock()
    mock_langchain_openai.ChatOpenAI = MagicMock(return_value=mock_llm_instance)
    mock_langchain_core_prompts = MagicMock()
    mock_langchain_core_prompts.PromptTemplate = MagicMock(return_value=mock_prompt_instance)

    with (
        patch("app.analysis.explainer.settings", mock_settings),
        patch.dict(sys.modules, {
            "langchain_openai": mock_langchain_openai,
            "langchain_core.prompts": mock_langchain_core_prompts,
        }),
    ):
        result = await generate_explanation("AAPL", "BUY", 75, ind, [])

    assert result == ""


def test_build_prompt_values_rsi_oversold():
    """Template values include correct RSI oversold note."""
    ind = _make_indicator_set(rsi_14=28.0)
    values = _build_prompt_values("AAPL", "BUY", 80, ind, ["RSI oversold (28.0)"])
    assert values["rsi_14"] == "28.0"
    assert "oversold" in values["rsi_note"]


def test_build_prompt_values_rsi_overbought():
    """Template values include correct RSI overbought note."""
    ind = _make_indicator_set(rsi_14=72.0)
    values = _build_prompt_values("AAPL", "SELL", 70, ind, [])
    assert "overbought" in values["rsi_note"]


def test_build_prompt_values_macd_above():
    """MACD status shows 'above' when macd_val > macd_signal."""
    ind = _make_indicator_set(macd_val=0.5, macd_signal=0.2)
    values = _build_prompt_values("AAPL", "BUY", 75, ind, [])
    assert "above" in values["macd_status"]


def test_build_prompt_values_macd_below():
    """MACD status shows 'below' when macd_val < macd_signal."""
    ind = _make_indicator_set(macd_val=0.1, macd_signal=0.4)
    values = _build_prompt_values("AAPL", "SELL", 65, ind, [])
    assert "below" in values["macd_status"]


def test_build_prompt_values_atr_pct_calculated():
    """ATR percentage of price is correctly computed."""
    ind = _make_indicator_set(atr_14=2.5, close=100.0)
    values = _build_prompt_values("AAPL", "BUY", 75, ind, [])
    # atr_pct = 2.5 / 100 * 100 = 2.5%
    assert values["atr_pct_note"] == "2.5"


def test_build_prompt_values_none_indicators():
    """Template handles None indicator values gracefully."""
    ind = _make_indicator_set(rsi_14=None, macd_val=None, macd_signal=None)
    values = _build_prompt_values("AAPL", "HOLD", 40, ind, [])
    assert values["rsi_14"] == "N/A"
    assert values["macd_status"] == "N/A"
    assert values["rsi_note"] == ""
