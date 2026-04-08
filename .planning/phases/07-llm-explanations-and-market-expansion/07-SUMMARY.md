---
phase: "07"
plan: "07"
subsystem: llm-explanations-and-market-expansion
tags: [llm, langchain, openai, forex, multi-timeframe, signal-explanation, alpha-vantage]
dependency-graph:
  requires: [phase-02-analysis-engine]
  provides: [llm-signal-explanations, multi-timeframe-agreement, forex-market-data, signal-card-ui]
  affects: [signals-api, scanner, scheduler, signal-feed-ui]
tech-stack:
  added: [langchain-openai>=0.3.0]
  patterns: [deferred-langchain-import-guard, prompt-grounded-in-verified-data, graceful-api-key-fallback]
key-files:
  created:
    - backend/app/analysis/explainer.py
    - backend/app/analysis/multiframe.py
    - backend/alembic/versions/007_add_explanation_to_signals.py
    - backend/app/ingestion/providers/forex_provider.py
    - backend/tests/test_explainer.py
    - backend/tests/test_forex.py
    - frontend/src/components/signals/SignalCard.tsx
    - .planning/phases/07-llm-explanations-and-market-expansion/07-VERIFICATION.md
  modified:
    - backend/app/models/signal.py
    - backend/app/analysis/scanner.py
    - backend/app/api/routes/signals.py
    - backend/app/core/config.py
    - backend/app/ingestion/scheduler.py
    - backend/pyproject.toml
    - frontend/src/components/signals/SignalFeed.tsx
    - frontend/src/types/index.ts
    - .env.example
decisions:
  - LLM explanations disabled by default (llm_enabled=False) — no key required to run the system; activate with OPENAI_API_KEY + LLM_ENABLED=true
  - Forex scoped to daily timeframes only — Alpha Vantage free tier too rate-limited for intraday (25 req/day)
  - settings imported at module level in explainer.py (not deferred) to enable patch-based test mocking
  - LangChain imports remain deferred inside generate_explanation() — no ImportError when langchain-openai not installed and LLM disabled
  - multiframe_agreement stored as JSON text column alongside explanation — consistent with existing reasons column pattern
metrics:
  duration: "~30min"
  completed: "2026-04-08"
  tasks: 2
  files: 17
---

# Phase 7: LLM Explanations and Market Expansion Summary

**One-liner:** LangChain gpt-4o-mini signal explanations grounded in verified IndicatorSet values, multi-timeframe 1H/4H/1D agreement detection, and Alpha Vantage forex ingestion for EUR/USD, GBP/USD, USD/JPY, AUD/USD.

## What Was Built

### Task 1: LLM Signal Explanations + Multi-Timeframe

**explainer.py** — `generate_explanation()` function:
- Gracefully disabled when `llm_enabled=False` or `openai_api_key=""` — returns `""` with no LangChain import error
- PromptTemplate contains only actual IndicatorSet field values; LLM explicitly told not to invent numbers
- Uses `langchain_openai.ChatOpenAI` with `gpt-4o-mini`, `temperature=0.3`, `max_tokens=200`
- try/except wraps the entire LLM call — any API error returns `""` without crashing the scanner

**multiframe.py** — `compute_multiframe_agreement()`:
- Queries signals table for same symbol across `['1H', '4H', '1D']` intervals
- Returns `{"1H": "BUY", "4H": "BUY", "1D": "BUY", "agreement": true}` dict
- Missing intervals excluded from agreement check (returns `{"agreement": false}` when no data)

**Migration 007** — adds `explanation` (Text) and `multiframe_agreement` (Text/JSON) columns to signals table.

**Scanner updated** — calls explainer + multiframe after scoring, upserts both fields. Signal API response includes both fields.

**Settings** — `openai_api_key` and `llm_enabled` added to config.py; `ALPHA_VANTAGE_API_KEY` also added.

### Task 2: Forex Market Data + SignalCard UI

**ForexProvider** — implements OHLCVProvider ABC:
- Fetches Alpha Vantage FX_DAILY for EUR/USD, GBP/USD, USD/JPY, AUD/USD
- volume=0.0 (FX_DAILY has no volume field — consistent with CoinGecko pattern)
- market="forex" on all returned candles
- Gracefully returns `[]` when API key not set (logs warning, no crash)
- Handles rate-limit `Information` key, HTTP errors, malformed rows

**Scheduler** — `forex_daily_job()` registered as 7th APScheduler job (24h interval).

**SignalCard.tsx** — extracted from SignalFeed with additions:
- Explanation text area (rendered only when explanation non-empty)
- Multi-timeframe badges (1H/4H/1D) colored by direction (green=BUY, red=SELL, slate=HOLD)
- "Aligned" label when agreement=true
- Falls back to top 2 signal reasons when LLM disabled

**SignalFeed.tsx** — refactored to delegate card rendering to SignalCard.

## Test Results

- `tests/test_explainer.py` — 10 tests: all pass (mocked LangChain/OpenAI, no real API calls)
- `tests/test_forex.py` — 10 tests: all pass (mocked httpx, no real Alpha Vantage calls)
- Total: 20/20 passing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] settings deferred import prevented test patching**
- **Found during:** Task 1 (test run)
- **Issue:** `settings` imported inside `generate_explanation()` made `patch("app.analysis.explainer.settings", ...)` fail with AttributeError
- **Fix:** Moved `from app.core.config import settings` to module-level import; kept langchain imports deferred inside function (still prevents ImportError when LLM disabled)
- **Files modified:** `backend/app/analysis/explainer.py`
- **Commit:** 99329f8

## Known Stubs

None — all functionality is wired. LLM explanation and multiframe_agreement are empty/`{"agreement": false}` by default (when LLM disabled or no scan data for multiple intervals), which is intentional documented behavior, not a stub.

## Self-Check: PASSED

Files created:
- backend/app/analysis/explainer.py — FOUND
- backend/app/analysis/multiframe.py — FOUND
- backend/alembic/versions/007_add_explanation_to_signals.py — FOUND
- backend/app/ingestion/providers/forex_provider.py — FOUND
- backend/tests/test_explainer.py — FOUND
- backend/tests/test_forex.py — FOUND
- frontend/src/components/signals/SignalCard.tsx — FOUND
- .planning/phases/07-llm-explanations-and-market-expansion/07-VERIFICATION.md — FOUND

Commits: 99329f8 (Task 1), 56565a7 (Task 2) — both verified in git log.
