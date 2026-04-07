# Roadmap: AI Trading Bot

## Overview

The system is built in strict dependency order: a robust data pipeline must exist before signals can be generated, signals must be validated before paper trading begins, and the full core loop must be proven before adding LLM explanations or expanding to additional markets. Seven phases carry all 33 v1 requirements from raw market data ingestion through to an AI-explained, multi-market trading dashboard.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Data Foundation** - Ingest and store normalized OHLCV data for stocks and crypto via free APIs
- [ ] **Phase 2: Analysis Engine** - Compute technical indicators and generate rule-based AI signals with scores
- [ ] **Phase 3: Backtesting Engine** - Validate signal quality against historical data with look-ahead bias prevention
- [ ] **Phase 4: Paper Trading Simulator** - Simulate trading with fake money against live data with P&L tracking
- [ ] **Phase 5: Dashboard** - Web dashboard with charts, signal feed, portfolio view, and real-time updates
- [ ] **Phase 6: Alerts and Education** - Configurable alert channels and educational context for new traders
- [ ] **Phase 7: LLM Explanations and Market Expansion** - LLM-powered signal reasoning, multi-timeframe correlation, and forex data

## Phase Details

### Phase 1: Data Foundation
**Goal**: Normalized, queryable OHLCV data for US stocks and crypto is available to all downstream components
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05
**Success Criteria** (what must be TRUE):
  1. System stores US stock OHLCV candles (1m through 1D) in the database updated on a schedule without manual intervention
  2. System stores crypto OHLCV data for BTC, ETH, and top altcoins updated on a schedule
  3. Multiple timeframes (1m, 5m, 15m, 1H, 4H, 1D) are available for any stored asset
  4. A new data source can be swapped in by implementing the provider interface without changing strategy code
  5. Historical OHLCV queries by symbol and time range return results in under one second
**Plans**: TBD

### Phase 2: Analysis Engine
**Goal**: The system continuously scans stored market data, generates ranked trading signals with scores and template-based reasoning
**Depends on**: Phase 1
**Requirements**: ANLYS-01, ANLYS-02, ANLYS-04, ANLYS-06
**Success Criteria** (what must be TRUE):
  1. Technical indicators (RSI, MACD, Bollinger Bands, moving averages, ADX, volume) are computed from stored OHLCV and queryable per asset
  2. The system generates BUY/SELL/HOLD signals with confidence scores (0-100) derived from indicator convergence
  3. The scanner ranks all monitored assets by opportunity score and the top opportunities are retrievable via API
  4. Each asset is labeled with a current market regime (trending / ranging / volatile)
**Plans**: TBD

### Phase 3: Backtesting Engine
**Goal**: Users can test signal strategies against historical data and receive trustworthy performance metrics that are free of look-ahead bias
**Depends on**: Phase 2
**Requirements**: BKTS-01, BKTS-02, BKTS-03, BKTS-04
**Success Criteria** (what must be TRUE):
  1. User can run a backtest on any stored asset and strategy combination and receive results within seconds
  2. Backtest results show Sharpe ratio, max drawdown, win rate, and profit factor
  3. Backtest engine enforces shift(1) signal delay — no signal at time T uses data with timestamp >= T (verifiable by audit test)
  4. Transaction costs (configurable commission and slippage) are deducted from all backtest results
**Plans**: TBD

### Phase 4: Paper Trading Simulator
**Goal**: Users can trade with fake money against live market data and compare simulated results to backtest predictions
**Depends on**: Phase 3
**Requirements**: PAPER-01, PAPER-02, PAPER-03, PAPER-04
**Success Criteria** (what must be TRUE):
  1. User has a paper account with configurable starting balance and can place simulated buy/sell orders
  2. Order fills simulate slippage against real-time market prices (not perfect-fill execution)
  3. User can view a running P&L equity curve showing account value over time
  4. User can see a side-by-side comparison of paper trading results vs. backtest predictions for the same strategy
**Plans**: TBD

### Phase 5: Dashboard
**Goal**: Users can view all system outputs — charts, signals, portfolio, and analytics — through a responsive web interface with real-time updates
**Depends on**: Phase 4
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. User can view candlestick charts for any stored asset with indicator overlays (RSI, MACD, Bollinger Bands) and signal markers
  2. The signal feed displays ranked AI opportunities with confidence score, entry price, exit target, and stop-loss level
  3. Portfolio view shows current paper positions, total P&L, and allocation breakdown
  4. Backtest results page renders an equity curve and performance metrics table
  5. Signal feed and chart prices update in real-time via WebSocket without a page refresh
**Plans**: TBD
**UI hint**: yes

### Phase 6: Alerts and Education
**Goal**: Users receive proactive alerts on significant market events and have access to educational context that explains trading concepts in plain language
**Depends on**: Phase 5
**Requirements**: ALERT-01, ALERT-02, ALERT-03, ALERT-04, EDU-02, EDU-03, EDU-04
**Success Criteria** (what must be TRUE):
  1. User receives alerts for price spikes, volume surges, and trend reversals via at least one configured channel (email, Telegram, or Discord)
  2. User can configure custom alert thresholds (e.g., price change > 5%, volume > 2x average) through the dashboard
  3. Each alert message includes what changed, why it matters, and any related AI signal
  4. Dashboard displays risk warnings and confidence levels alongside every signal with a paper-vs-live performance disclaimer
  5. A built-in glossary defines all technical terms (RSI, MACD, Sharpe ratio, etc.) accessible from any chart or signal view
**Plans**: TBD

### Phase 7: LLM Explanations and Market Expansion
**Goal**: Signals are explained in natural language by an LLM grounded in verified data, multi-timeframe correlation is surfaced, and forex market data is integrated
**Depends on**: Phase 6
**Requirements**: ANLYS-03, ANLYS-05, DATA-06, EDU-01
**Success Criteria** (what must be TRUE):
  1. Each AI signal includes a plain-language explanation of why the opportunity was flagged, citing specific verified indicator values (no hallucinated numbers)
  2. Signal cards show multi-timeframe agreement indicators — whether the signal is confirmed on 1H, 4H, and daily charts simultaneously
  3. Forex data (daily/swing timeframes) is ingested from the best available free source and appears in the opportunity feed
  4. LLM explanations are cached per signal — re-fetching the same signal does not trigger a new LLM call
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 0/? | Not started | - |
| 2. Analysis Engine | 0/? | Not started | - |
| 3. Backtesting Engine | 0/? | Not started | - |
| 4. Paper Trading Simulator | 0/? | Not started | - |
| 5. Dashboard | 0/? | Not started | - |
| 6. Alerts and Education | 0/? | Not started | - |
| 7. LLM Explanations and Market Expansion | 0/? | Not started | - |
