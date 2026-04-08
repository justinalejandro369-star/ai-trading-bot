---
phase: 03
slug: backtesting-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 03 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | backend/pyproject.toml |
| **Quick run command** | `PYTHONPATH=backend uv --project backend run pytest tests/test_backtest.py -q` |
| **Full suite command** | `PYTHONPATH=backend uv --project backend run pytest tests/ -q` |
| **Estimated runtime** | ~8 seconds |

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 03-01-01 | 01 | 1 | BKTS-01 | unit | `pytest tests/test_backtest.py::test_engine -q` | ⬜ pending |
| 03-01-02 | 01 | 1 | BKTS-02/03/04 | unit | `pytest tests/test_backtest.py -q` | ⬜ pending |
| 03-02-01 | 02 | 2 | BKTS-01 | integration | `pytest tests/test_backtest_api.py -q` | ⬜ pending |

## Wave 0 Requirements

- [ ] `tests/test_backtest.py` — stubs for BKTS-01 through BKTS-04
- [ ] `tests/test_backtest_api.py` — API endpoint tests

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Backtest completes within seconds on 3yr daily data | BKTS-01 | Timing varies by hardware | Run POST /api/backtest with 3yr date range, verify < 5s response |

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
