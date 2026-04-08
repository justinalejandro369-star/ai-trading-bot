# Deferred Items - Phase 03 Backtesting Engine

## Pre-existing Test Failures (out of scope for Phase 03)

### Circular Import: tests/test_analysis_api.py and tests/test_scanner.py

**Discovered during:** Phase 03 Plan 01 execution
**Scope:** Pre-existing in Phase 02 code — not caused by Phase 03 changes

**Error:**
```
ImportError: cannot import name 'CCXT_CRYPTO_SYMBOLS' from partially initialized module 
'app.ingestion.scheduler' (most likely due to a circular import)
```

**Root cause:** `app/analysis/scanner.py` imports from `app/ingestion/scheduler.py`, and `app/ingestion/scheduler.py` imports back from `app/analysis/scanner.py`. This circular import was present before Phase 03 execution.

**Impact:** `tests/test_analysis_api.py` and `tests/test_scanner.py` fail to collect.

**Recommended fix:** Move shared constants (CCXT_CRYPTO_SYMBOLS, STOCK_WATCHLIST) to `app/core/watchlists.py` and import from there in both scheduler and scanner (pattern already used in Phase 02 for SCAN_INTERVAL).

**Deferred to:** Phase 02 bug fix or standalone fix before Phase 04.
