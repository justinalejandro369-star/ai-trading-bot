---
phase: 05-dashboard
plan: "02"
subsystem: frontend-scaffold
tags: [react, vite, typescript, tailwind, shadcn, zustand, react-router, auth-flow]
dependency_graph:
  requires: [backend-auth]
  provides: [frontend-scaffold, auth-flow-ui, landing-page, login-page, dashboard-shell]
  affects: [all-frontend-features]
tech_stack:
  added:
    - react@18
    - vite@8
    - typescript@5
    - tailwindcss@4 (via @tailwindcss/vite)
    - shadcn/ui (base-ui Radix variant)
    - zustand@5
    - react-router-dom@7
    - "@tanstack/react-query@5"
    - lightweight-charts@5.1
    - recharts
    - "@playwright/test"
  patterns:
    - zustand-auth-store
    - react-router-v7-protected-routes
    - vite-proxy-to-fastapi
    - httponly-cookie-credentials-include
    - shadcn-ui-base-ui-variant
key_files:
  created:
    - frontend/package.json
    - frontend/vite.config.ts
    - frontend/tsconfig.app.json
    - frontend/tailwind.config.ts
    - frontend/playwright.config.ts
    - frontend/components.json
    - frontend/src/main.tsx
    - frontend/src/App.tsx
    - frontend/src/index.css
    - frontend/src/api/client.ts
    - frontend/src/api/auth.ts
    - frontend/src/store/auth.ts
    - frontend/src/router/index.tsx
    - frontend/src/router/PrivateRoute.tsx
    - frontend/src/pages/Landing.tsx
    - frontend/src/pages/Login.tsx
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/lib/utils.ts
    - frontend/src/components/ui/button.tsx
    - frontend/src/components/ui/card.tsx
    - frontend/src/components/ui/tabs.tsx
    - frontend/src/components/ui/input.tsx
    - frontend/src/components/ui/label.tsx
    - frontend/src/components/ui/badge.tsx
    - frontend/src/components/ui/table.tsx
    - frontend/src/components/ui/dialog.tsx
    - frontend/src/components/ui/separator.tsx
  modified: []
decisions:
  - shadcn/ui v4 uses @base-ui/react/button (not Radix Slot) — no asChild support; used onClick + navigate() instead of Link-wrapped Buttons
  - Vite scaffold creates embedded .git — removed frontend/.git before committing to avoid submodule
  - checkAuth() called eagerly in main.tsx before first render via useAuthStore.getState() — avoids useEffect timing issues with PrivateRoute loading state
  - tsconfig.app.json ignoreDeprecations="6.0" required for baseUrl paths alias with TypeScript 5.8
metrics:
  duration_minutes: 9
  completed_date: "2026-04-08"
  tasks_completed: 2
  files_created: 27
---

# Phase 5 Plan 02: Frontend Scaffold Summary

React 18 + Vite 5 + TypeScript + Tailwind 4 + shadcn/ui SPA with complete auth flow: Landing -> Login -> Dashboard -> Logout using JWT cookie auth via Zustand store and React Router v7 protected routes.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Vite scaffold, deps, Tailwind + shadcn/ui, Playwright | bce2a19 | 26 files (package.json, vite.config.ts, tsconfig.*, shadcn components) |
| 2 | Auth store, API client, pages, protected routes | 2626937 | 8 files (api/, store/, router/, pages/) |

## What Was Built

### Scaffold (Task 1)
- Vite 8 + React 18 + TypeScript 5 frontend at `frontend/`
- Tailwind 4 via `@tailwindcss/vite` plugin (CSS `@import "tailwindcss"` syntax)
- shadcn/ui initialized with Nova preset, slate base (base-ui Radix variant)
- 9 UI components: Button, Card, Table, Badge, Tabs, Dialog, Separator, Input, Label
- Vite proxy: `/api`, `/auth` → `http://localhost:8000`; `/ws` → `ws://localhost:8000`
- Playwright config pointing at `http://localhost:5173` with Chromium project
- `npm run build` exits 0, zero TypeScript errors

### Auth Flow (Task 2)
- `api/client.ts`: `apiFetch`, `apiGet`, `apiPost` — always `credentials: 'include'`
- `api/auth.ts`: `loginUser` (FormData for OAuth2PasswordRequestForm), `logoutUser`, `getMe`
- `store/auth.ts`: Zustand store with `isAuthenticated`, `username`, `isLoading`, `checkAuth`, `setAuthenticated`, `clearAuth`
- `router/PrivateRoute.tsx`: loading spinner while `isLoading`, redirect to `/login` if not authenticated
- `router/index.tsx`: `/` → Landing, `/login` → Login, `/dashboard` → PrivateRoute → Dashboard
- `pages/Landing.tsx`: dark hero with gradient headline + 6 feature cards using shadcn Card
- `pages/Login.tsx`: centered card form with error state and loading state during submit
- `pages/Dashboard.tsx`: top nav (logo + username + Logout) + 4-tab layout (Chart/Signals/Portfolio/Backtest) with placeholder content

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] shadcn/ui v4 does not support asChild prop**
- **Found during:** Task 2, Landing.tsx TypeScript errors
- **Issue:** New shadcn/ui v4 uses `@base-ui/react/button` instead of Radix `Slot`; `asChild` prop does not exist on this Button type
- **Fix:** Replaced `<Button asChild><Link>...</Link></Button>` with `<Button onClick={() => navigate(...)}>`; equivalent behavior
- **Files modified:** `frontend/src/pages/Landing.tsx`
- **Commit:** 2626937

**2. [Rule 3 - Blocking] Vite scaffold creates embedded .git repository**
- **Found during:** Task 1, git staging
- **Issue:** `npm create vite` initializes a git repo inside `frontend/`, making it appear as a submodule
- **Fix:** Removed `frontend/.git` with `rm -rf` then staged files normally
- **Files modified:** (no code change, git structure fix)

**3. [Rule 3 - Blocking] TypeScript 5.8 deprecates baseUrl**
- **Found during:** Task 1, `npm run build`
- **Issue:** `tsconfig.app.json` with `baseUrl` for path aliases raises TS5101 deprecation error
- **Fix:** Added `"ignoreDeprecations": "6.0"` to compilerOptions
- **Files modified:** `frontend/tsconfig.app.json`
- **Commit:** bce2a19

## Known Stubs

The following dashboard tab content is intentionally placeholder (will be replaced in Wave 3 Plans 03+):
- `frontend/src/pages/Dashboard.tsx` — Chart tab: "Candlestick Chart — Coming in Wave 3"
- `frontend/src/pages/Dashboard.tsx` — Signals tab: "Signal Feed — Coming in Wave 3"
- `frontend/src/pages/Dashboard.tsx` — Portfolio tab: "Portfolio View — Coming in Wave 3"
- `frontend/src/pages/Dashboard.tsx` — Backtest tab: "Backtest Results — Coming in Wave 3"

These are intentional scaffolding stubs per plan spec. Wave 3 plans (05-03, 05-04) will replace them.

## Self-Check: PASSED
