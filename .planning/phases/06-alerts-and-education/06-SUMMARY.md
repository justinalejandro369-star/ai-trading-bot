---
phase: "06"
plan: "06-01"
subsystem: alerts-and-education
tags: [alerts, telegram, discord, education, tooltips]
dependency_graph:
  requires: [phase-05-dashboard, phase-02-analysis-engine]
  provides: [alert-rules-api, alert-events-history, education-concepts-api, concept-tooltip, education-page]
  affects: [scheduler, main, dashboard]
tech_stack:
  added: [httpx-async-notifications]
  patterns: [pure-function-alert-engine, scheduler-job-pattern, no-auth-education-endpoint]
key_files:
  created:
    - backend/app/alerts/engine.py
    - backend/app/alerts/telegram_notifier.py
    - backend/app/alerts/discord_notifier.py
    - backend/app/alerts/jobs.py
    - backend/app/alerts/__init__.py
    - backend/app/models/alert.py
    - backend/alembic/versions/006_create_alerts_tables.py
    - backend/app/api/routes/alerts.py
    - backend/app/education/__init__.py
    - backend/app/education/content.py
    - backend/app/api/routes/education.py
    - backend/tests/test_alerts.py
    - backend/tests/test_education.py
    - frontend/src/components/education/ConceptTooltip.tsx
    - frontend/src/pages/Education.tsx
  modified:
    - backend/app/core/config.py
    - backend/app/ingestion/scheduler.py
    - backend/app/main.py
    - frontend/src/pages/Dashboard.tsx
    - .env.example
decisions:
  - "Education API is unprotected (no JWT dep) — educational content is non-sensitive, reduces friction for new users"
  - "Alert engine is a pure function (no DB I/O) — maximizes testability and reuse without mocking"
  - "ConceptTooltip uses inline data (not API fetch) — avoids async waterfall on every hover interaction"
  - "Alert check job runs every 5 min matching analysis_scan_job cadence — ensures alerts evaluate fresh signals"
metrics:
  duration: "25min"
  completed_date: "2026-04-08"
  tasks_completed: 2
  files_created: 15
  files_modified: 5
  tests_passing: 23
---

# Phase 6 Plan 1: Alerts and Education Summary

**One-liner:** Proactive Telegram/Discord alerts via pure-function engine with RSI/price/volume detectors, plus a 6-concept trading glossary with hover tooltips and full Education page wired as Dashboard 5th tab.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Alert engine + Telegram + Discord + API | 1d0bfbe | alerts/engine.py, alerts/jobs.py, models/alert.py, routes/alerts.py, migration 006 |
| 2 | Education content + frontend | b11d60c | education/content.py, routes/education.py, ConceptTooltip.tsx, Education.tsx, Dashboard.tsx |

## What Was Built

### Task 1 — Alert Engine + Notifications + API

**`backend/app/alerts/engine.py`** — `check_alerts(candles, rules, rsi_series)` pure function detecting:
- `price_spike`: `|close_t - close_{t-1}| / close_{t-1} * 100 >= threshold`
- `volume_surge`: `latest_volume / avg_volume(20) >= threshold`
- `trend_reversal`: RSI crosses 30 (bullish) or 70 (bearish)

**`backend/app/alerts/telegram_notifier.py`** — `send_telegram(message)` async, POST to Bot API with HTML parse_mode. Silently no-ops when token/chat_id not configured.

**`backend/app/alerts/discord_notifier.py`** — `send_discord(message)` async, POST to webhook with `username: TradingBot`. Silently no-ops when webhook_url not configured.

**`backend/app/models/alert.py`** — `AlertRule` (symbol, threshold_type, threshold_value) + `AlertEvent` (rule_id FK cascade, triggered_at, message) ORM models.

**`backend/alembic/versions/006_create_alerts_tables.py`** — Migration 006 creating `alert_rules` and `alert_events` tables.

**`backend/app/api/routes/alerts.py`** — CRUD: `POST /api/alerts/rules`, `GET /api/alerts/rules`, `DELETE /api/alerts/rules/{id}`, `GET /api/alerts/history`.

**`backend/app/alerts/jobs.py`** — `alert_check_job()` APScheduler job: loads all rules, fetches candles per symbol, evaluates engine, persists `AlertEvent`, dispatches Telegram + Discord.

**Scheduler:** 6th job `alert_check/5min` registered alongside existing 5 jobs.

**Config:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `DISCORD_WEBHOOK_URL` added to `settings` and `.env.example`.

### Task 2 — Education Content + Frontend

**`backend/app/education/content.py`** — 6 concepts: RSI (thresholds 30/70, momentum), MACD (signal line crossover), Bollinger Bands (squeeze/breakout, std dev 2), ADX (trend strength 20/25/40), ATR (volatility, stop-loss sizing), Sharpe Ratio (risk-adjusted return).

**`backend/app/api/routes/education.py`** — `GET /api/education/concepts` (all), `GET /api/education/concepts/{slug}`. No auth dependency — content is non-sensitive.

**`frontend/src/components/education/ConceptTooltip.tsx`** — Hover/focus tooltip for RSI, MACD, Bollinger Bands, ADX, ATR. Uses inline concept data (no API fetch on hover). Accessible via `tabIndex=0` + onFocus/onBlur.

**`frontend/src/pages/Education.tsx`** — Full glossary page: category sidebar (Momentum/Trend/Volatility/Performance), concept detail panel with explanation, key thresholds table, "how this bot uses it" callout.

**Dashboard:** 5th tab "Learn" wired to `<Education />` component.

## Tests

- `tests/test_alerts.py`: 20 tests covering price spike (above/below/down/zero-prior), volume surge (triggers/no-trigger/zero-avg), trend reversal (bullish/bearish/stable/no-rsi), edge cases (empty/single candle/multiple rules), notifier skip-when-unconfigured
- `tests/test_education.py`: 7 tests covering list all concepts, get RSI/MACD/BB by slug, 404 for unknown, required field validation

**All 23 tests GREEN.**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed bad DataFrame construction in multi-rule test**
- **Found during:** Task 1 test run
- **Issue:** Test `test_multiple_rules_multiple_triggers` passed arrays of mismatched lengths to `make_candles()`
- **Fix:** Unified closes and vols to same length (20 elements each)
- **Files modified:** `backend/tests/test_alerts.py`
- **Commit:** 1d0bfbe

**2. [Rule 3 - Blocking] uv sync required before tests**
- **Found during:** Task 1 test run
- **Issue:** `slowapi`, `secure`, `passlib` not installed in venv despite being in pyproject.toml
- **Fix:** Ran `uv sync` to install missing deps
- **Commit:** N/A (environment fix)

## Known Stubs

None — all concepts are fully populated with explanation, thresholds, how_we_use_it, and category. Education page fetches from real API endpoint. Alert engine evaluates real candle data.

## Self-Check: PASSED

Files created:
- backend/app/alerts/engine.py — FOUND
- backend/app/alerts/telegram_notifier.py — FOUND
- backend/app/alerts/discord_notifier.py — FOUND
- backend/app/alerts/jobs.py — FOUND
- backend/app/models/alert.py — FOUND
- backend/alembic/versions/006_create_alerts_tables.py — FOUND
- backend/app/api/routes/alerts.py — FOUND
- backend/app/education/content.py — FOUND
- backend/app/api/routes/education.py — FOUND
- frontend/src/components/education/ConceptTooltip.tsx — FOUND
- frontend/src/pages/Education.tsx — FOUND
- backend/tests/test_alerts.py — FOUND
- backend/tests/test_education.py — FOUND

Commits: 1d0bfbe, b11d60c — verified in git log.
