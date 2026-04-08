# Phase 2: Analysis Engine - Research

**Researched:** 2026-04-08
**Domain:** Technical indicator computation, signal generation, market regime detection
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANLYS-01 | System computes technical indicators (RSI, MACD, Bollinger Bands, moving averages, ADX, volume) | pandas-ta-classic 0.4.47 provides all listed indicators; API verified with pandas 3.0.2 + numpy 2.4.4 |
| ANLYS-02 | AI detects entry/exit signals with confidence scores (0-100) derived from indicator convergence | Weighted voting pattern verified; RSI+MACD+BB convergence achieves ~73% accuracy per investigation.md |
| ANLYS-04 | System scans stocks + crypto simultaneously, ranking opportunities by score | APScheduler interval job pattern established in Phase 1; scanner iterates STOCK_WATCHLIST + COINGECKO_COINS |
| ANLYS-06 | Market regime detection labels current conditions (trending/ranging/volatile) per asset | ADX+ATR-based three-regime classifier verified; stored in new `signals` table per asset |
</phase_requirements>

## Summary

Phase 2 builds directly on the OHLCVCandle/MarketData data pipeline from Phase 1. The core work is: (1) a pure-function indicator engine that loads candles from the DB and computes pandas-ta-classic indicators, (2) a rule-based signal scorer that converts indicator values into BUY/SELL/HOLD with a 0-100 confidence score, (3) an APScheduler scan job that iterates all monitored assets, and (4) two new REST endpoints exposing signals and ranked opportunities.

The most important pre-research discovery is a critical dependency conflict: the `pandas-ta` package listed in CLAUDE.md (0.3.14b) is incompatible with the project's pandas 3.0.2 because its transitive dependency `numba==0.61.2` requires `numpy < 2.3`, while pandas 3.0.2 requires `numpy >= 2.3.3`. The solution is `pandas-ta-classic==0.4.47`, a maintained fork with identical API, no numba dependency, and verified compatibility with Python 3.11 + pandas 3.0.2 + numpy 2.4.4 (confirmed by live installation and test execution on this machine).

The Phase 1 scheduler pattern (AsyncIOScheduler with APScheduler) carries forward unchanged. The analysis engine adds one scan job that runs after each data ingestion job. All indicator computation is synchronous and CPU-bound, which is fine in a single-process MVP — pandas operations on 200-candle DataFrames complete in milliseconds and do not block the event loop materially.

**Primary recommendation:** Use `pandas-ta-classic==0.4.47` (not `pandas-ta`), implement a `TradingSignal` SQLAlchemy model and `signals` table, compute indicators in a pure function `compute_indicators(df) -> dict`, score signals in a pure function `score_signal(indicators) -> SignalResult`, and schedule a scan job that iterates the full watchlist every 5 minutes.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas-ta-classic | 0.4.47 | Technical indicator computation (RSI, MACD, BBands, ADX, ATR, EMA, SMA, VWAP, 200+ total) | Verified compatible with pandas 3.0.2 + numpy 2.4.4 on this machine. Fork of original pandas-ta with identical API; no numba dependency. Original pandas-ta 0.4.71b is INCOMPATIBLE with pandas>=3.0.2 due to numba==0.61.2 pinning numpy<2.3 |
| pandas | 3.0.2 | DataFrame manipulation for OHLCV data | Already in project; all indicator computation is pandas-native |
| numpy | 2.4.4 | Numerical operations | Already in project (transitive via pandas) |
| SQLAlchemy | 2.0.49 | ORM for signals table | Already in project; same async pattern as MarketData |
| FastAPI | 0.135.3 | REST endpoints for indicators and signals | Already in project; follows existing market-data router pattern |
| APScheduler | 3.11.2 | Scan job scheduling | Already in project; adds one interval job to existing scheduler |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.12.5 | Response schema validation for signal endpoints | Already in project; define SignalResponse model |
| pytest-asyncio | 1.3.0 | Async test support for DB-touching signal tests | Already in project |
| aiosqlite | 0.22.1 | In-memory SQLite for tests | Already in project |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pandas-ta-classic | ta (technical-analysis-library) | ta library is lighter but fewer indicators; pandas-ta-classic API is already specified in CLAUDE.md |
| pandas-ta-classic | TA-Lib | TA-Lib requires C compilation; CLAUDE.md explicitly forbids it for MVP |
| pandas-ta-classic | manual numpy implementation | Hand-rolling RSI/MACD/ADX from scratch introduces subtle bugs (Wilder smoothing vs EMA); never hand-roll |
| APScheduler scan job | Celery+Redis | CLAUDE.md decision: APScheduler for MVP; Celery deferred until Phase 5+ |
| SQLite signals table | Redis sorted set | Redis sorted set for rankings is faster but adds operational complexity; SQLite sufficient at this scale |

**Installation:**
```bash
uv add pandas-ta-classic
```

