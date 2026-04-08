# analysis/ — Signal Generation Guide

All analysis engines are pure functions — no DB, no FastAPI imports. Fully testable in isolation.

## Files

| File | Purpose |
|------|---------|
| `indicators.py` | `compute_indicators()` — pandas-ta-classic wrapper |
| `signals.py` | `score_signal()` — weighted confluence scorer |
| `regime.py` | `detect_regime()` — ADX/ATR market classifier |
| `scanner.py` | `scan_all_assets()` — orchestrates full pipeline, DB upsert |
| `explainer.py` | `generate_explanation()` — LLM signal explanation (optional) |
| `multiframe.py` | `compute_multiframe_agreement()` — cross-timeframe signal correlation |

## compute_indicators()

```python
from app.analysis.indicators import compute_indicators, MIN_CANDLES

# df: DataFrame with [open, high, low, close, volume], DatetimeIndex ascending
ind = compute_indicators(df, symbol="AAPL", interval="1D")
# Returns None if len(df) < MIN_CANDLES (200)
```

**MIN_CANDLES = 200** — EMA-200 requires exactly 200 candles. The scanner silently skips assets with fewer rows.

Returns `IndicatorSet` dataclass with:
```
rsi_14          — RSI(14)
macd_val        — MACD_12_26_9
macd_signal     — MACDs_12_26_9
macd_hist       — MACDh_12_26_9
bb_upper        — BBU_20_2.0
bb_lower        — BBL_20_2.0
bb_pct          — BBP_20_2.0 (position within bands, 0=lower, 1=upper)
adx_14          — ADX_14
atr_14          — ATRr_14
ema_50          — EMA_50
ema_200         — EMA_200
vol_sma_20      — SMA(20) of volume
close           — last close price
volume          — last volume
```

All fields can be `None` if pandas-ta-classic returns all-NaN (handled gracefully by scorer).

## score_signal()

```python
from app.analysis.signals import score_signal, THRESHOLD

result = score_signal(ind)
# result.direction: "BUY" | "SELL" | "HOLD"
# result.confidence: 0-100
# result.entry_price, stop_loss, target_price
# result.reasons: list[str]
```

**Scoring weights (total 100 pts):**

| Component | Points | Condition |
|-----------|--------|-----------|
| RSI | 25 | RSI < 35 = bull; RSI > 65 = bear |
| MACD | 30 | MACD > signal = bull; MACD < signal = bear |
| Bollinger Band | 25 | BBP < 0.2 = bull (near lower); BBP > 0.8 = bear (near upper) |
| Volume surge | 10 | volume > 1.5x vol_sma_20; amplifies leading direction |
| EMA50 trend | 10 | close > EMA50 = bull; close < EMA50 = bear |

**Direction threshold (THRESHOLD = 55):** Signal fires only if score >= 55 AND strictly greater than opposite direction.

**Stop-loss / target (BUY only):**
- `stop_loss = close - 2 * ATR(14)`
- `target_price = close + 3 * ATR(14)` (1.5:1 reward:risk ratio)

## detect_regime()

```python
from app.analysis.regime import detect_regime

regime = detect_regime(ind, atr_sma_20=1.23)
# "volatile"  — ADX > 25 AND ATR > 1.2x its 20-period SMA
# "trending"  — ADX > 25, normal ATR
# "ranging"   — ADX <= 25 or no ADX data
```

The scanner computes `atr_sma_20` separately before calling `detect_regime()`:
```python
atr_series = ta.atr(df["high"], df["low"], df["close"], length=14)
atr_sma_20 = float(atr_series.rolling(20).mean().dropna().iloc[-1])
```

## scan_all_assets()

Orchestrates the full pipeline for all assets:

1. Queries `market_data` table (last `MIN_CANDLES + 20` rows, ASC order)
2. Calls `compute_indicators()` → returns `None` if insufficient data → skip
3. Calls `detect_regime()` with ATR SMA
4. Calls `score_signal()` for BUY/SELL/HOLD direction
5. Calls `generate_explanation()` (LLM, async, gracefully disabled)
6. Calls `compute_multiframe_agreement()` (reads existing signals from DB)
7. Upserts to `signals` table via `ON CONFLICT (symbol, interval) DO UPDATE` — always refreshed

**Why DO UPDATE (not DO NOTHING):** Signals must reflect the latest market state after each scan, not the first scan ever.

```python
from app.analysis.scanner import scan_all_assets

async with async_session_factory() as session:
    count = await scan_all_assets(session)  # returns number of signals upserted
```

## generate_explanation() — LLM Explainer

```python
from app.analysis.explainer import generate_explanation

explanation = await generate_explanation(
    symbol="AAPL",
    direction="BUY",
    confidence=75,
    ind=ind,
    reasons=signal.reasons,
)
# Returns "" if llm_enabled=False or openai_api_key="" — never raises
```

Uses `gpt-4o-mini` via LangChain. The prompt contains only verified `IndicatorSet` values — the LLM is instructed not to invent numbers. Explanation is cached on the signal row; no duplicate LLM calls per signal per scan.

**Enabling LLM:** Set `OPENAI_API_KEY=sk-...` and `LLM_ENABLED=true` in `.env`.

## multiframe.py

`compute_multiframe_agreement(symbol, session)` queries the `signals` table for 1H, 4H, and 1D signals for the same symbol and returns a dict of `{interval: direction}`. Stored as JSON on the signal row.

```python
from app.analysis.multiframe import compute_multiframe_agreement

multiframe = await compute_multiframe_agreement("AAPL", session)
# {"1H": "BUY", "4H": "HOLD", "1D": "BUY"}
```
