---
phase: 02-analysis-engine
verified: 2026-04-08T00:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 2: Analysis Engine Verification Report

**Phase Goal:** The system continuously scans stored market data, generates ranked trading signals with scores and template-based reasoning
**Verified:** 2026-04-08
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `compute_indicators()` returns an `IndicatorSet` with all named fields (RSI, MACD, BB, ADX, ATR, EMA, volume) when given >= 200 rows | VERIFIED | `indicators.py` line 100-116: all fields populated from pandas_ta_classic calls; 12 tests pass confirming field presence |
| 2 | `compute_indicators()` returns `None` when given < 200 rows | VERIFIED | `indicators.py` line 79: `if len(df) < MIN_CANDLES: return None`; test `test_compute_indicators_returns_none_when_insufficient_candles` verifies |
| 3 | `score_signal()` returns BUY/SELL/HOLD with confidence 0-100 derived from indicator convergence | VERIFIED | `signals.py` lines 104-128: three branches emit Literal["BUY","SELL","HOLD"] with `min(..., 100)` clamping; THRESHOLD=55 for directional signals; 8 unit tests pass |
| 4 | `detect_regime()` returns "trending", "ranging", or "volatile" based on ADX and ATR thresholds | VERIFIED | `regime.py` lines 35-47: ADX>25 + ATR>1.2x SMA → "volatile", ADX>25 → "trending", ADX<=25 or None → "ranging"; 5 unit tests pass |
| 5 | `scan_all_assets()` upserts TradingSignal rows using ON CONFLICT DO UPDATE (not DO NOTHING) | VERIFIED | `scanner.py` line 115: `ON CONFLICT (symbol, interval) DO UPDATE SET` with all 13 fields updated; test `test_scan_asset_upserts_signal_to_db` verifies exactly 1 row after 2 scans |
| 6 | GET /api/signals/top returns signals ranked by confidence DESC | VERIFIED | `signals.py` lines 71-76: `.order_by(TradingSignal.confidence.desc()).limit(limit)` |
| 7 | `analysis_scan_job` is registered as a 4th APScheduler job in scheduler.py | VERIFIED | `scheduler.py` line 163-169: `scheduler.add_job(analysis_scan_job, IntervalTrigger(minutes=5), id="analysis_scan", ...)`; `grep -c scheduler.add_job` returns 4 |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/analysis/indicators.py` | `compute_indicators()` pure function and `IndicatorSet` dataclass | VERIFIED | 118 lines; exports `IndicatorSet`, `compute_indicators`, `MIN_CANDLES`; `import pandas_ta_classic as ta` (correct package) |
| `backend/app/analysis/signals.py` | `score_signal()` pure function, `SignalResult` dataclass | VERIFIED | 131 lines; `THRESHOLD=55`; BUY/SELL/HOLD branches; ATR-based stop/target for BUY only |
| `backend/app/analysis/regime.py` | `detect_regime()` pure function | VERIFIED | 48 lines; ADX>25 threshold; 1.2x ATR-SMA volatile sub-classification |
| `backend/app/analysis/scanner.py` | `scan_asset()`, `scan_all_assets()`, `analysis_scan_job()` | VERIFIED | 224 lines; ON CONFLICT DO UPDATE; iterates STOCK_WATCHLIST + CCXT_CRYPTO_SYMBOLS separately |
| `backend/app/ingestion/scheduler.py` | 4 APScheduler jobs including `analysis_scan_job` | VERIFIED | 4 `scheduler.add_job` calls; `analysis_scan_job` imported from scanner; `id="analysis_scan"` |
| `backend/app/api/routes/signals.py` | GET /api/signals and GET /api/signals/top | VERIFIED | 78 lines; `/top` route orders by `TradingSignal.confidence.desc()` |
| `backend/app/api/routes/indicators.py` | GET /api/indicators/{symbol} | VERIFIED | 110 lines; on-demand computation; 404 for < MIN_CANDLES |
| `backend/app/models/signal.py` | `TradingSignal` ORM model with composite PK | VERIFIED | Composite PK (symbol, interval); all 15 columns including rsi_14, macd_val, adx_14, atr_14 |
| `backend/app/core/watchlists.py` | Shared watchlist constants (extracted to resolve circular import) | VERIFIED | 30 lines; `STOCK_WATCHLIST`, `CCXT_CRYPTO_SYMBOLS` defined here; both scheduler.py and scanner.py import from this module |
| `backend/tests/test_indicators.py` | 12 unit tests for indicator computation | VERIFIED | 12 tests covering: None on <200 rows, IndicatorSet type, all field types, close/volume passthrough, zero volume, MIN_CANDLES constant |
| `backend/tests/test_signals.py` | 14 unit tests for scorer and regime detector | VERIFIED | 9 scorer tests + 5 regime tests; all pass |
| `backend/tests/test_scanner.py` | 6 integration tests for scanner with in-memory SQLite | VERIFIED | 6 tests; upsert test verifies COUNT(*) == 1 after 2 scans |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scanner.py` | `indicators.py` | `from app.analysis.indicators import compute_indicators, MIN_CANDLES` | WIRED | Line 26 of scanner.py; called at line 86 |
| `scanner.py` | `signals.py` | `from app.analysis.signals import score_signal` | WIRED | Line 27 of scanner.py; called at line 100 |
| `scanner.py` | `regime.py` | `from app.analysis.regime import detect_regime` | WIRED | Line 28 of scanner.py; called at line 99 |
| `scanner.py` | `signal.py` (ORM) | `from app.models.signal import TradingSignal` | WIRED | Line 31 of scanner.py; used in upsert and return object |
| `scanner.py` | `watchlists.py` | `from app.core.watchlists import CCXT_CRYPTO_SYMBOLS, STOCK_WATCHLIST` | WIRED | Line 30; circular import resolved by extracting constants to watchlists.py |
| `scheduler.py` | `scanner.py` | `from app.analysis.scanner import analysis_scan_job` | WIRED | Line 28 of scheduler.py; registered as 4th APScheduler job at line 163 |
| `signals.py` (route) | `signal.py` (ORM) | `from app.models.signal import TradingSignal` | WIRED | Used in both GET endpoints with SQLAlchemy `select(TradingSignal)` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `scanner.py` → `signals` table | `TradingSignal` rows | `market_data` table → `compute_indicators()` → `score_signal()` + `detect_regime()` | Yes — full pipeline from DB candles through pandas computation to upsert | FLOWING |
| `signals.py` route `/top` | `rows` from `select(TradingSignal)` | `signals` table populated by scanner | Yes — real SQLAlchemy ORM query with `.order_by(TradingSignal.confidence.desc())` | FLOWING |
| `indicators.py` route `/{symbol}` | `ind` IndicatorSet | `market_data` table → `compute_indicators()` | Yes — real DB query; 404 when insufficient data | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 32 Phase 2 tests pass | `PYTHONPATH=. uv run pytest tests/test_indicators.py tests/test_signals.py tests/test_scanner.py -q` | `32 passed in 0.67s` | PASS |
| MIN_CANDLES constant is 200 | `grep "MIN_CANDLES: int = 200" backend/app/analysis/indicators.py` | Match found at line 19 | PASS |
| Scanner uses DO UPDATE not DO NOTHING | `grep "ON CONFLICT.*DO UPDATE" backend/app/analysis/scanner.py` | Match at line 115 | PASS |
| Scheduler registers exactly 4 jobs | `grep -c "scheduler.add_job" backend/app/ingestion/scheduler.py` | Returns 4 | PASS |
| `/top` endpoint orders by confidence DESC | `grep "confidence.desc" backend/app/api/routes/signals.py` | Match at line 73 | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ANLYS-01 | 02-01 | System computes technical indicators (RSI, MACD, BB, moving averages, ADX, volume) | SATISFIED | `compute_indicators()` computes all 8 indicator families; 12 tests confirm. Note: REQUIREMENTS.md shows this as `[ ]` (unchecked) — the checkbox was not updated after implementation. The code fully satisfies the requirement. |
| ANLYS-02 | 02-02 | AI detects entry/exit signals with confidence scores based on indicator convergence | SATISFIED | `score_signal()` uses 5-component weighted confluence scoring (RSI+MACD+BB+Volume+EMA) producing BUY/SELL/HOLD with 0-100 confidence |
| ANLYS-04 | 02-03 | System scans across stocks + crypto simultaneously, ranking opportunities by score | SATISFIED | `scan_all_assets()` iterates STOCK_WATCHLIST then CCXT_CRYPTO_SYMBOLS; GET /api/signals/top returns rows ranked by confidence DESC |
| ANLYS-06 | 02-02 | Market regime detection labels current conditions (trending/ranging/volatile) per asset | SATISFIED | `detect_regime()` classifies all three regimes based on ADX threshold (>25) and ATR vs SMA ratio (>1.2x) |

