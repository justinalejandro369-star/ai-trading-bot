---
phase: 02
slug: analysis-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | backend/pyproject.toml |
| **Quick run command** | `PYTHONPATH=backend uv --project backend run pytest tests/test_indicators.py -q` |
| **Full suite command** | `PYTHONPATH=backend uv --project backend run pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `PYTHONPATH=backend uv --project backend run pytest tests/test_indicators.py -q`
- **After every plan wave:** Run `PYTHONPATH=backend uv --project backend run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | ANLYS-01 | unit | `pytest tests/test_indicators.py -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | ANLYS-01 | unit | `pytest tests/test_indicators.py -q` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | ANLYS-02 | unit | `pytest tests/test_signals.py -q` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | ANLYS-04 | unit | `pytest tests/test_signals.py -q` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 3 | ANLYS-06 | integration | `pytest tests/test_scanner.py -q` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 3 | ANLYS-06 | integration | `pytest tests/test_scanner.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_indicators.py` — stubs for ANLYS-01 (indicator computation)
- [ ] `tests/test_signals.py` — stubs for ANLYS-02 (signal generation) and ANLYS-04 (market regime)
- [ ] `tests/test_scanner.py` — stubs for ANLYS-06 (scanner/ranking)
- [ ] `tests/conftest.py` — already exists from Phase 1, extend with analysis fixtures

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Top opportunities API response quality | ANLYS-06 | Requires live data and human judgment on signal quality | Start server, call GET /api/signals/top, verify ranking makes intuitive sense |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
