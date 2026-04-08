---
phase: 02-analysis-engine
plan: "02"
subsystem: api
tags: [fastapi, sqlalchemy, pandas-ta, signals, regime-detection, tdd]

requires:
  - phase: 02-01
    provides: IndicatorSet dataclass, compute_indicators(), TradingSignal model, market_data table

provides:
  - score_signal() pure function with weighted confluence scoring (THRESHOLD=55)
  - detect_regime() pure function with ADX/ATR-based regime classification
  - GET /api/indicators/{symbol} endpoint (on-demand indicator computation)
  - GET /api/signals endpoint (all latest signals from DB)
  - GET /api/signals/top endpoint (top N signals sorted by confidence DESC)

affects: [02-03, 03-backtesting, 04-dashboard]

tech-stack:
  added: []
  patterns:
    - "score_signal(): pure function taking IndicatorSet, returning SignalResult with confidence 0-100"
    - "detect_regime(): pure function classifying ADX/ATR into trending/ranging/volatile"
    - "Router get_session() dependency pattern: async generator yielding AsyncSession (same as market_data)"
    - "Route files export get_session as module-level symbol for FastAPI dependency_overrides in tests"

key-files:
  created:
    - backend/app/analysis/signals.py
    - backend/app/analysis/regime.py
    - backend/app/api/routes/indicators.py
    - backend/app/api/routes/signals.py
    - backend/tests/test_signals.py
    - backend/tests/test_analysis_api.py
  modified:
    - backend/app/main.py

key-decisions:
  - "SELL signals have stop_loss=None and target_price=None per research spec — risk management for shorts deferred"
  - "GET /api/indicators/{symbol} computes on-demand from DB candles — not pre-cached — suitable for single-asset dashboard lookups only"
  - "Volume surge guard: vol_sma_20 > 0 check prevents ZeroDivisionError for CoinGecko zero-volume assets"

patterns-established:
  - "TDD: test_signals.py RED before signals.py/regime.py created; test_analysis_api.py RED before routes created"
  - "Route module exports get_session at module level to enable FastAPI dependency_overrides in integration tests"

requirements-completed: [ANLYS-02, ANLYS-06]

duration: 2min
completed: 2026-04-08
---

# Phase 02 Plan 02: Signal Scorer and REST Endpoints Summary

**Rule-based weighted confluence scorer (score_signal), regime detector (detect_regime), and two REST routes exposing pre-computed signals plus on-demand indicator lookup**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-08T05:59:17Z
- **Completed:** 2026-04-08T06:01:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- score_signal() pure function with 5-component scoring (RSI/MACD/BB/Volume/EMA) at THRESHOLD=55, producing BUY/SELL/HOLD with ATR-based stop/target for BUY signals
- detect_regime() pure function with ADX>25 threshold and 1.2x ATR-SMA volatile sub-classification
- GET /api/indicators/{symbol} computes IndicatorSet on-demand from DB candles, returns 404 for insufficient data
- GET /api/signals and GET /api/signals/top read pre-computed signals table with confidence-DESC ordering
- 20 tests passing (14 unit + 6 integration)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement signals.py and regime.py with test_signals.py** - `042acc9` (feat)
2. **Task 2: Create REST endpoints (indicators + signals routes)** - `86917d1` (feat)

## Files Created/Modified

- `backend/app/analysis/signals.py` - score_signal() with THRESHOLD=55, BUY/SELL/HOLD, ATR stop/target
- `backend/app/analysis/regime.py` - detect_regime() with ADX/ATR regime classification
- `backend/app/api/routes/indicators.py` - GET /api/indicators/{symbol}, on-demand computation, 404 for <200 candles
- `backend/app/api/routes/signals.py` - GET /api/signals and GET /api/signals/top (confidence DESC)
- `backend/app/main.py` - registered indicators_router and signals_router under /api prefix
- `backend/tests/test_signals.py` - 14 unit tests for scorer and regime detector
- `backend/tests/test_analysis_api.py` - 6 integration tests for both REST endpoints

## Decisions Made

- SELL signals return stop_loss=None and target_price=None per research spec — shorting risk management is out of scope for Phase 2
- GET /api/indicators/{symbol} computes on-demand rather than reading pre-cached values — keeps the endpoint correct for any symbol queried from the dashboard without requiring a prior scan
- Volume surge zero-guard (vol_sma_20 > 0) prevents ZeroDivisionError for CoinGecko assets where volume=0.0

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- score_signal() and detect_regime() are ready for the scanner (Plan 03) to call per asset
- /api/signals/top is ready for the dashboard frontend to consume
- /api/indicators/{symbol} is ready for single-asset detail views in the dashboard
- No blockers for Phase 02 Plan 03 (scanner integration)

---
*Phase: 02-analysis-engine*
*Completed: 2026-04-08*