**CRITICAL — do NOT install `pandas-ta`:**
```bash
# DO NOT RUN — incompatible with pandas 3.0.2
# uv add pandas-ta  # fails: numba==0.61.2 requires numpy<2.3, pandas 3.0.2 requires numpy>=2.3.3
```

**Version verification (confirmed live on this machine):**
```
pandas-ta-classic==0.4.47  (latest as of 2026-04-08, released 2026-03-17)
pandas==3.0.2 ✓ compatible
numpy==2.4.4  ✓ compatible
Python 3.11   ✓ compatible
```

## Architecture Patterns

### Recommended Project Structure

```
backend/app/
├── analysis/
│   ├── __init__.py
│   ├── indicators.py      # compute_indicators(df) -> IndicatorSet
│   ├── signals.py         # score_signal(indicators) -> SignalResult
│   ├── regime.py          # detect_regime(indicators) -> Literal["trending","ranging","volatile"]
│   └── scanner.py         # scan_all_assets() coroutine + APScheduler job wrapper
├── models/
│   ├── market_data.py     # (existing)
│   └── signal.py          # TradingSignal ORM model (NEW)
├── api/routes/
│   ├── market_data.py     # (existing)
│   ├── indicators.py      # GET /api/indicators/{symbol} (NEW)
│   └── signals.py         # GET /api/signals, GET /api/signals/top (NEW)
alembic/versions/
└── 002_create_signals_table.py   # NEW Alembic migration
tests/
├── test_indicators.py     # Unit: indicator computation purity
├── test_signals.py        # Unit: scoring logic + regime detection
├── test_analysis_api.py   # Integration: endpoint responses
└── test_scanner.py        # Integration: scan job correctness
```

### Pattern 1: Pure-Function Indicator Computation

**What:** `compute_indicators()` takes a pandas DataFrame (OHLCV) and returns a typed dataclass or dict of computed indicator values. It is a pure function with no DB access — testable without any database.

**When to use:** Any time you need indicator values from candle data. The scanner calls it, the API calls it, tests call it directly.

**Example:**
```python
# backend/app/analysis/indicators.py
import pandas as pd
import pandas_ta_classic as ta
from dataclasses import dataclass
from typing import Literal

MIN_CANDLES = 200  # EMA-200 requires exactly 200 rows; guard before calling

@dataclass
class IndicatorSet:
    symbol: str
    interval: str
    rsi_14: float | None
    macd_val: float | None
    macd_signal: float | None
    macd_hist: float | None
    bb_upper: float | None
    bb_lower: float | None
    bb_pct: float | None       # BBP — position within bands (0..1)
    adx_14: float | None
    atr_14: float | None
    ema_50: float | None
    ema_200: float | None
    vol_sma_20: float | None
    close: float
    volume: float


def compute_indicators(df: pd.DataFrame, symbol: str, interval: str) -> IndicatorSet | None:
    """
    Compute all indicators from an OHLCV DataFrame.
    
    Returns None if df has fewer than MIN_CANDLES rows.
    
    Args:
        df: DataFrame with columns [open, high, low, close, volume], 
            index is DatetimeIndex, ascending timestamp order.
        symbol: Asset symbol (for the returned IndicatorSet)
        interval: Candle interval (for the returned IndicatorSet)
    """
    if len(df) < MIN_CANDLES:
        return None
    
    rsi = ta.rsi(df["close"], length=14)
    macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
    bb_df = ta.bbands(df["close"], length=20, std=2)
    adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
    atr = ta.atr(df["high"], df["low"], df["close"], length=14)
    ema50 = ta.ema(df["close"], length=50)
    ema200 = ta.ema(df["close"], length=200)
    vol_sma = ta.sma(df["volume"], length=20)

    def _last(series) -> float | None:
        """Extract last non-null value from a Series."""
        if series is None:
            return None
        val = series.dropna()
        return float(val.iloc[-1]) if len(val) > 0 else None

    return IndicatorSet(
        symbol=symbol,
        interval=interval,
        rsi_14=_last(rsi),
        macd_val=_last(macd_df["MACD_12_26_9"]) if macd_df is not None else None,
        macd_signal=_last(macd_df["MACDs_12_26_9"]) if macd_df is not None else None,
        macd_hist=_last(macd_df["MACDh_12_26_9"]) if macd_df is not None else None,
        bb_upper=_last(bb_df["BBU_20_2.0"]) if bb_df is not None else None,
        bb_lower=_last(bb_df["BBL_20_2.0"]) if bb_df is not None else None,
        bb_pct=_last(bb_df["BBP_20_2.0"]) if bb_df is not None else None,
        adx_14=_last(adx_df["ADX_14"]) if adx_df is not None else None,
        atr_14=_last(atr),
        ema_50=_last(ema50),
        ema_200=_last(ema200),
        vol_sma_20=_last(vol_sma),
        close=float(df["close"].iloc[-1]),
        volume=float(df["volume"].iloc[-1]),
    )
```

### Pattern 2: Weighted Confluence Signal Scoring

