"""
Market scanner: iterates monitored assets, runs each registered strategy,
and upserts results to the signals table.

Design:
  - scan_asset(): for ONE asset + ONE strategy, computes indicators and upserts
  - scan_all_assets(): iterates strategies × (STOCK_WATCHLIST + CCXT_CRYPTO_SYMBOLS)
  - analysis_scan_job(): async APScheduler wrapper -- called by scheduler.py

Strategy abstraction:
  Each strategy is a BaseStrategy instance. The default is BaselineStrategy
  (the legacy scoring rules). Additional strategies coexist on the same
  (symbol, interval) — the PK includes strategy_name. The signals table is
  upserted with ON CONFLICT (symbol, interval, strategy_name) DO UPDATE so
  every scan refreshes the row in place.

Anti-patterns avoided:
  - Indicators computed once per (asset, scan) — even for multiple strategies
    we still call compute_indicators() per asset to avoid double work via
    caching at the IndicatorSet layer (TODO: per-asset memoization is future).
  - Strategy errors are caught per-asset — one bad strategy never crashes
    the scan loop.
"""
import json
import logging
from datetime import datetime, timezone

import pandas as pd
import pandas_ta_classic as ta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.explainer import generate_explanation
from app.analysis.indicators import MIN_CANDLES, IndicatorSet, compute_indicators
from app.analysis.llm_advisor import get_llm_advisory
from app.analysis.multiframe import compute_multiframe_agreement
from app.analysis.regime import detect_regime
from app.analysis.signals import apply_llm_advisory
from app.core.database import async_session_factory
from app.core.watchlists import CCXT_CRYPTO_SYMBOLS, STOCK_WATCHLIST
from app.models.signal import TradingSignal
from app.strategies import STRATEGY_REGISTRY
from app.strategies.base import BaseStrategy
from app.strategies.baseline import BaselineStrategy

__all__ = [
    "SCAN_INTERVAL",
    "DEFAULT_STRATEGIES",
    "scan_asset",
    "scan_all_assets",
    "analysis_scan_job",
]

log = logging.getLogger(__name__)

#: Primary timeframe for signal generation. Multi-timeframe deferred to Phase 7.
SCAN_INTERVAL: str = "1d"

#: Fetch slightly more candles than MIN_CANDLES to compute ATR SMA
_FETCH_LIMIT: int = MIN_CANDLES + 20


def _default_strategies() -> list[BaseStrategy]:
    """Default to baseline only. To enable more strategies in production, set
    the SCANNER_STRATEGIES env var or pass an explicit list to scan_all_assets()."""
    return [BaselineStrategy()]


DEFAULT_STRATEGIES = _default_strategies