**Documentation gap noted:** ANLYS-01 is marked `[ ]` (pending) in REQUIREMENTS.md line 21 and "Pending" in the tracking table at line 115. The implementation fully satisfies this requirement. The checkbox should be updated to `[x]` and the tracking table to "Complete".

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None | — | — | — |

No stubs, placeholder returns, TODO/FIXME comments, or hardcoded empty values found in any Phase 2 implementation files. All data-returning functions perform real computation or real DB queries.

---

### Human Verification Required

#### 1. REST Endpoint Integration with Running Server

**Test:** Start the FastAPI server (`uv run uvicorn app.main:app`) with a populated database and call `GET /api/signals/top?limit=5` via browser or curl
**Expected:** Returns JSON array of up to 5 signal objects with `direction`, `confidence`, `regime`, and `reasons` fields populated
**Why human:** Requires a running server + populated database from Phase 1 ingestion jobs

#### 2. APScheduler Job Timing Behavior

**Test:** Run the server for 5+ minutes and observe logs for `analysis_scan_job: complete` entries
**Expected:** Log line appears every 5 minutes with a count of signals upserted
**Why human:** Requires a live running process to observe scheduled job execution

---

### Gaps Summary

No gaps found. All 7 observable truths are verified, all artifacts exist and are wired, and the full 32-test suite passes green. The only finding is a documentation inconsistency: ANLYS-01 remains marked as `[ ]` (pending) in REQUIREMENTS.md despite being fully implemented. This is a doc update, not a code gap.

---

_Verified: 2026-04-08_
_Verifier: Claude (gsd-verifier)_