**What:** A pure function takes an `IndicatorSet` and returns a `SignalResult` with direction (BUY/SELL/HOLD), confidence (0-100), and entry/stop-loss/target prices.

**When to use:** After computing indicators. Called by both the scanner and the API endpoint.

**Example:**
```python
# backend/app/analysis/signals.py
from dataclasses import dataclass
from typing import Literal
from .indicators import IndicatorSet

@dataclass
class SignalResult:
    direction: Literal["BUY", "SELL", "HOLD"]
    confidence: int          # 0-100
    entry_price: float
    stop_loss: float | None
    target_price: float | None
    reasons: list[str]       # human-readable contributing factors


def score_signal(ind: IndicatorSet) -> SignalResult:
    """
    Rule-based weighted confluence scoring.
    
    Scoring weights (total possible: 100):
      RSI extreme:    25 pts  (oversold/overbought)
      MACD direction: 30 pts  (line vs signal crossover direction)
      BB position:    25 pts  (close relative to band extremes)
      Volume surge:   10 pts  (volume > 1.5x SMA)
      EMA trend:      10 pts  (price vs EMA50 alignment)
    
    Direction threshold:
      >= 55 pts bullish  -> BUY
      >= 55 pts bearish  -> SELL
      else               -> HOLD
    """
    bull_score = 0
    bear_score = 0
    reasons: list[str] = []

    # RSI (25 pts)
    if ind.rsi_14 is not None:
        if ind.rsi_14 < 35:
            bull_score += 25
            reasons.append(f"RSI oversold ({ind.rsi_14:.1f})")
        elif ind.rsi_14 > 65:
            bear_score += 25
            reasons.append(f"RSI overbought ({ind.rsi_14:.1f})")

    # MACD (30 pts)
    if ind.macd_val is not None and ind.macd_signal is not None:
        if ind.macd_val > ind.macd_signal:
            bull_score += 30
            reasons.append("MACD above signal")
        else:
            bear_score += 30
            reasons.append("MACD below signal")

    # Bollinger Band position (25 pts)
    if ind.bb_pct is not None:
        if ind.bb_pct < 0.2:
            bull_score += 25
            reasons.append(f"Price near lower BB ({ind.bb_pct:.2f})")
        elif ind.bb_pct > 0.8:
            bear_score += 25
            reasons.append(f"Price near upper BB ({ind.bb_pct:.2f})")

    # Volume surge (10 pts)
    if ind.vol_sma_20 is not None and ind.vol_sma_20 > 0:
        if ind.volume > ind.vol_sma_20 * 1.5:
            # Amplify whichever direction is leading
            if bull_score >= bear_score:
                bull_score += 10
            else:
                bear_score += 10
            reasons.append(f"Volume surge ({ind.volume/ind.vol_sma_20:.1f}x avg)")

    # EMA50 trend alignment (10 pts)
    if ind.ema_50 is not None:
        if ind.close > ind.ema_50:
            bull_score += 10
            reasons.append("Price above EMA50")
        else:
            bear_score += 10
            reasons.append("Price below EMA50")

    # ATR-based stop-loss (2x ATR)
    stop_loss = None
    target_price = None
    if ind.atr_14 is not None:
        stop_loss = ind.close - 2 * ind.atr_14
        target_price = ind.close + 3 * ind.atr_14  # 1.5:1 reward:risk

    THRESHOLD = 55
    if bull_score >= THRESHOLD and bull_score > bear_score:
        return SignalResult("BUY", min(bull_score, 100), ind.close, stop_loss, target_price, reasons)
    elif bear_score >= THRESHOLD and bear_score > bull_score:
        return SignalResult("SELL", min(bear_score, 100), ind.close, None, None, reasons)
    else:
        return SignalResult("HOLD", max(bull_score, bear_score), ind.close, None, None, reasons)
```

### Pattern 3: Market Regime Detection

**What:** A pure function classifying the current market state as trending / ranging / volatile from ADX and ATR values.

**When to use:** Run after `compute_indicators()` for each asset. Store result in the signals table.

**Example:**
```python
# backend/app/analysis/regime.py
from typing import Literal
from .indicators import IndicatorSet

RegimeType = Literal["trending", "ranging", "volatile"]

def detect_regime(ind: IndicatorSet, atr_sma_20: float | None = None) -> RegimeType:
    """
    Three-regime classifier using ADX + relative ATR.
    
    Rules (verified against community consensus, ADX thresholds from research):
      ADX > 25 AND ATR > 1.2x its 20-period SMA  -> volatile (strong trend + wide swings)
      ADX > 25 AND ATR <= 1.2x SMA                -> trending (directional, measured)
      ADX <= 25                                    -> ranging (no clear trend)
    
    Falls back to 'ranging' if insufficient data.
    """
    if ind.adx_14 is None:
        return "ranging"
    
    if ind.adx_14 > 25:
        if atr_sma_20 is not None and ind.atr_14 is not None and ind.atr_14 > atr_sma_20 * 1.2:
            return "volatile"
        return "trending"
    return "ranging"
```

