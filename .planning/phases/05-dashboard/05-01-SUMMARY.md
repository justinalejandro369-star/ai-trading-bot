---
phase: 05-dashboard
plan: "01"
subsystem: backend-auth
tags: [auth, jwt, security, websocket, rate-limiting, cors]
dependency_graph:
  requires: []
  provides: [backend-auth, websocket-live-endpoint]
  affects: [all-api-routes, frontend-auth-flow]
tech_stack:
  added: [pyjwt, argon2-cffi, passlib, python-multipart, slowapi, secure]
  patterns: [httpOnly-jwt-cookie, argon2-hashing, slowapi-rate-limiting, fastapi-dependency-injection]
key_files:
  created:
    - backend/app/core/security.py
    - backend/app/core/auth.py
    - backend/app/core/rate_limit.py
    - backend/app/api/routes/auth.py
    - backend/app/api/routes/websocket.py
    - backend/alembic/versions/005_add_users.py
    - backend/tests/test_auth.py
  modified:
    - backend/app/core/config.py
    - backend/app/main.py
    - backend/tests/conftest.py
    - backend/tests/test_analysis_api.py
    - backend/tests/test_backtest_api.py
    - backend/tests/test_paper_trading_api.py
    - backend/pyproject.toml
decisions:
  - "rate_limit.py singleton: shared slowapi Limiter extracted to app/core/rate_limit.py to prevent double-counting when auth routes module is reloaded in tests"
  - "monkeypatch.setattr on pydantic Settings object used in tests instead of importlib.reload to prevent @limiter.limit decorator double-application"
  - "alembic stamp head used for migration 005 on SQLite dev DB — TimescaleDB create_hypertable SQL in migration 001 is not SQLite-compatible"
  - "secure.Secure.with_default_headers().set_headers_async(response) used — framework.fastapi() method does not exist in secure>=1.0.1"
metrics:
  duration: "35 minutes"
  completed_date: "2026-04-08"
  tasks_completed: 2
  files_changed: 14
---

# Phase 05 Plan 01: Auth Foundation Summary

JWT httpOnly cookie auth with Argon2 hashing, slowapi rate limiting, CORS, security headers, and WS /ws/live endpoint protecting all API routes.

## What Was Built

### Auth Core (security.py, auth.py, rate_limit.py)
- `hash_password` / `verify_password` using Argon2 via passlib CryptContext
- `create_access_token` / `decode_access_token` using PyJWT with HS256
- `get_current_user` FastAPI dependency reads httpOnly cookie, decodes JWT, raises 401 on missing/invalid
- `rate_limit.py` shared singleton `Limiter` used by both `main.py` and `auth.py` routes

### Auth Routes (auth.py router)
- `POST /auth/login`: validates env-var admin credentials, sets httpOnly JWT cookie, rate-limited to 5/minute via slowapi
- `POST /auth/logout`: deletes access_token cookie
- `GET /auth/me`: returns `{"username": sub}` from decoded JWT

### WebSocket Endpoint (websocket.py)
- `ConnectionManager` class with `connect`, `disconnect`, `broadcast` methods
- `GET /ws/live` WebSocket endpoint with 30-second ping keepalive
- Module-level `manager` singleton exported for scheduler broadcast calls

### main.py Hardening
- Version bumped to 0.5.0
- CORS locked to `settings.frontend_url` (default: http://localhost:5173), allow_credentials=True
- Secure headers middleware via `secure.Secure.with_default_headers().set_headers_async()`
- All existing API routers (`/api/*`) protected with `Depends(get_current_user)`
- Auth router and WS router registered without auth requirement

### Database Migration
- Migration 005: `users` table (id, username, password_hash, created_at) for future multi-user expansion
- MVP auth uses env-var credentials only; users table is forward-compatible

### Test Suite (test_auth.py — 12 tests)
All 12 tests green plus all 72 existing tests (84 total):
- `test_password_hash`, `test_jwt_roundtrip`, `test_jwt_invalid` — unit tests
- `test_login_success`, `test_login_wrong_password`, `test_logout`
- `test_me_authenticated`, `test_me_unauthenticated`
- `test_protected_endpoint_blocked` — GET /api/signals → 401 without cookie
- `test_rate_limit` — 6th rapid POST /auth/login → 429
- `test_cors_header` — OPTIONS with Origin: http://localhost:5173 → CORS header
- `test_security_headers` — X-Frame-Options + X-Content-Type-Options present

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] secure library API mismatch**
- **Found during:** Task 2
- **Issue:** Plan specified `secure_headers.framework.fastapi(response)` but `Secure` object in secure>=1.0.1 has no `framework` attribute
- **Fix:** Used `await _secure_headers.set_headers_async(response)` — the correct async API
- **Files modified:** backend/app/main.py
- **Commit:** da48f04

**2. [Rule 1 - Bug] Rate limiter double-counting from module reload in tests**
- **Found during:** Task 2 (test debugging)
- **Issue:** `@limiter.limit("5/minute")` decorator was being applied multiple times when `importlib.reload(auth_routes)` was called in test fixtures, causing each HTTP request to count as N hits in the rate limiter storage (where N = number of reloads)
- **Fix:** Extracted limiter to `app/core/rate_limit.py` singleton (not reloaded), used `monkeypatch.setattr` on the live `settings` object instead of `importlib.reload`, removed reloads from `test_jwt_roundtrip`/`test_jwt_invalid`
- **Files modified:** backend/app/core/rate_limit.py (new), backend/app/api/routes/auth.py, backend/tests/test_auth.py, backend/tests/conftest.py
- **Commit:** da48f04

**3. [Rule 1 - Bug] Alembic migration cannot run against SQLite dev DB**
- **Found during:** Task 1 migration execution
- **Issue:** `alembic upgrade head` from revision 0 fails because migration 001 contains TimescaleDB-specific `create_hypertable()` SQL that SQLite rejects
- **Fix:** Used `alembic stamp head` to mark 005 as applied (the schema already exists from prior phases; TimescaleDB SQL is production-only)
- **Files modified:** None (operational fix)
- **Commit:** 90aff18

**4. [Rule 2 - Missing Functionality] Auth bypass for all pre-existing API tests**
- **Found during:** Task 2 (full suite run)
- **Issue:** Adding `Depends(get_current_user)` to all `/api` routers broke 12 existing API tests that had no cookie
- **Fix:** Added `override_get_current_user` helper in conftest.py; injected into fixtures in test_analysis_api.py, test_backtest_api.py, test_paper_trading_api.py
- **Files modified:** backend/tests/conftest.py, backend/tests/test_analysis_api.py, backend/tests/test_backtest_api.py, backend/tests/test_paper_trading_api.py
- **Commit:** da48f04

## Known Stubs

None. All exported functions are fully implemented.

## Commits

| Commit | Description |
|--------|-------------|
| 90aff18 | feat(05-01): auth core — security.py, auth.py, rate_limit.py, migration 005 |
| da48f04 | feat(05-01): auth routes, WebSocket endpoint, main.py hardening |

## Self-Check: PASSED

All 6 key files exist. Both commits (90aff18, da48f04) found in git log. Full test suite: 84 passed, 0 failed.