async def scan_asset(
    symbol: str,
    market: str,
    session: AsyncSession,
    strategy: BaseStrategy | None = None,
) -> TradingSignal | None:
    """Fetch candles for one asset, run ``strategy`` over them, upsert to DB.

    Returns None if insufficient candle history (< MIN_CANDLES rows).
    Returns the upserted TradingSignal on success.

    Args:
        symbol: Asset symbol (e.g. "AAPL", "BTC/USDT").
        market: "stock" or "crypto".
        session: Active SQLAlchemy async session (caller manages lifecycle).
        strategy: BaseStrategy instance. Defaults to BaselineStrategy().
    """
    if strategy is None:
        strategy = BaselineStrategy()

    result = await session.execute(
        text("""
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = :symbol AND interval = :interval
            ORDER BY timestamp ASC
            LIMIT :limit
        """),
        {"symbol": symbol, "interval": SCAN_INTERVAL, "limit": _FETCH_LIMIT},
    )
    rows = result.fetchall()

    if len(rows) < MIN_CANDLES:
        log.debug(
            "scan_asset: skipping %s -- only %d candles (need %d)",
            symbol,
            len(rows),
            MIN_CANDLES,
        )
        return None

    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp")

    ind = compute_indicators(df, symbol=symbol, interval=SCAN_INTERVAL)
    if ind is None:
        return None

    atr_sma_20: float | None = None
    atr_series = ta.atr(df["high"], df["low"], df["close"], length=14)
    if atr_series is not None:
        atr_sma = atr_series.rolling(window=20).mean()
        vals = atr_sma.dropna()
        if len(vals) > 0:
            atr_sma_20 = float(vals.iloc[-1])

    regime = detect_regime(ind, atr_sma_20=atr_sma_20)
    signal = strategy.generate_signal(ind)

    # LLM advisory: review indicators and adjust confidence (no-op if disabled)
    advisory = await get_llm_advisory(
        ind=ind,
        regime=regime,
        direction=signal.direction,
        confidence=signal.confidence,
    )
    signal = apply_llm_advisory(signal, advisory)

    explanation = await generate_explanation(
        symbol=symbol,
        direction=signal.direction,
        confidence=signal.confidence,
        ind=ind,
        reasons=signal.reasons,
    )

    multiframe = await compute_multiframe_agreement(symbol, session)

    now = datetime.now(tz=timezone.utc)

    await session.execute(
        text("""
            INSERT INTO signals
                (symbol, interval, strategy_name, scanned_at, direction, confidence, regime,
                 close, entry_price, stop_loss, target_price,
                 rsi_14, macd_val, adx_14, atr_14, reasons,
                 explanation, multiframe_agreement,
                 llm_adjustment, llm_reasoning, llm_patterns)
            VALUES
                (:symbol, :interval, :strategy_name, :scanned_at, :direction, :confidence, :regime,
                 :close, :entry_price, :stop_loss, :target_price,
                 :rsi_14, :macd_val, :adx_14, :atr_14, :reasons,
                 :explanation, :multiframe_agreement,
                 :llm_adjustment, :llm_reasoning, :llm_patterns)
            ON CONFLICT (symbol, interval, strategy_name) DO UPDATE SET
                scanned_at            = excluded.scanned_at,
                direction             = excluded.direction,
                confidence            = excluded.confidence,
                regime                = excluded.regime,
                close                 = excluded.close,
                entry_price           = excluded.entry_price,
                stop_loss             = excluded.stop_loss,
                target_price          = excluded.target_price,
                rsi_14                = excluded.rsi_14,
                macd_val              = excluded.macd_val,
                adx_14                = excluded.adx_14,
                atr_14                = excluded.atr_14,
                reasons               = excluded.reasons,
                explanation           = excluded.explanation,
                multiframe_agreement  = excluded.multiframe_agreement,
                llm_adjustment        = excluded.llm_adjustment,
                llm_reasoning         = excluded.llm_reasoning,
                llm_patterns          = excluded.llm_patterns
        """),
        {
            "symbol": symbol,
            "interval": SCAN_INTERVAL,
            "strategy_name": strategy.name,
            "scanned_at": now,
            "direction": signal.direction,
            "confidence": signal.confidence,
            "regime": regime,
            "close": ind.close,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "target_price": signal.target_price,
            "rsi_14": ind.rsi_14,
            "macd_val": ind.macd_val,
            "adx_14": ind.adx_14,
            "atr_14": ind.atr_14,
            "reasons": json.dumps(signal.reasons),
            "explanation": explanation,
            "multiframe_agreement": json.dumps(multiframe),
            "llm_adjustment": signal.llm_adjustment,
            "llm_reasoning": signal.llm_reasoning,
            "llm_patterns": json.dumps(signal.llm_patterns),
        },
    )
    await session.commit()

    log.info(
        "scan_asset: %s [%s] -> %s (confidence=%d, regime=%s)",
        symbol,
        strategy.name,
        signal.direction,
        signal.confidence,
        regime,
    )

    return TradingSignal(
        symbol=symbol,
        interval=SCAN_INTERVAL,
        strategy_name=strategy.name,
        scanned_at=now,
        direction=signal.direction,
        confidence=signal.confidence,
        regime=regime,
        close=ind.close,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss,
        target_price=signal.target_price,
        rsi_14=ind.rsi_14,
        macd_val=ind.macd_val,
        adx_14=ind.adx_14,
        atr_14=ind.atr_14,
        reasons=json.dumps(signal.reasons),
        explanation=explanation,
        multiframe_agreement=json.dumps(multiframe),
        llm_adjustment=signal.llm_adjustment,
        llm_reasoning=signal.llm_reasoning,
        llm_patterns=json.dumps(signal.llm_patterns),
    )


async def scan_all_assets(
    session: AsyncSession,
    strategies: list[BaseStrategy] | None = None,
) -> int:
    """Scan all monitored assets across all selected strategies.

    Iterates ``strategies × (STOCK_WATCHLIST + CCXT_CRYPTO_SYMBOLS)``. Assets
    with insufficient history are silently skipped. Individual asset/strategy
    failures are caught and logged so one bad combination cannot crash the
    full scan.

    Args:
        session: Active async session.
        strategies: Strategies to run. Defaults to [BaselineStrategy()] —
            preserves the pre-pluggable-interface behavior.

    Returns:
        Number of (symbol, strategy) signals successfully upserted.
    """
    if strategies is None:
        strategies = _default_strategies()

    scanned = 0

    for strategy in strategies:
        for symbol in STOCK_WATCHLIST:
            try:
                result = await scan_asset(symbol, "stock", session, strategy=strategy)
                if result is not None:
                    scanned += 1
            except Exception as exc:
                log.error(
                    "scan_all_assets: error scanning stock %s with %s: %s",
                    symbol,
                    strategy.name,
                    exc,
                )

        for symbol in CCXT_CRYPTO_SYMBOLS:
            try:
                result = await scan_asset(symbol, "crypto", session, strategy=strategy)
                if result is not None:
                    scanned += 1
            except Exception as exc:
                log.error(
                    "scan_all_assets: error scanning crypto %s with %s: %s",
                    symbol,
                    strategy.name,
                    exc,
                )

    log.info(
        "scan_all_assets: complete -- %d signals upserted across %d strategies",
        scanned,
        len(strategies),
    )
    return scanned


async def analysis_scan_job() -> None:
    """APScheduler job wrapper for scan_all_assets()."""
    try:
        async with async_session_factory() as session:
            count = await scan_all_assets(session)
            log.info("analysis_scan_job: complete -- %d signals", count)
    except Exception as exc:
        log.error("analysis_scan_job: fatal error: %s", exc)