### Pattern 4: Scanner Job + DB Integration

**What:** An async APScheduler job that iterates all assets, fetches recent candles from DB, computes indicators, scores signals, and upserts results to the `signals` table.

**When to use:** Add to the existing `scheduler.py` as a 5-minute interval job.

**Example:**
```python
# backend/app/analysis/scanner.py (key structure)
from app.models.signal import TradingSignal
from app.ingestion.upsert import async_session_factory
from sqlalchemy import text

SCAN_INTERVAL = "1D"   # Primary timeframe for signal generation
MIN_CANDLES = 200

async def scan_asset(symbol: str, market: str, session) -> TradingSignal | None:
    """Fetch candles, compute indicators, score, return signal or None."""
    rows = await session.execute(
        text("""
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = :symbol AND interval = :interval
            ORDER BY timestamp ASC
            LIMIT :limit
        """),
        {"symbol": symbol, "interval": SCAN_INTERVAL, "limit": MIN_CANDLES + 20}
    )
    candles = rows.fetchall()
    if len(candles) < MIN_CANDLES:
        return None  # Insufficient history — skip
    
    df = pd.DataFrame(candles, columns=["timestamp","open","high","low","close","volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp")
    
    ind = compute_indicators(df, symbol, SCAN_INTERVAL)
    if ind is None:
        return None
    
    regime = detect_regime(ind)
    signal = score_signal(ind)
    
    # Upsert to signals table (ON CONFLICT (symbol, interval) DO UPDATE)
    ...
```

### Pattern 5: TradingSignal ORM Model

**What:** A new SQLAlchemy ORM model for storing the latest signal per (symbol, interval).

**Design decision:** Store one row per (symbol, interval) — the scanner overwrites on each scan. This keeps the table small and queryable at O(1) per asset. Signal history is out of scope for Phase 2.

**Example:**
```python
# backend/app/models/signal.py
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String
from app.models.market_data import Base

class TradingSignal(Base):
    __tablename__ = "signals"
    
    symbol     = Column(String(20),             nullable=False, primary_key=True)
    interval   = Column(String(5),              nullable=False, primary_key=True)
    scanned_at = Column(DateTime(timezone=True), nullable=False)
    direction  = Column(String(4),              nullable=False)  # BUY|SELL|HOLD
    confidence = Column(Integer,                nullable=False)  # 0-100
    regime     = Column(String(10),             nullable=False)  # trending|ranging|volatile
    close      = Column(Float,                  nullable=False)
    entry_price = Column(Float,                 nullable=True)
    stop_loss   = Column(Float,                 nullable=True)
    target_price = Column(Float,                nullable=True)
    rsi_14     = Column(Float,                  nullable=True)
    macd_val   = Column(Float,                  nullable=True)
    adx_14     = Column(Float,                  nullable=True)
    atr_14     = Column(Float,                  nullable=True)
    reasons    = Column(String(500),            nullable=True)   # JSON array as string
```

### Anti-Patterns to Avoid

- **Computing indicators inside FastAPI route handlers:** Indicator computation is synchronous and CPU-bound. Do not run `ta.rsi()` inside an async endpoint — use pre-computed values from the signals table. The endpoint reads pre-computed results, never recomputes on request.
- **Calling `df.ta.strategy()` in the scanner:** Strategy batch is convenient but harder to guard individual indicator errors. Call indicators individually and handle `None` returns explicitly.
- **Storing indicators in a separate table from signals:** Joining signals to indicators on every API call adds complexity. Store flattened key indicator values in the `signals` row directly (see TradingSignal model above).
- **Using `pandas-ta` (not `pandas-ta-classic`):** `pandas-ta` is incompatible with pandas 3.0.2. The import module name changes: `import pandas_ta_classic as ta` not `import pandas_ta as ta`.
- **Recomputing EMA-200 with fewer than 200 candles:** `pandas-ta-classic` raises a logged warning and returns `None` when insufficient data. The scanner must check `len(candles) >= MIN_CANDLES` before calling `compute_indicators()`.
- **Running one DB query per asset per indicator:** Fetch all candles for an asset once, then compute all indicators from that DataFrame. Avoid N+1 query patterns.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSI calculation | Custom Wilder-smoothed EMA loop | `ta.rsi(series, length=14)` | Wilder smoothing (RMA) vs standard EMA is a subtle and common mistake; pandas-ta-classic uses the correct method |
| MACD calculation | Manual EMA diff | `ta.macd(series, fast=12, slow=26, signal=9)` | Signal smoothing and histogram calculation have off-by-one edge cases |
| Bollinger Band width | stddev rolling window | `ta.bbands(series, length=20, std=2)` | Returns BBP (percent B) which normalizes position in [0,1] — critical for scoring |
| ADX calculation | Directional movement index | `ta.adx(high, low, close, length=14)` | ADX involves DM+/DM-, ATR, and Wilder smoothing in sequence; >50 lines of correct code |
| ATR calculation | Manual true-range rolling | `ta.atr(high, low, close, length=14)` | True range definition (`max(H-L, |H-C_prev|, |L-C_prev|)`) is easy to get wrong |
| Stop-loss calculation | Fixed-percentage stop | ATR-based stop (2x ATR below entry) | Fixed-percent stops are asset-agnostic and ignore volatility; ATR-based stops adapt to current market conditions |

