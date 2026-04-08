# Requirements: AI Trading Bot

**Defined:** 2026-04-06
**Core Value:** Surface high-quality trading opportunities with clear reasoning and win-rate tracking, so users make informed decisions faster than manual scanning.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Ingestion

- [x] **DATA-01**: System ingests US stock OHLCV data via yfinance with Finnhub WebSocket for real-time updates
- [x] **DATA-02**: System ingests crypto data (BTC, ETH, top altcoins) via CoinGecko API
- [x] **DATA-03**: System supports multiple timeframes (1m, 5m, 15m, 1H, 4H, 1D candles)
- [x] **DATA-04**: Data provider abstraction layer allows swapping sources without code changes
- [x] **DATA-05**: System stores historical OHLCV data in TimescaleDB for fast time-series queries
- [ ] **DATA-06**: System researches and integrates forex data via best available free source (XE API, TradingView, Alpha Vantage, or alternative)

### Analysis Engine

- [ ] **ANLYS-01**: System computes technical indicators (RSI, MACD, Bollinger Bands, moving averages, ADX, volume)
- [x] **ANLYS-02**: AI detects entry/exit signals with confidence scores based on indicator convergence
- [ ] **ANLYS-03**: Each signal includes plain-language explanation of WHY it was generated (LLM-powered)
- [x] **ANLYS-04**: System scans across stocks + crypto simultaneously, ranking opportunities by score
- [ ] **ANLYS-05**: Multi-timeframe correlation — signals show agreement across 1H, 4H, and daily charts
- [x] **ANLYS-06**: Market regime detection labels current conditions (trending/ranging/volatile) per asset

### Backtesting

- [ ] **BKTS-01**: User can backtest strategies against historical data using vectorbt
- [ ] **BKTS-02**: Backtesting engine enforces look-ahead bias prevention by design
- [ ] **BKTS-03**: Backtest results show performance metrics: Sharpe ratio, max drawdown, win rate, profit factor
- [ ] **BKTS-04**: Backtest models transaction costs (slippage + commissions) for realistic results

### Paper Trading

- [x] **PAPER-01**: User has a paper trading account with configurable starting balance and fake money
- [x] **PAPER-02**: Paper trades simulate order fills with slippage modeling against real-time data
- [x] **PAPER-03**: User can view P&L tracking over time with visual equity curve
- [x] **PAPER-04**: User can compare paper trading results vs backtest predictions

### Dashboard

- [ ] **DASH-01**: Web dashboard displays TradingView-style candlestick charts with indicator overlays
- [ ] **DASH-02**: Real-time signal feed shows AI suggestions with reasoning, confidence, and entry/exit/stop-loss levels
- [ ] **DASH-03**: Portfolio view shows current positions, P&L, allocation breakdown
- [ ] **DASH-04**: Backtest results page with visual equity curves and performance metrics
- [ ] **DASH-05**: Dashboard updates in real-time via WebSocket connection

### Alerts & Notifications

- [ ] **ALERT-01**: System sends alerts for significant market movements (price spikes, volume surges, trend reversals)
- [ ] **ALERT-02**: User can configure alert channels: email, Telegram, and/or Discord
- [ ] **ALERT-03**: Alerts include context: what changed, why it matters, and any related AI signal
- [ ] **ALERT-04**: User can set custom alert thresholds (e.g., price change > 5%, volume > 2x average)

### Education

- [ ] **EDU-01**: Each AI signal includes plain-language reasoning explaining the opportunity
- [ ] **EDU-02**: Risk warnings clearly communicate confidence levels and paper-vs-live performance gap
- [ ] **EDU-03**: Built-in trading glossary with definitions for all technical terms (RSI, MACD, Sharpe ratio, etc.)
- [ ] **EDU-04**: Strategy guides explaining day trading vs swing trading approaches

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Auto-Execution

- **AUTO-01**: User can enable auto-execution of trades via brokerage API (Alpaca, IBKR)
- **AUTO-02**: Auto-execution requires explicit opt-in with risk disclaimers
- **AUTO-03**: Kill switch to immediately halt all auto-trading

### Advanced ML

- **ML-01**: Offline ML model training for price prediction (LSTM, transformer-based)
- **ML-02**: Walk-forward optimization for strategy parameter tuning
- **ML-03**: Sentiment analysis from news and social media feeds

### Options & Advanced Markets

- **OPT-01**: Options chain data with Greeks and implied volatility
- **OPT-02**: Options strategy suggestions (covered calls, spreads, etc.)

### Mobile

- **MOB-01**: Native mobile app with push notifications
- **MOB-02**: Mobile-optimized dashboard views

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real money brokerage integration | MVP is simulation-only; reduces regulatory and financial risk |
| High-frequency trading (sub-second) | Not the goal; focus is on day/swing trading timeframes |
| Paid data APIs | MVP validates with free sources; upgrade path after validation |
| Options real-time data | No free API provides computed Greeks/IV; deferred to v2 |
| Social/copy trading | Adds user management complexity; not core value |
| Mobile app | Web-first; mobile alerts via Telegram/Discord cover mobile needs for now |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 1 | Complete |
| DATA-04 | Phase 1 | Complete |
| DATA-05 | Phase 1 | Complete |
| DATA-06 | Phase 7 | Pending |
| ANLYS-01 | Phase 2 | Pending |
| ANLYS-02 | Phase 2 | Complete |
| ANLYS-03 | Phase 7 | Pending |
| ANLYS-04 | Phase 2 | Complete |
| ANLYS-05 | Phase 7 | Pending |
| ANLYS-06 | Phase 2 | Complete |
| BKTS-01 | Phase 3 | Pending |
| BKTS-02 | Phase 3 | Pending |
| BKTS-03 | Phase 3 | Pending |
| BKTS-04 | Phase 3 | Pending |
| PAPER-01 | Phase 4 | Complete |
| PAPER-02 | Phase 4 | Complete |
| PAPER-03 | Phase 4 | Complete |
| PAPER-04 | Phase 4 | Complete |
| DASH-01 | Phase 5 | Pending |
| DASH-02 | Phase 5 | Pending |
| DASH-03 | Phase 5 | Pending |
| DASH-04 | Phase 5 | Pending |
| DASH-05 | Phase 5 | Pending |
| ALERT-01 | Phase 6 | Pending |
| ALERT-02 | Phase 6 | Pending |
| ALERT-03 | Phase 6 | Pending |
| ALERT-04 | Phase 6 | Pending |
| EDU-01 | Phase 7 | Pending |
| EDU-02 | Phase 6 | Pending |
| EDU-03 | Phase 6 | Pending |
| EDU-04 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 33 total
- Mapped to phases: 33
- Unmapped: 0

---
*Requirements defined: 2026-04-06*
*Last updated: 2026-04-06 after roadmap creation — all 33 requirements mapped*
