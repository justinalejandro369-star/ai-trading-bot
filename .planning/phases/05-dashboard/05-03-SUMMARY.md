---
phase: "05-dashboard"
plan: "03"
subsystem: "frontend"
tags: ["react", "lightweight-charts", "tanstack-query", "recharts", "websocket", "typescript"]
dependency_graph:
  requires: ["05-01", "05-02"]
  provides: ["candlestick-chart", "signal-feed", "portfolio-view", "backtest-results", "websocket-hook"]
  affects: ["frontend-dashboard"]
tech_stack:
  added: []
  patterns: ["TanStack Query for REST data fetching", "Zustand WebSocket state injection via setQueryData", "lightweight-charts v5 addSeries API", "Recharts for portfolio/backtest charts"]
key_files:
  created:
    - frontend/src/types/index.ts
    - frontend/src/api/market.ts
    - frontend/src/api/signals.ts
    - frontend/src/api/paper.ts
    - frontend/src/api/backtest.ts
    - frontend/src/hooks/useWebSocket.ts
    - frontend/src/components/chart/CandlestickChart.tsx
    - frontend/src/components/chart/EquityCurveChart.tsx
    - frontend/src/components/chart/PnLPieChart.tsx
    - frontend/src/components/signals/SignalFeed.tsx
    - frontend/src/components/portfolio/PortfolioView.tsx
    - frontend/src/components/backtest/BacktestResults.tsx
  modified:
    - frontend/src/pages/Dashboard.tsx
decisions:
  - "lightweight-charts v5 addSeries 3rd arg is paneIndex (number), not PaneOptions object — plan had wrong type; fixed to pass integer 1"
  - "Recharts Tooltip formatter types require unknown params cast to concrete types — stricter in recharts v3"
  - "RSI sub-pane on pane index 1 with no initial data — harmless empty pane until real RSI data is wired"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-08"
  tasks: 2
  files: 13
---

# Phase 05 Plan 03: Dashboard Components Summary

Full dashboard built: candlestick chart, signal feed, portfolio view, and backtest results — all wired with real API data fetching via TanStack Query and real-time WebSocket updates.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | API layer + WebSocket hook + CandlestickChart + SignalFeed | e92428b | 8 files created |
| 2 | Portfolio view, Backtest results, Dashboard page wiring | 9562d38 | 5 files created, Dashboard.tsx updated |

## What Was Built

**API Layer** (`src/api/`): Four typed API modules — market (candles + indicators), signals (top N), paper (account, equity curve, compare), backtest (run mutation). All use the existing `apiGet`/`apiPost` client with cookie-based auth.

**Types** (`src/types/index.ts`): Shared TypeScript interfaces for `Candle`, `Signal`, `PaperAccount`, `PaperPosition`, `EquityPoint`, `BacktestResult`.

**useWebSocket hook**: Reconnecting WebSocket (3s retry on unexpected close). Handles `signal_update` by prepending signal to `['signals','top']` query cache. Handles `price_tick` by appending candle to `['candles', symbol]` cache (rolling 200-bar window). Ignores `ping` keepalives.

**CandlestickChart**: lightweight-charts v5 with `addSeries(CandlestickSeries, options)`. Backend DESC candles reversed to ASC in `getCandles()`. RSI LineSeries on pane index 1. Symbol selector (AAPL/MSFT/GOOGL/BTC-USD/ETH-USD). Resize observer for responsive width.

**SignalFeed**: TanStack Query polling every 60s with 30s stale time. Direction badge (BUY=green, SELL=red, HOLD=gray), confidence progress bar, entry/stop-loss/target grid, reason list (max 2). `data-testid="signal-{symbol}"` on each card. Skeleton loading, empty state.

**EquityCurveChart**: Recharts LineChart with dark theme. Formats dates and dollar values in tooltip. `data-testid="equity-curve-chart"`.

**PnLPieChart**: Recharts PieChart computing allocation % from position values. `data-testid="allocation-pie-chart"`.

**PortfolioView**: Account balance/P&L/return summary cards. Positions table with Symbol/Qty/Avg/Current/P&L/% columns. Equity curve + allocation pie side by side. `data-testid="portfolio-view"` and `data-testid="positions-table"`.

**BacktestResults**: Run form with symbol input + interval select. `useMutation` for POST /api/backtest. Metrics cards (Sharpe, drawdown, win rate, profit factor). Equity curve from result. `data-testid="backtest-results"`, `data-testid="backtest-metrics"`, `data-testid="backtest-equity-chart"`.

**Dashboard.tsx**: `useWebSocket` called on mount with `VITE_WS_URL` env var (fallback `ws://localhost:8000`). All 4 tabs replaced with real components. `data-testid="dashboard-nav"` and `data-testid="dashboard-tabs"`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] lightweight-charts v5 addSeries pane arg type**
- **Found during:** Task 1 — TypeScript compile
- **Issue:** Plan specified `{ height: 120 }` as third arg to `addSeries`. Actual v5 signature is `paneIndex?: number`.
- **Fix:** Changed to `chart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 1 }, 1)`
- **Files modified:** `frontend/src/components/chart/CandlestickChart.tsx`
- **Commit:** e92428b

**2. [Rule 1 - Bug] Recharts Tooltip formatter strict types**
- **Found during:** Task 2 — TypeScript compile
- **Issue:** recharts v3 Tooltip `formatter` and `labelFormatter` use `ValueType | undefined` / `ReactNode` — stricter than `number` / `string`.
- **Fix:** Cast params to `unknown` then to concrete types in EquityCurveChart and PnLPieChart
- **Files modified:** `frontend/src/components/chart/EquityCurveChart.tsx`, `frontend/src/components/chart/PnLPieChart.tsx`
- **Commit:** 9562d38

**3. [Rule 1 - Bug] Unused `directionVariant` function in SignalFeed**
- **Found during:** Task 1 — TypeScript compile (TS6133)
- **Fix:** Removed the unused function (was replaced by inline `directionClass`)
- **Files modified:** `frontend/src/components/signals/SignalFeed.tsx`
- **Commit:** e92428b

## Known Stubs

- **RSI sub-pane** (`CandlestickChart.tsx`): RSI series created on pane index 1 but receives no data — will render as empty pane until `getIndicators()` data is fetched and wired in a future plan.
- **ACCOUNT_ID hardcoded to 1** (`PortfolioView.tsx`): MVP single-user constraint. Multi-account support deferred.

## Self-Check: PASSED

- frontend/src/types/index.ts — FOUND
- frontend/src/api/market.ts — FOUND
- frontend/src/api/signals.ts — FOUND
- frontend/src/api/paper.ts — FOUND
- frontend/src/api/backtest.ts — FOUND
- frontend/src/hooks/useWebSocket.ts — FOUND
- frontend/src/components/chart/CandlestickChart.tsx — FOUND
- frontend/src/components/chart/EquityCurveChart.tsx — FOUND
- frontend/src/components/chart/PnLPieChart.tsx — FOUND
- frontend/src/components/signals/SignalFeed.tsx — FOUND
- frontend/src/components/portfolio/PortfolioView.tsx — FOUND
- frontend/src/components/backtest/BacktestResults.tsx — FOUND
- Commit e92428b — FOUND
- Commit 9562d38 — FOUND
- TypeScript build: zero errors
- Vite build: clean (940KB bundle, chunk size warning only — not an error)
- `addSeries(CandlestickSeries` confirmed in CandlestickChart.tsx
- `.reverse()` confirmed in api/market.ts