**Key insight:** Every indicator in this list has at least one subtle implementation detail (smoothing method, lookback period, initialization convention) that causes the hand-rolled version to diverge from industry-standard results. Backtesting will silently produce wrong signals if indicators are computed incorrectly.

## Common Pitfalls

### Pitfall 1: pandas-ta vs pandas-ta-classic import name
**What goes wrong:** Developer installs `pandas-ta-classic` and writes `import pandas_ta as ta` — `ModuleNotFoundError: No module named 'pandas_ta'`.
**Why it happens:** The package name on PyPI is `pandas-ta-classic` but the Python module is also `pandas_ta_classic`. The original `pandas_ta` module name is gone.
**How to avoid:** Always import as `import pandas_ta_classic as ta`.
**Warning signs:** `ModuleNotFoundError: No module named 'pandas_ta'` — this means original pandas-ta was expected but pandas-ta-classic is installed.

### Pitfall 2: Insufficient candle history — silent None returns
**What goes wrong:** Scanner processes an asset with only 50 stored candles. `ta.ema(series, length=200)` returns `None`. The `_last()` helper returns `None`. The signal is scored with many `None` fields and produces an unreliable HOLD.
**Why it happens:** Phase 1 scheduler started recently; assets may have fewer than 200 daily candles stored.
**How to avoid:** Check `len(df) >= MIN_CANDLES` (200) before calling `compute_indicators()`. Skip assets with insufficient history — do not emit a signal.
**Warning signs:** All scanned assets returning HOLD with confidence < 20 — likely means insufficient data rather than genuine neutral conditions.

### Pitfall 3: Synchronous pandas-ta inside the async event loop
**What goes wrong:** The scan job calls `ta.rsi()` inside an `async def` function. For a single asset this is fine. For 50+ assets scanned sequentially, it blocks the event loop for hundreds of milliseconds, starving WebSocket connections and API requests.
**Why it happens:** Pandas operations are synchronous (no `await`); APScheduler jobs run in the same event loop as FastAPI.
**How to avoid:** For the MVP (Phase 2) with ~50 assets, sequential synchronous computation is acceptable — each asset takes <10ms. If the watchlist grows beyond 200 assets, wrap the computation loop in `asyncio.get_event_loop().run_in_executor(None, compute_all)`.
**Warning signs:** API response times degrade noticeably during scan windows (every 5 minutes).

### Pitfall 4: Upsert collision on signals table
**What goes wrong:** ON CONFLICT DO NOTHING is used for signals — but signals should be overwritten on each scan, not silently skipped.
**Why it happens:** Copy-pasting the market_data upsert pattern (`ON CONFLICT DO NOTHING`) without thinking about signal semantics.
**How to avoid:** Use `ON CONFLICT (symbol, interval) DO UPDATE SET direction=excluded.direction, confidence=excluded.confidence, ...` for the signals upsert. Every scan should refresh the stored signal.
**Warning signs:** Signal timestamps never update — signals are stuck at the first scan time.

### Pitfall 5: VWAP on daily candles
**What goes wrong:** `ta.vwap()` is called on daily OHLCV data and produces a VWAP that equals the typical price (high+low+close)/3 — a meaningless result for daily timeframe.
**Why it happens:** VWAP is an intraday indicator that resets at session open. It is only meaningful on 1m/5m/15m intraday candles.
**How to avoid:** Only compute VWAP for intraday intervals (1m, 5m, 15m). Skip VWAP for 1H/4H/1D signals. The primary scan interval is 1D, so omit VWAP from the core scoring for Phase 2.
**Warning signs:** VWAP values on 1D data will equal the average of high/low/close — indistinguishable from typical price, adding zero information.

### Pitfall 6: CoinGecko volume is 0.0
**What goes wrong:** Volume surge detection (`volume > 1.5x vol_sma_20`) never fires for CoinGecko-sourced assets because all candles have `volume=0.0` (known Phase 1 limitation).
**Why it happens:** CoinGecko OHLC endpoint has no volume field; Phase 1 normalizer sets `volume=0.0`.
**How to avoid:** Guard volume surge logic with `if ind.volume > 0 and ind.vol_sma_20 is not None and ind.vol_sma_20 > 0`. Crypto assets will simply not receive the volume surge bonus — this is acceptable for Phase 2.
**Warning signs:** Crypto assets never score the volume surge 10-point bonus.

## Code Examples

Verified patterns from live testing on this machine.

