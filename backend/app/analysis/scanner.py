"""
Market scanner: iterates all monitored assets, computes indicators, scores signals,
and upserts results to the signals table.

Design:
  - scan_asset(): fetches candles for ONE asset, computes indicators, upserts signal
  - scan_all_assets(): iterates STOCK_WATCHLIST + CCXT_CRYPTO_SYMBOLS
  - analysis_scan_job(): async APScheduler wrapper -- called by scheduler.py

Scan interval: 1D only. Multi-timeframe correlation deferred to Phase 7.

Anti-pattern avoided:
  - Indicators computed once per asset from a single DB query (no N+1)
  - Computation is synchronous pandas -- acceptable at MVP scale (~50 assets, <10ms each)
  - ON CONFLICT DO UPDATE (not DO NOTHING) ensures signals are always refreshed
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
from app.analysis.multiframe import compute_multiframe_agreement
from app.analysis.regime import detect_regime
from app.analysis.signals import score_signal
from app.core.database import async_session_factory
from app.core.watchlists import CCXT_CRYPTO_SYMBOLS, STOCK_WATCHLIST
from app.models.signal import TradingSignal

__all__ = ["SCAN_INTERVAL", "scan_asset", "scan_all_assets", "analysis_scan_job"]

log = logging.getLogger(__name__)

#: Primary timeframe for signal generation. Multi-timeframe deferred to Phase 7.
SCAN_INTERVAL: str = "1D"

#: Fetch slightly more candles than MIN_CANDLES to compute ATR SMA
_FETCH_LIMIT: int = MIN_CANDLES + 20


async def scan_asset(
    symbol: str,
    market: str,
    session: AsyncSession,
) -> TradingSignal | None:
    """
    Fetch candles for one asset, compute indicators + signal, upsert to DB.

    Returns None if insufficient candle history (< MIN_CANDLES rows).
    Returns the upserted TradingSignal on success.

    Args:
        symbol: Asset symbol (e.g. "AAPL", "BTC/USDT")
        market: "stock" or "crypto"
        session: Active SQLAlchemy async session (caller manages lifecycle)
    """
    # Fetch candles ordered ASC (oldest first) for indicator computation
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

    # Compute ATR SMA for regime detection (20-period SMA of ATR column)
    atr_sma_20: float | None = None
    atr_series = ta.atr(df["high"], df["low"], df["close"], length=14)
    if atr_series is not None:
        atr_sma = atr_series.rolling(window=20).mean()
        vals = atr_sma.dropna()
        if len(vals) > 0:
            atr_sma_20 = float(vals.iloc[-1])

    regime = detect_regime(ind, atr_sma_20=atr_sma_20)
    signal = score_signal(ind)

    # Phase 7: generate LLM explanation (gracefully disabled if llm_enabled=False)
    explanation = await generate_explanation(
        symbol=symbol,
        direction=signal.direction,
        confidence=signal.confidence,
        ind=ind,
        reasons=signal.reasons,
    )

    # Phase 7: compute multi-timeframe agreement (reads existing DB signals)
    multiframe = await compute_multiframe_agreement(symbol, session)

    now = datetime.now(tz=timezone.utc)

    # Upsert: ON CONFLICT DO UPDATE refreshes the signal on every scan
    await session.execute(
        text("""
            INSERT INTO signals
                (symbol, interval, scanned_at, direction, confidence, regime,
                 close, entry_price, stop_loss, target_price,
                 rsi_14, macd_val, adx_14, atr_14, reasons,
                 explanation, multiframe_agreement)
            VALUES
                (:symbol, :interval, :scanned_at, :direction, :confidence, :regime,
                 :close, :entry_price, :stop_loss, :target_price,
                 :rsi_14, :macd_val, :adx_14, :atr_14, :reasons,
                 :explanation, :multiframe_agreement)
            ON CONFLICT (symbol, interval) DO UPDATE SET
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
                multiframe_agreement  = excluded.multiframe_agreement
        """),
        {
            "symbol": symbol,
            "interval": SCAN_INTERVAL,
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
        },
    )
    await session.commit()

    log.info(
        "scan_asset: %s -> %s (confidence=%d, regime=%s)",
        symbol,
        signal.direction,
        signal.confidence,
        regime,
    )

    # Return the upserted signal for testing and logging
    return TradingSignal(
        symbol=symbol,
        interval=SCAN_INTERVAL,
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
    )


async def scan_all_assets(session: AsyncSession) -> int:
    """
    Scan all monitored assets: stocks + crypto.

    Iterates STOCK_WATCHLIST and CCXT_CRYPTO_SYMBOLS (from scheduler.py).
    Assets with insufficient history are silently skipped (logged at DEBUG).
    Individual asset failures are caught and logged -- other assets continue.

    Returns:
        Number of signals successfully upserted.
    """
    scanned = 0

    for symbol in STOCK_WATCHLIST:
        try:
            result = await scan_asset(symbol, "stock", session)
            if result is not None:
                scanned += 1
        except Exception as exc:
            log.error("scan_all_assets: error scanning stock %s: %s", symbol, exc)

    for symbol in CCXT_CRYPTO_SYMBOLS:
        try:
            result = await scan_asset(symbol, "crypto", session)
            if result is not None:
                scanned += 1
        except Exception as exc:
            log.error("scan_all_assets: error scanning crypto %s: %s", symbol, exc)

    log.info("scan_all_assets: complete -- %d signals upserted", scanned)
    return scanned


async def analysis_scan_job() -> None:
    """
    APScheduler job wrapper for scan_all_assets().

    Creates its own DB session (same pattern as stock_incremental_job in scheduler.py).
    Errors are caught at the top level -- a failed scan never crashes the scheduler.
    """
    try:
        async with async_session_factory() as session:
            count = await scan_all_assets(session)
            log.info("analysis_scan_job: complete -- %d signals", count)
    except Exception as exc:
        log.error("analysis_scan_job: fatal error: %s", exc)
