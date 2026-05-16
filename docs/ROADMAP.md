# Roadmap

The system was built in strict dependency order: a robust data pipeline before signals, signals before paper trading, the full loop before LLM explanations and market expansion. Seven phases shipped v1; Phase 8 (pluggable strategies) is the next milestone and the reason this repo is public.

## Status overview

| Phase | Status | Goal |
|---|---|---|
| 1. Data Foundation | ✅ Done (2026-04-08) | Normalized OHLCV ingestion for stocks and crypto |
| 2. Analysis Engine | ✅ Done (2026-04-08) | Technical indicators + rule-based ranked signals |
| 3. Backtesting Engine | 🚧 In progress | vectorbt + `shift(1)` look-ahead prevention |
| 4. Paper Trading | ✅ Done (2026-04-08) | Slippage-modeled fills, equity curve |
| 5. Dashboard | 🚧 In progress | Charts, signal feed, portfolio, real-time WebSocket |
| 6. Alerts & Education | 📋 Planned | Telegram/Discord, glossary, risk warnings |
| 7. LLM Explanations & Market Expansion | ✅ Done | LLM reasoning, multi-timeframe agreement, forex |
| 8. Pluggable Strategies | 📋 Next | `BaseStrategy` ABC, registry, compare UI |

---

## Phase 1 — Data Foundation ✅

**Goal:** Normalized, queryable OHLCV data for US stocks and crypto available to all downstream components.

**Success criteria (all met):**
1. US stock OHLCV candles (1m through 1D) stored in DB and updated on schedule
2. Crypto OHLCV (BTC, ETH, top altcoins) updated on schedule
3. Multiple timeframes (1m / 5m / 15m / 1H / 4H / 1D) available per asset
4. Data sources hot-swappable via `OHLCVProvider` ABC — no strategy code touched
5. Historical OHLCV queries by symbol+range return in under one second

**Requirements covered:** DATA-01 through DATA-05.

## Phase 2 — Analysis Engine ✅

**Goal:** Continuous market scanning that generates ranked signals with scores and reasoning.

**Success criteria (all met):**
1. Technical indicators (RSI, MACD, Bollinger Bands, MAs, ADX, volume) computable per asset
2. BUY/SELL/HOLD signals with confidence 0–100 derived from indicator convergence
3. Scanner ranks all monitored assets; top opportunities retrievable via API
4. Each asset labeled with regime (trending / ranging / volatile)

**Requirements covered:** ANLYS-01, ANLYS-02, ANLYS-04, ANLYS-06.

## Phase 3 — Backtesting Engine 🚧

**Goal:** Trustworthy historical performance metrics, no look-ahead bias.

**Success criteria:**
1. Backtest any stored asset + strategy combination, results in seconds
2. Reports Sharpe ratio, max drawdown, win rate, profit factor
3. Engine enforces `shift(1)` signal delay (auditable by test)
4. Configurable commission + slippage applied to results

**Requirements covered:** BKTS-01 through BKTS-04. Engine implemented, API route still in flight.

## Phase 4 — Paper Trading Simulator ✅

**Goal:** Trade with fake money against live data, compare to backtest predictions.

**Success criteria (all met):**
1. Configurable starting balance, place simulated buy/sell orders
2. Order fills simulate slippage against real-time prices
3. Running P&L equity curve
4. Side-by-side paper-vs-backtest comparison

**Requirements covered:** PAPER-01 through PAPER-04.

## Phase 5 — Dashboard 🚧

**Goal:** All system outputs visible through a responsive web UI with real-time updates.

**Success criteria:**
1. Candlestick charts with RSI/MACD/Bollinger overlays and signal markers
2. Ranked signal feed with entry/exit/stop levels
3. Portfolio view with positions, P&L, allocation
4. Backtest results page with equity curve and metrics table
5. Real-time updates via WebSocket — no page refresh

**Requirements covered:** DASH-01 through DASH-05.

## Phase 6 — Alerts and Education 📋

**Goal:** Proactive alerts on significant events; plain-language education for new traders.

**Success criteria:**
1. Alerts for price spikes, volume surges, trend reversals via email/Telegram/Discord
2. Custom alert thresholds configurable via dashboard
3. Each alert includes what changed, why it matters, and the related signal
4. Risk warnings + confidence levels alongside every signal
5. Built-in glossary defining all technical terms

**Requirements covered:** ALERT-01 through ALERT-04, EDU-02 through EDU-04.

## Phase 7 — LLM Explanations and Market Expansion ✅

**Goal:** Signals explained in natural language by an LLM grounded in verified data; multi-timeframe correlation surfaced; forex integrated.

**Success criteria (all met):**
1. Plain-language explanations citing verified indicator values (no hallucinated numbers)
2. Multi-timeframe agreement indicators (1H / 4H / daily) on signal cards
3. Forex daily data integrated and visible in the opportunity feed
4. LLM explanations cached per signal — no duplicate API calls

**Requirements covered:** ANLYS-03, ANLYS-05, DATA-06, EDU-01.

---

## Phase 8 — Pluggable Strategies (next, the reason this repo is public)

**Goal:** Any contributor can drop their own algorithm into a branch and compare it against the baseline.

**Planned success criteria:**
1. `BaseStrategy` ABC under `backend/app/strategies/` — same pattern as `OHLCVProvider`
2. Registry + decorator: `@register_strategy` colocates name + class
3. `score_signal()` (current monolithic logic) becomes `BaselineStrategy` — zero behavior change
4. Backtest engine deletes duplicated vectorized logic, routes through `strategy.generate_entries_exits(df)`
5. Alembic migration adds `strategy_name` to `signals` PK and `backtest_runs`
6. Multiple strategies coexist per asset — `signals` PK becomes `(symbol, interval, strategy_name)`
7. New API endpoints: `GET /api/strategies`, filter params on `/api/signals` and `/api/backtest`
8. Frontend `/backtest/compare` page overlays equity curves from two strategies with metric table
9. Example strategy file `example_simple_ma_crossover.py` ships as documentation
10. Parity test locks baseline behavior (`BaselineStrategy().generate_signal(ind) == score_signal(ind)`)

**Contributor experience:**
- Fork → `git checkout -b strategy/<name>` → drop one file → run tests → backtest → compare
- See [`STRATEGIES.md`](STRATEGIES.md) for the full interface and example

## Future ideas (post-v1)

- **Options chains** — IV surface, Greeks, option-flow signals
- **Multi-account paper trading** — let users compare their own strategies to each other on the same dashboard
- **Strategy marketplace** — community-contributed strategies under `backend/app/strategies/community/` with parity-checked PRs
- **Live execution** (broker integration) — explicit opt-in, well behind a feature flag, real-money disclaimer
- **Mobile app** — React Native shell consuming the same FastAPI backend