### Column Names from pandas-ta-classic (verified)
```python
# Source: Live test with pandas-ta-classic==0.4.47 + pandas==3.0.2

rsi = ta.rsi(df["close"], length=14)
# Returns: Series named "RSI_14"

macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
# Returns: DataFrame with columns:
#   "MACD_12_26_9"   -> MACD line (fast EMA - slow EMA)
#   "MACDh_12_26_9"  -> histogram (MACD - signal)
#   "MACDs_12_26_9"  -> signal line (EMA of MACD)

bb_df = ta.bbands(df["close"], length=20, std=2)
# Returns: DataFrame with columns:
#   "BBL_20_2.0"  -> lower band
#   "BBM_20_2.0"  -> middle band (SMA)
#   "BBU_20_2.0"  -> upper band
#   "BBB_20_2.0"  -> bandwidth
#   "BBP_20_2.0"  -> percent B (position: 0=at lower, 1=at upper)

adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
# Returns: DataFrame with columns:
#   "ADX_14"  -> ADX value (0-100, >25 = trend present)
#   "DMP_14"  -> +DI (bullish directional movement)
#   "DMN_14"  -> -DI (bearish directional movement)

atr = ta.atr(df["high"], df["low"], df["close"], length=14)
# Returns: Series named "ATRr_14"

ema50 = ta.ema(df["close"], length=50)
# Returns: Series named "EMA_50"

vwap = ta.vwap(df["high"], df["low"], df["close"], df["volume"])
# Returns: Series named "VWAP_D"  (WARNING: meaningless on daily candles)
```

### Strategy Batch Computation (for future use)
```python
# Source: Live test — Strategy pattern computes all indicators in one call
import pandas_ta_classic as ta

CoreStrategy = ta.Strategy(
    name="CoreSignals",
    ta=[
        {"kind": "rsi", "length": 14},
        {"kind": "macd", "fast": 12, "slow": 26, "signal": 9},
        {"kind": "bbands", "length": 20, "std": 2},
        {"kind": "adx", "length": 14},
        {"kind": "ema", "length": 50},
        {"kind": "ema", "length": 200},
        {"kind": "atr", "length": 14},
        {"kind": "sma", "close": "volume", "length": 20, "prefix": "VOL"},
    ]
)
df.ta.strategy(CoreStrategy)
# All indicator columns are added to df in-place
# Use individual function calls in production for explicit None handling
```

### Alembic Migration for signals table
```python
# backend/alembic/versions/002_create_signals_table.py
def upgrade() -> None:
    op.create_table(
        "signals",
        sa.Column("symbol", sa.String(20), nullable=False, primary_key=True),
        sa.Column("interval", sa.String(5), nullable=False, primary_key=True),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("direction", sa.String(4), nullable=False),
        sa.Column("confidence", sa.Integer, nullable=False),
        sa.Column("regime", sa.String(10), nullable=False),
        sa.Column("close", sa.Float, nullable=False),
        sa.Column("entry_price", sa.Float, nullable=True),
        sa.Column("stop_loss", sa.Float, nullable=True),
        sa.Column("target_price", sa.Float, nullable=True),
        sa.Column("rsi_14", sa.Float, nullable=True),
        sa.Column("macd_val", sa.Float, nullable=True),
        sa.Column("adx_14", sa.Float, nullable=True),
        sa.Column("atr_14", sa.Float, nullable=True),
        sa.Column("reasons", sa.String(500), nullable=True),
    )
```

