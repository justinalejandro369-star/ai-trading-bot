---
phase: 1
slug: data-foundation
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-06
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pytest.ini or pyproject.toml (Wave 0 installs) |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest tests/ -v --timeout=60`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | DATA-04 | — | N/A | unit | `pytest tests/test_provider_interface.py` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | DATA-05 | — | N/A | unit | `pytest tests/test_db_schema.py` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | DATA-01 | — | N/A | integration | `pytest tests/test_stock_ingestion.py` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | DATA-02 | — | N/A | integration | `pytest tests/test_crypto_ingestion.py` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | DATA-03 | — | N/A | integration | `pytest tests/test_timeframes.py` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 2 | DATA-01 | — | N/A | integration | `pytest tests/test_scheduler.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (test DB connection, mock API responses)
- [ ] `tests/test_provider_interface.py` — stubs for DATA-04 provider abstraction
- [ ] `tests/test_db_schema.py` — stubs for DATA-05 TimescaleDB schema
- [ ] `tests/test_stock_ingestion.py` — stubs for DATA-01 stock data
- [ ] `tests/test_crypto_ingestion.py` — stubs for DATA-02 crypto data
- [ ] `tests/test_timeframes.py` — stubs for DATA-03 multi-timeframe
- [ ] `tests/test_scheduler.py` — stubs for scheduling
- [ ] `pytest` + `pytest-timeout` + `pytest-asyncio` — test framework install

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Finnhub WebSocket connection stays alive | DATA-01 | Requires external service | Connect WS, verify heartbeat for 60s |
| CoinGecko rate limit not exceeded | DATA-02 | Requires monitoring over time | Run scheduler for 1 hour, check API response codes |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (TDD inline pattern: test files created within the same task as production code; no separate Wave 0 plan needed)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (revision 2026-04-06 — all blocker issues resolved)
