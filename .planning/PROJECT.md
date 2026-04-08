# AI Trading Bot

## What This Is

An AI-powered trading assistant that scans multiple financial markets (stocks, crypto, forex, options), identifies the best opportunities using artificial intelligence, and presents actionable suggestions with profitability estimates. Users can simulate strategies through backtesting and paper trading before committing real money. The MVP focuses on AI-driven suggestions — not auto-execution — delivered through a web dashboard.

## Core Value

The AI must surface high-quality trading opportunities with clear reasoning and win-rate tracking, so users can make informed decisions faster than they could manually scanning markets.

## Requirements

### Validated

- [x] Multi-market data ingestion (stocks, crypto) via free APIs — Validated in Phase 01: Data Foundation
- [x] Normalized OHLCV data pipeline with TimescaleDB hypertable storage — Validated in Phase 01: Data Foundation
- [x] Provider abstraction (OHLCVProvider ABC) enabling new sources without touching other modules — Validated in Phase 01: Data Foundation
- [x] Conflict-safe upsert layer (no duplicate candles) — Validated in Phase 01: Data Foundation
- [x] Scheduled background fetch (Celery/APScheduler) with REST query endpoint — Validated in Phase 01: Data Foundation

### Active

- [ ] Multi-market data ingestion (stocks, crypto, forex, options) via free APIs and scraping
- [ ] AI-powered market scanning that identifies trading opportunities across timeframes (day trading and swing trading)
- [ ] Suggestion engine that presents opportunities with reasoning, entry/exit points, and estimated profitability
- [ ] Backtesting engine to test strategies against historical data
- [ ] Paper trading simulator with fake money and real market data
- [ ] Web dashboard with charts, opportunity feed, and portfolio tracking
- [ ] Win rate tracking and performance analytics for suggestions
- [ ] Educational context — explains why opportunities are flagged, teaching users as they go

### Out of Scope

- Auto-execution of trades — MVP is suggestions only, auto-trading is v2+
- Paid data APIs — MVP uses free sources only (Yahoo Finance, free tiers, scraping)
- Mobile app — web-first, mobile alerts can come later
- Real money brokerage integration — simulation only for MVP
- High-frequency trading / sub-second execution — not the goal
- ML model training from scratch (like "Meadowfish" offline prediction) — deferred to future version after MVP validates the approach

## Context

- User has no prior trading experience — the bot needs to be educational and explain its reasoning
- All four markets (stocks, crypto, forex, options) are desired, but research should guide MVP prioritization based on free data availability and complexity
- Trading timeframes span day trading (minutes to hours) to swing trading (days to weeks)
- The system should leverage existing open-source trading tools and libraries to accelerate development
- Community research (Reddit, Quora, forums) should inform what users hate about existing tools so we can avoid those pitfalls
- Future versions will add: auto-execution, ML prediction models, paid data feeds, mobile alerts

## Constraints

- **Data**: Free sources only — Yahoo Finance, CoinGecko, free API tiers, web scraping where necessary
- **Tech stack**: Research-driven — let domain research guide the best stack (Python likely for finance/ML ecosystem)
- **Deployment**: Web dashboard accessible via browser
- **Budget**: Zero ongoing costs for data — infrastructure costs should be minimal

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Suggestions-first, no auto-trading | Safer for a user learning trading; reduces regulatory/financial risk | — Pending |
| Free data sources only | MVP validation before investing in paid feeds | — Pending |
| Web dashboard as primary interface | Visual charts and data exploration are essential for trading decisions | — Pending |
| Research guides market prioritization | User wants all 4 markets but is flexible on MVP scope based on feasibility | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-06 after initialization*