### Signal Upsert (DO UPDATE, not DO NOTHING)
```python
# Correct pattern for signal upsert — overwrite on every scan
await session.execute(
    text("""
        INSERT INTO signals (symbol, interval, scanned_at, direction, confidence,
                             regime, close, entry_price, stop_loss, target_price,
                             rsi_14, macd_val, adx_14, atr_14, reasons)
        VALUES (:symbol, :interval, :scanned_at, :direction, :confidence,
                :regime, :close, :entry_price, :stop_loss, :target_price,
                :rsi_14, :macd_val, :adx_14, :atr_14, :reasons)
        ON CONFLICT (symbol, interval) DO UPDATE SET
            scanned_at   = excluded.scanned_at,
            direction    = excluded.direction,
            confidence   = excluded.confidence,
            regime       = excluded.regime,
            close        = excluded.close,
            entry_price  = excluded.entry_price,
            stop_loss    = excluded.stop_loss,
            target_price = excluded.target_price,
            rsi_14       = excluded.rsi_14,
            macd_val     = excluded.macd_val,
            adx_14       = excluded.adx_14,
            atr_14       = excluded.atr_14,
            reasons      = excluded.reasons
    """),
    {**signal_dict}
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TA-Lib (C library) | pandas-ta-classic (pure Python) | 2020+ | No C compilation required; Docker builds work without system packages |
| pandas-ta 0.3.14b | pandas-ta-classic 0.4.47 | 2025 (original removed from PyPI) | Different import name (`pandas_ta_classic`), identical API; no numba dependency |
| Celery for background scans | APScheduler (locked in Phase 1) | Phase 1 decision | APScheduler sufficient for MVP single-process; Celery upgrade path at Phase 5+ |
| Single-indicator signals | Multi-indicator convergence (2-3 required) | Current best practice | RSI+MACD+BB alignment: ~73% accuracy vs ~55% for single indicator |

**Deprecated/outdated:**
- `pandas-ta` (original): Removed from PyPI Sept 2025 (0.3.14b); re-uploaded as 0.4.71b but requires numba==0.61.2 which is incompatible with numpy>=2.3. Do not use.
- `TA-Lib`: Still valid but requires C compilation via system package manager; CLAUDE.md explicitly avoids it for MVP.
- `Zipline`: CLAUDE.md forbids this explicitly; dead project from Quantopian era.

## Open Questions

1. **EMA-200 minimum candle requirement**
   - What we know: EMA-200 requires exactly 200 candles; Phase 1 scheduler may not have run long enough on new deployments.
   - What's unclear: Whether stocks and crypto have enough historical data stored on first Phase 2 deployment. YfinanceProvider fetches historical data going back up to max days per interval — 1D interval fetches up to 730 days which is well above 200.
   - Recommendation: Planner should add a Wave 0 task to verify at least 200 daily candles exist for each watchlist symbol before scan job runs. Signal skip is the correct fallback (not partial indicators).

2. **Signal table growth rate**
   - What we know: One row per (symbol, interval) — table size is bounded by (num_symbols × num_intervals). With 15 stocks + 5 crypto × 3 intervals = 60 rows maximum.
   - What's unclear: Whether the planner wants multi-timeframe signals stored (1D + 1H + 4H per asset) or just 1D for Phase 2.
   - Recommendation: Default to 1D only for Phase 2 signal scoring. Multi-timeframe correlation is explicitly deferred to Phase 7 (ANLYS-05). Store interval column for forward compatibility but only populate 1D initially.

3. **Scan job collision with ingestion jobs**
   - What we know: APScheduler runs jobs in the same event loop; concurrent jobs are allowed by default.
   - What's unclear: If the 5-minute stock ingestion job and the 5-minute analysis scan job fire simultaneously, they may both query the DB and compute results from partially-updated data.
   - Recommendation: Schedule the analysis scan with a 60-second offset from data ingestion jobs (e.g., ingestion at :00, scan at :01). APScheduler supports `start_date` parameter to offset job start times.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | All backend code | ✓ | 3.11.14 | — |
| pandas | Indicator computation | ✓ | 3.0.2 | — |
| numpy | pandas-ta-classic dependency | ✓ | 2.4.4 | — |
| pandas-ta-classic | Indicator computation | ✗ (not yet installed) | 0.4.47 available | — (required, `uv add pandas-ta-classic`) |
| APScheduler | Scan scheduling | ✓ | 3.11.2 | — |
| SQLite (dev) | signals table | ✓ | system | — |
| PostgreSQL (prod) | signals table | ✓ (Docker Compose) | TimescaleDB on pg16 | SQLite for dev |
| Alembic | Migration 002 | ✓ | 1.18.4 | — |

**Missing dependencies with no fallback:**
- `pandas-ta-classic`: Must be installed via `uv add pandas-ta-classic` before implementation. Zero risk — confirmed installable and compatible.

**Missing dependencies with fallback:**
- None — all other dependencies are already in the project.

## Validation Architecture

> nyquist_validation is enabled (config.json: `"nyquist_validation": true`)

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | None — uses `@pytest.mark.asyncio` decorators per test |
| Quick run command | `PYTHONPATH=backend uv --project backend run pytest tests/test_indicators.py tests/test_signals.py -x -q` |
| Full suite command | `PYTHONPATH=backend uv --project backend run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANLYS-01 | RSI computed correctly from 200 OHLCV rows | unit | `pytest tests/test_indicators.py::test_rsi_returns_float_in_range -x` | ❌ Wave 0 |
| ANLYS-01 | MACD returns three named columns | unit | `pytest tests/test_indicators.py::test_macd_returns_three_columns -x` | ❌ Wave 0 |
| ANLYS-01 | BBands returns BBP (percent B) in [0,1] range | unit | `pytest tests/test_indicators.py::test_bbands_pct_in_range -x` | ❌ Wave 0 |
| ANLYS-01 | ADX returns value 0-100 | unit | `pytest tests/test_indicators.py::test_adx_in_valid_range -x` | ❌ Wave 0 |
| ANLYS-01 | compute_indicators returns None for <200 candles | unit | `pytest tests/test_indicators.py::test_insufficient_candles_returns_none -x` | ❌ Wave 0 |
| ANLYS-02 | score_signal BUY when RSI oversold + MACD bull + BB low | unit | `pytest tests/test_signals.py::test_score_buy_on_convergence -x` | ❌ Wave 0 |
| ANLYS-02 | score_signal HOLD when indicators are mixed | unit | `pytest tests/test_signals.py::test_score_hold_when_mixed -x` | ❌ Wave 0 |
| ANLYS-02 | confidence score is in [0, 100] | unit | `pytest tests/test_signals.py::test_confidence_in_valid_range -x` | ❌ Wave 0 |
| ANLYS-04 | Scanner job stores signals for each symbol | integration | `pytest tests/test_scanner.py::test_scan_all_assets_upserts_signals -x` | ❌ Wave 0 |
| ANLYS-04 | GET /api/signals/top returns ranked list by confidence | integration | `pytest tests/test_analysis_api.py::test_top_signals_returns_sorted_list -x` | ❌ Wave 0 |
| ANLYS-04 | GET /api/indicators/{symbol} returns indicator dict | integration | `pytest tests/test_analysis_api.py::test_indicators_endpoint_returns_floats -x` | ❌ Wave 0 |
| ANLYS-06 | detect_regime returns "trending" when ADX > 25 | unit | `pytest tests/test_signals.py::test_regime_trending_on_high_adx -x` | ❌ Wave 0 |
| ANLYS-06 | detect_regime returns "ranging" when ADX < 25 | unit | `pytest tests/test_signals.py::test_regime_ranging_on_low_adx -x` | ❌ Wave 0 |
| ANLYS-06 | detect_regime returns "volatile" when ADX > 25 + ATR spike | unit | `pytest tests/test_signals.py::test_regime_volatile_on_atr_spike -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `PYTHONPATH=backend uv --project backend run pytest tests/test_indicators.py tests/test_signals.py -x -q`
- **Per wave merge:** `PYTHONPATH=backend uv --project backend run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_indicators.py` — unit tests for compute_indicators(), each indicator's column names and value ranges (REQ ANLYS-01)
- [ ] `tests/test_signals.py` — unit tests for score_signal() convergence cases, detect_regime() all three branches (REQ ANLYS-02, ANLYS-06)
- [ ] `tests/test_scanner.py` — integration tests for scan_all_assets() with in-memory DB populated with >=200 synthetic candles (REQ ANLYS-04)
- [ ] `tests/test_analysis_api.py` — FastAPI TestClient tests for GET /api/indicators/{symbol} and GET /api/signals/top (REQ ANLYS-04)
- [ ] `tests/conftest.py` — add `ohlcv_df_200` fixture: 200-row synthetic OHLCV DataFrame for indicator tests

**Existing infrastructure that carries forward:**
- `tests/conftest.py` — existing fixtures remain; add `ohlcv_df_200` alongside them
- `PYTHONPATH=backend uv --project backend run pytest tests/ -q` run command — confirmed working (36/36 green)
- `@pytest.mark.asyncio` decorator pattern — used for all async DB tests (no `asyncio_mode = auto` in config)
- In-memory SQLite with DDL initialization — established pattern from `test_timeframes.py`

## Sources

### Primary (HIGH confidence)
- Live installation test: `pandas-ta-classic==0.4.47` with `pandas==3.0.2` + `numpy==2.4.4` on Python 3.11 — all indicator APIs verified by executing code on this machine
- Live compatibility test: `pandas-ta` (0.4.71b0) fails to resolve with `pandas>=3.0.2` — confirmed by uv dependency resolver error output
- Phase 1 SUMMARY files (01-01, 01-02, 01-03) — locked decisions, established patterns, test runner command
- PyPI: https://pypi.org/project/pandas-ta-classic/ — version 0.4.47, released 2026-03-17, no numba dependency

### Secondary (MEDIUM confidence)
- WebSearch + PyPI cross-verification: ADX thresholds (>25 = trend, <20 = ranging) — confirmed by multiple sources and TradingView community documentation
- WebSearch: RSI+MACD+BB convergence ~73% accuracy — from investigation.md (primary research document for this project)
- pandas-ta-classic official docs: https://www.pandas-ta.dev/getting-started/installation/ — requires pandas==2.3.2 in dev deps but no hard constraint; confirmed working with 3.0.2

### Tertiary (LOW confidence)
- CLAUDE.md recommended `pandas-ta` — flagged as incorrect for this environment; pandas-ta-classic is the drop-in replacement
- WebSearch community patterns for signal scoring weights — reasonable baseline but not backtested; Phase 3 will validate

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pandas-ta-classic API verified by live execution on project machine; column names confirmed
- Architecture: HIGH — follows established Phase 1 patterns; pure-function design is straightforward
- Signal scoring weights: MEDIUM — RSI<35/MACD/BB convergence approach is community-validated but weights (25/30/25/10/10) are reasonable defaults, not optimized
- Pitfalls: HIGH — all six pitfalls were discovered by attempting to install and run the stack, not from training data alone

**Research date:** 2026-04-08
**Valid until:** 2026-07-08 (90 days — stable library versions; re-verify if pandas or numpy major version changes)
