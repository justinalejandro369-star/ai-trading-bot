# Phase 5: Dashboard — Research

**Researched:** 2026-04-08
**Domain:** Full-stack web dashboard — React+Vite SPA, FastAPI auth, WebSocket real-time, security hardening, Playwright E2E
**Confidence:** HIGH (stack fully specified in CLAUDE.md; versions verified against npm/PyPI registries)

---

## Summary

Phase 5 introduces the entire user-facing layer: a React 18 + Vite 5 SPA consuming all backend APIs built in Phases 1–4. The phase divides into three separate concerns that must be executed in sequence: (1) the backend auth + WebSocket layer, (2) the frontend scaffold and views, (3) security hardening + Playwright E2E coverage. All backend API shapes are known from the existing codebase (market-data, signals, backtest, paper-trading routes), so the frontend has a fixed contract to implement against.

The critical discovery from library version research is that **lightweight-charts shipped v5 in 2024** — it is now the `latest` tag at `5.1.0`. The v5 API is a breaking change from v4: `addCandlestickSeries()` is gone; the unified `chart.addSeries(CandlestickSeries, options)` import pattern replaces it. Signal markers and watermarks moved to the plugin system. CLAUDE.md specifies "v4+" which technically includes v5 — use v5.1.0 (current latest).

For security, the architecture uses **JWT stored in httpOnly + Secure + SameSite=Strict cookies** (not localStorage), backed by **Argon2 password hashing via argon2-cffi + passlib** (not bcrypt), rate-limited auth endpoints via **slowapi 0.1.9**, security headers via **secure 1.0.1**, and CORS locked to the frontend origin only. For 100 concurrent users, a single uvicorn async worker handles the WebSocket load — Redis pub/sub is only needed when running multiple uvicorn worker processes.

**Primary recommendation:** Build backend auth + WebSocket endpoints first (Wave 1), then the React scaffold + views (Wave 2), then security hardening + Playwright tests (Wave 3). Never expose JWT secret in frontend; never allow wildcard CORS in production.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | Candlestick charts with RSI, MACD, BB overlays and signal markers | lightweight-charts v5 CandlestickSeries + LineSeries for overlays; markers via series.setMarkers() or Markers plugin |
| DASH-02 | Signal feed: ranked AI opportunities with confidence, entry/exit, stop-loss | GET /api/signals/top exists; TanStack Query polling or WebSocket push; shadcn/ui Table/Card |
| DASH-03 | Portfolio view: paper positions, P&L, allocation | GET /api/paper/accounts/{id} exists; allocation breakdown via Recharts PieChart |
| DASH-04 | Backtest results: equity curve + metrics table | POST /api/backtest + GET /api/paper/accounts/{id}/compare exist; Recharts LineChart for equity curve |
| DASH-05 | Real-time WebSocket updates without page refresh | FastAPI WebSocket endpoint (new); Redis pub/sub for multi-worker; queryClient.setQueryData on message |
| AUTH | Secure login / JWT httpOnly cookies | FastAPI OAuth2PasswordRequestForm + PyJWT + argon2-cffi; httpOnly Secure SameSite=Strict |
| SECURITY | OWASP Top 10, CORS, CSRF, rate limiting, input validation | slowapi + secure library + fastapi-csrf-protect + CORSMiddleware |
| LANDING | Excellent marketing/onboarding landing page | React Router v7 public route; Tailwind + shadcn/ui Hero/Feature components |
| PLAYWRIGHT | E2E test every user interaction | Playwright 1.59.1; webServer config pointing at Vite dev; page.routeWebSocket for WS mocking |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

### Locked Technology Decisions
- **Frontend:** React 18 + Vite 5 + TypeScript 5 (not Next.js, not Streamlit)
- **Charts:** TradingView Lightweight Charts (not Chart.js, not D3)
- **State:** TanStack Query 5 (server state) + Zustand 4 (client state)
- **Styling:** Tailwind CSS 3 + shadcn/ui (Radix UI based)
- **Secondary charts:** Recharts 2
- **Backend:** FastAPI (not Node.js, not Flask, not Django)
- **Data layer:** Free APIs only — yfinance, Finnhub, CoinGecko, CCXT
- **Python dep management:** uv (not pip, not Poetry)
- **Containerization:** Docker + Docker Compose

### Forbidden Patterns
- No Zipline, no yfinance for real-time polling
- No Streamlit for the dashboard
- No Node.js backend
- No RabbitMQ (Redis only)
- No Redux (Zustand only)
- No Chart.js or D3 for OHLCV
- No free forex intraday data
- No options data in MVP
- No wildcard CORS `allow_origins=["*"]` in production

### Existing Backend API Contracts (verified from source)
```
GET  /api/market-data/{symbol}?interval={}&limit={}       → OHLCV array (DESC order)
GET  /api/indicators/{symbol}                              → computed indicators
GET  /api/signals                                          → all latest signals
GET  /api/signals/top?limit={}                             → top N by confidence
POST /api/backtest                                         → BacktestResult dict
POST /api/paper/accounts                                   → create account
GET  /api/paper/accounts/{id}                             → account + positions
POST /api/paper/accounts/{id}/orders                      → place order
GET  /api/paper/accounts/{id}/equity                      → equity curve
GET  /api/paper/accounts/{id}/compare                     → paper vs backtest
```

---

## Standard Stack

### Backend — New Additions for Phase 5
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyJWT | 2.10.1 | JWT token creation and verification | Simpler than python-jose; actively maintained; already installed on system |
| argon2-cffi | 25.1.0 | Argon2id password hashing | OWASP-recommended over bcrypt; already installed on system |
| passlib | 1.7.4 | CryptContext wrapper for argon2-cffi | Clean hash/verify API; already installed on system |
| python-multipart | 0.0.6 | OAuth2 form body parsing | Required by FastAPI for OAuth2PasswordRequestForm; already installed |
| slowapi | 0.1.9 | Rate limiting decorator for FastAPI/Starlette | Limiter(key_func=get_remote_address); compatible with async FastAPI |
| secure | 1.0.1 | Security headers middleware (CSP, HSTS, X-Frame-Options) | One import adds all OWASP-required headers; presets for FastAPI |
| fastapi-csrf-protect | 1.0.7 | CSRF token generation and validation | Required for httpOnly cookie + form-based auth flows |
| redis (aioredis interface) | 7.4.0 | Async pub/sub for WebSocket broadcast across workers | Python redis client with asyncio support |

**Note:** `python-jose` is installed on the system but PyJWT is preferred for new code — simpler API, no ecdsa/pyasn1 transitive deps, same JWT RFC compliance.

### Backend — Installation
```bash
uv add pyjwt argon2-cffi passlib python-multipart slowapi secure fastapi-csrf-protect redis
```

### Frontend — Verified Versions
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | 19.2.4 | UI framework | Specified in CLAUDE.md; latest stable |
| react-dom | 19.2.4 | DOM rendering | Companion to react |
| vite | 8.0.7 | Build tool + dev server | Specified in CLAUDE.md; sub-second HMR |
| @vitejs/plugin-react | 6.0.1 | Vite React plugin (Babel transform) | Required by Vite for JSX |
| typescript | 6.0.2 | Type safety | Specified in CLAUDE.md |
| lightweight-charts | **5.1.0** | OHLCV candlestick charts | Specified in CLAUDE.md; v5 is current latest |
| @tanstack/react-query | 5.96.2 | Server state management | Specified in CLAUDE.md |
| zustand | 5.0.12 | Client state (auth, UI) | Specified in CLAUDE.md |
| tailwindcss | 4.2.2 | Utility-first styling | Specified in CLAUDE.md |
| recharts | 3.8.1 | Secondary charts (equity curve, P&L) | Specified in CLAUDE.md |
| react-router-dom | 7.14.0 | SPA routing with protected routes | Mature v7 with hook-based API |
| @playwright/test | 1.59.1 | E2E testing | Specified by phase requirements |
| vitest | 4.1.3 | Unit + component testing | Vite-native; faster than Jest for Vite projects |
| msw | 2.13.2 | API mocking for unit tests | Intercepts fetch/WebSocket in tests |

**shadcn/ui:** Installed via CLI (`npx shadcn@latest init`), not as npm dependency. Components are copied into `src/components/ui/`. No version pin needed.

### Frontend — Installation
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install lightweight-charts @tanstack/react-query zustand react-router-dom recharts
npm install -D @playwright/test vitest @vitest/ui msw
npx shadcn@latest init
npx shadcn@latest add button card table badge tabs dialog separator
```

### Alternatives Considered
| Recommended | Alternative | When Alternative Makes Sense |
|-------------|-------------|------------------------------|
| PyJWT | python-jose | When you need JWKS/RS256 multi-key rotation at scale |
| argon2-cffi + passlib | bcrypt | Never for greenfield — argon2id wins on OWASP guidance |
| slowapi | fastapi-limiter | fastapi-limiter requires Redis as dependency; slowapi works in-memory for single worker |
| secure library | Secweb | Both are valid; secure has FastAPI preset, slightly simpler API |
| react-router-dom v7 | tanstack-router | TanStack Router is excellent but adds complexity; react-router v7 is the standard |
| Vitest | Jest | Jest requires babel config with Vite; Vitest is zero-config |

---

## Architecture Patterns

### Recommended Project Structure

```
trading-bot/
├── backend/
│   └── app/
│       ├── api/
│       │   └── routes/
│       │       ├── auth.py          # POST /auth/login, POST /auth/logout, GET /auth/me (NEW)
│       │       └── websocket.py     # WS /ws/live — price + signal broadcast (NEW)
│       ├── core/
│       │   ├── auth.py              # JWT encode/decode, get_current_user dep (NEW)
│       │   └── security.py          # Argon2 hash/verify, password policy (NEW)
│       └── main.py                  # + CORSMiddleware, security headers, rate limiter
├── frontend/
│   ├── src/
│   │   ├── api/                     # All fetch functions (typed)
│   │   │   ├── client.ts            # Axios/fetch base with credentials: 'include'
│   │   │   ├── market.ts            # getCandles()
│   │   │   ├── signals.ts           # getTopSignals()
│   │   │   ├── backtest.ts          # runBacktest()
│   │   │   └── paper.ts             # getAccount(), placeOrder(), getEquity()
│   │   ├── components/
│   │   │   ├── ui/                  # shadcn/ui copied components
│   │   │   ├── chart/
│   │   │   │   ├── CandlestickChart.tsx   # lightweight-charts v5 wrapper
│   │   │   │   ├── EquityCurveChart.tsx   # Recharts LineChart
│   │   │   │   └── PnLPieChart.tsx        # Recharts PieChart
│   │   │   ├── signals/
│   │   │   │   └── SignalFeed.tsx
│   │   │   ├── portfolio/
│   │   │   │   └── PortfolioView.tsx
│   │   │   └── backtest/
│   │   │       └── BacktestResults.tsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts      # WebSocket connection + reconnect logic
│   │   │   └── useAuth.ts           # Zustand auth slice
│   │   ├── pages/
│   │   │   ├── Landing.tsx          # Public marketing page
│   │   │   ├── Login.tsx            # Auth form
│   │   │   ├── Dashboard.tsx        # Main protected view
│   │   │   ├── Signals.tsx
│   │   │   ├── Portfolio.tsx
│   │   │   └── Backtest.tsx
│   │   ├── store/
│   │   │   └── auth.ts              # Zustand auth store
│   │   ├── router/
│   │   │   ├── index.tsx            # react-router-dom createBrowserRouter
│   │   │   └── PrivateRoute.tsx     # Redirects to /login if unauthenticated
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── e2e/                         # Playwright tests
│   │   ├── auth.spec.ts
│   │   ├── dashboard.spec.ts
│   │   ├── signals.spec.ts
│   │   ├── portfolio.spec.ts
│   │   └── backtest.spec.ts
│   ├── playwright.config.ts
│   └── vite.config.ts
```

### Pattern 1: lightweight-charts v5 React Integration

**What:** The v5 unified series API replaces all named series creation methods. `addCandlestickSeries()` is gone. Import the series type class and pass it to `addSeries()`.

**Breaking change from v4:** `chart.addCandlestickSeries({...})` → `chart.addSeries(CandlestickSeries, {...})`

**When to use:** Every OHLCV chart view (Dashboard main chart).

```typescript
// Source: https://tradingview.github.io/lightweight-charts/docs/series-types
import { createChart, CandlestickSeries, LineSeries, ColorType } from 'lightweight-charts';
import { useEffect, useRef } from 'react';

export function CandlestickChart({ data, rsiData }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0f172a' },
        textColor: '#94a3b8',
      },
      width: containerRef.current.clientWidth,
      height: 400,
    });

    // v5 unified API — CandlestickSeries imported as class
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });
    candleSeries.setData(data);

    // RSI overlay on separate pane
    const rsiSeries = chart.addSeries(LineSeries, {
      color: '#f59e0b',
      lineWidth: 1,
    });
    rsiSeries.setData(rsiData);

    // Responsive resize
    const handleResize = () => {
      chart.applyOptions({ width: containerRef.current!.clientWidth });
    };
    window.addEventListener('resize', handleResize);

    // Cleanup — critical to prevent memory leaks
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, rsiData]);

  return <div ref={containerRef} />;
}
```

**Candle data shape** (verified from backend `/api/market-data/{symbol}` response):
```typescript
interface Candle {
  time: number;      // Unix timestamp (seconds) — must be ascending order
  open: number;
  high: number;
  low: number;
  close: number;
}
```

**Warning:** The backend returns candles in DESC order (most recent first). The frontend MUST reverse the array before calling `setData()`. lightweight-charts requires ascending time order.

### Pattern 2: FastAPI JWT httpOnly Cookie Auth

**What:** Login endpoint sets JWT in httpOnly Secure SameSite=Strict cookie. All subsequent requests include the cookie automatically. Frontend never reads the token value.

**When to use:** Every protected API endpoint.

```python
# Source: FastAPI official security docs + hardened cookie pattern
from fastapi import APIRouter, Response, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import jwt
from passlib.context import CryptContext

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_ctx = CryptContext(schemes=["argon2"], deprecated="auto")
SECRET_KEY = settings.jwt_secret  # from environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> dict:
    user = await authenticate_user(form_data.username, form_data.password, session)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = jwt.encode(
        {"sub": str(user.id), "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,         # HTTPS only in production
        samesite="strict",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"status": "ok"}

@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie("access_token")
    return {"status": "ok"}
```

### Pattern 3: FastAPI WebSocket with ConnectionManager

**What:** Single connection manager tracks all WebSocket clients per process. For single-uvicorn-worker deployments (sufficient for 100 users), in-process broadcast works. Redis pub/sub is additive for multi-worker scale.

**When to use:** `/ws/live` endpoint for real-time price + signal push.

```python
# Source: FastAPI WebSocket docs + production scaling patterns
from fastapi import WebSocket, WebSocketDisconnect
from typing import set

class ConnectionManager:
    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, data: dict):
        import json
        payload = json.dumps(data)
        dead = set()
        for ws in self.active:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        self.active -= dead

manager = ConnectionManager()

@router.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive / client ping
    except WebSocketDisconnect:
        manager.disconnect(ws)
```

**Frontend WebSocket hook:**
```typescript
// hooks/useWebSocket.ts
import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export function useWebSocket(url: string) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'signal_update') {
          // Inject into TanStack Query cache — triggers re-render without refetch
          queryClient.setQueryData(['signals', 'top'], (old: Signal[]) =>
            [msg.signal, ...(old ?? [])].slice(0, 10)
          );
        }
        if (msg.type === 'price_tick') {
          queryClient.setQueryData(['candles', msg.symbol], (old: Candle[]) =>
            old ? [...old.slice(-199), msg.candle] : [msg.candle]
          );
        }
      };

      ws.onclose = () => {
        // Reconnect after 3s on unexpected close
        setTimeout(connect, 3000);
      };
    };
    connect();
    return () => wsRef.current?.close();
  }, [url, queryClient]);
}
```

### Pattern 4: TanStack Query v5 for REST Data

**What:** All REST endpoints consumed via `useQuery` / `useMutation`. WebSocket updates bypass the fetch cycle via `queryClient.setQueryData`.

```typescript
// Signals feed — polls every 30s, WebSocket updates override
const { data: signals } = useQuery({
  queryKey: ['signals', 'top'],
  queryFn: () => fetch('/api/signals/top?limit=10').then(r => r.json()),
  staleTime: 30_000,
  refetchInterval: 60_000,   // fallback polling if WS disconnects
});
```

### Pattern 5: Protected Route with React Router v7

**What:** `PrivateRoute` component reads Zustand auth state; unauthenticated users redirect to `/login` with `location` preserved for post-login redirect.

```typescript
// router/PrivateRoute.tsx
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';

export function PrivateRoute() {
  const { isAuthenticated, isLoading } = useAuthStore();
  const location = useLocation();

  if (isLoading) return <div>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  return <Outlet />;
}
```

### Pattern 6: CORS + Security Headers in FastAPI

```python
# main.py additions
from fastapi.middleware.cors import CORSMiddleware
import secure

# CORS — locked to frontend origin, credentials required for cookies
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],  # e.g. "http://localhost:5173"
    allow_credentials=True,                  # required for httpOnly cookies
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

# Security headers — single middleware
secure_headers = secure.Secure.with_default_headers()

@app.middleware("http")
async def set_secure_headers(request, call_next):
    response = await call_next(request)
    secure_headers.framework.fastapi(response)
    return response
```

### Anti-Patterns to Avoid

- **Storing JWT in localStorage:** Exposes token to XSS; use httpOnly cookie only
- **`allow_origins=["*"]` with `allow_credentials=True`:** Browsers reject this combination; CORS spec prohibits it
- **Calling `chart.addCandlestickSeries()` (v4 API):** Removed in v5; use `chart.addSeries(CandlestickSeries, {})`
- **Passing DESC-ordered candles to lightweight-charts:** Library silently renders wrong chart; must sort ASC first
- **Using `queryClient.invalidateQueries` for WebSocket updates:** Triggers a network refetch; use `setQueryData` instead for real-time injection
- **Single Zustand store for everything:** Split auth, UI state, and data concerns into separate slices
- **Re-creating chart on every render:** Chart init must be inside `useEffect` with stable deps; not in component body

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom bcrypt wrapper | argon2-cffi + passlib CryptContext | Argon2id is OWASP winner; passlib handles salt, rehash-on-upgrade automatically |
| JWT creation/verification | Raw base64 encode | PyJWT | Handles exp claims, algorithm enforcement, signature verification edge cases |
| Rate limiting | Redis counter + decorator | slowapi | Handles sliding window, per-IP, per-user keying; integrates with FastAPI error handlers |
| Security headers | Manual `response.headers["X-Frame-Options"]` | secure library | Misconfigurations (wrong CSP values, missing nonce) are subtle bugs; secure gives correct defaults |
| CSRF protection | Custom double-submit cookie | fastapi-csrf-protect | CSRF is stateful and has many edge cases; the library handles token rotation correctly |
| OHLCV charting | Custom D3 candlesticks | lightweight-charts v5 | 35KB bundle, hardware-accelerated Canvas, tested against 100k+ bars — D3 candlesticks are thousands of lines of custom code |
| WebSocket reconnect | setTimeout loop with global state | useWebSocket hook with exponential backoff | Reconnect logic has state edge cases (multiple connections, cleanup on unmount) |
| Form validation | Manual input checks | Pydantic v2 models (backend) + native HTML5 + TypeScript (frontend) | Pydantic validates and coerces; HTML5 required/pattern covers 90% of UX without JS overhead |

**Key insight:** The security layer (auth, headers, CSRF, rate limiting) has the most subtle bugs if hand-rolled. Use the libraries; they encode years of attack research.

---

## Common Pitfalls

### Pitfall 1: lightweight-charts v5 Breaking API
**What goes wrong:** Code using `chart.addCandlestickSeries()` throws "addCandlestickSeries is not a function" at runtime.
**Why it happens:** v5 dropped all named series creation methods in favor of the unified `addSeries(SeriesClass, options)` API. The npm `latest` tag resolves to v5.1.0.
**How to avoid:** Pin `"lightweight-charts": "^5.1.0"` in package.json. Import `CandlestickSeries` from the package. Use `chart.addSeries(CandlestickSeries, {...})`.
**Warning signs:** TypeScript will catch it at compile time if using the library's types — `chart.addCandlestickSeries` will show as undefined.

### Pitfall 2: Candle Data Ordering
**What goes wrong:** Chart renders inverted or scrambled candlesticks.
**Why it happens:** The backend `GET /api/market-data/{symbol}` returns rows **DESC** (most recent first). lightweight-charts `setData()` requires **ascending** (oldest first) time order and will throw or silently corrupt if given unsorted data.
**How to avoid:** In the API client function, always `.reverse()` the array before returning it to components.
**Warning signs:** Chart renders but candles appear out of sequence or time axis is backwards.

### Pitfall 3: CORS + Credentials Cookie Rejection
**What goes wrong:** Browser silently drops the auth cookie; every API call returns 401.
**Why it happens:** When `allow_credentials=True` in CORSMiddleware, `allow_origins` must list the exact origin (protocol + host + port). Wildcard `*` is rejected by the browser CORS spec.
**How to avoid:** Set `FRONTEND_URL` as an environment variable (e.g., `http://localhost:5173`). Use `allow_origins=[settings.frontend_url]`. On the frontend, always pass `credentials: 'include'` in fetch options.
**Warning signs:** Browser Network tab shows `Access-Control-Allow-Origin: *` with cookies present — cookie will be ignored.

### Pitfall 4: WebSocket Auth — JWT Cookie Not Sent Automatically
**What goes wrong:** WebSocket connections arrive at the server unauthenticated even though the user has a valid cookie.
**Why it happens:** The browser's WebSocket API (`new WebSocket(url)`) does send cookies automatically to the same origin, but cookies with `SameSite=Strict` are **not** sent to cross-origin WebSocket connections. In development, the WS URL (`ws://localhost:8000`) is a different origin from the Vite frontend (`http://localhost:5173`).
**How to avoid:** For development, set `SameSite=Lax` (not Strict) for the cookie. For production (same domain), Strict works fine. Alternatively, validate via a short-lived WS handshake token passed as a query param (never in the URL for production secrets).
**Warning signs:** `/ws/live` endpoint receives connections with no cookies; `get_current_user` raises 401.

### Pitfall 5: Multiple Chart Instances on React Re-render
**What goes wrong:** Multiple overlapping chart canvases appear in the container div; memory usage grows.
**Why it happens:** `createChart()` called without proper cleanup. If the `useEffect` dependency array includes data (changes on every poll), chart is recreated on every data update.
**How to avoid:** Create the chart once in `useEffect` with `[]` empty deps. Update data using `series.update(newCandle)` or `series.setData(newData)` inside a separate effect that tracks only data changes.
**Warning signs:** Multiple canvas elements inside the chart container in browser DevTools.

### Pitfall 6: slowapi With Async FastAPI
**What goes wrong:** Rate limit decorator causes "no running event loop" error or silently fails.
**Why it happens:** slowapi requires its limiter to be set on the FastAPI app exception handlers AND the Starlette state. Missing either registration step.
**How to avoid:** Follow the full setup: `limiter = Limiter(key_func=get_remote_address)`, `app.state.limiter = limiter`, `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)`.
**Warning signs:** Rate limits never trigger (under-registration) or 500 errors instead of 429 (handler missing).

### Pitfall 7: Playwright WebSocket Testing — Cross-Browser Extraheaders Bug
**What goes wrong:** WebSocket connection drops or fails in Playwright tests using Chromium with `extraHTTPHeaders` for auth.
**Why it happens:** `extraHTTPHeaders` does not work with WebSocket connections in Chromium (confirmed Playwright issue). Firefox does not have this limitation.
**How to avoid:** For WebSocket testing, use `page.routeWebSocket()` to mock WS connections rather than testing live WS with auth headers. Alternatively, test WS via Firefox browser in Playwright config.
**Warning signs:** WS-dependent tests pass in Firefox but fail in Chromium with connection refused or auth errors.

---

## Code Examples

### Verified: v5 Series Data Update (for real-time streaming)
```typescript
// Source: https://tradingview.github.io/lightweight-charts/docs/series-types
// After initial setData(), use update() for real-time single-candle updates
candleSeries.update({
  time: 1642427876,
  open: 10.0,
  high: 10.63,
  low: 9.49,
  close: 9.55,
});
```

### Verified: Playwright WebSocket Route Mock
```typescript
// Source: https://playwright.dev/docs/api/class-websocketroute
test('signal feed updates in real-time', async ({ page }) => {
  await page.routeWebSocket('/ws/live', async (ws) => {
    // Send mock signal update immediately on connection
    ws.onopen = () => {
      ws.send(JSON.stringify({
        type: 'signal_update',
        signal: { symbol: 'AAPL', direction: 'BUY', confidence: 85 }
      }));
    };
  });

  await page.goto('/dashboard');
  await expect(page.getByTestId('signal-aapl')).toBeVisible();
});
```

### Verified: Playwright webServer Config for Vite
```typescript
// playwright.config.ts
// Source: https://playwright.dev/docs/test-webserver
import { defineConfig } from '@playwright/test';

export default defineConfig({
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
  use: {
    baseURL: 'http://localhost:5173',
  },
  testDir: './e2e',
});
```

### Verified: shadcn/ui Installation for Vite (2025 flow)
```bash
# Source: https://ui.shadcn.com/docs/installation/vite
npx shadcn@latest init  # interactive wizard — choose "New York" style, slate color
npx shadcn@latest add table card badge tabs dialog button separator
```

**Important:** The 2025 shadcn CLI command is `npx shadcn@latest` (not `shadcn-ui@latest` — that package name is deprecated).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `chart.addCandlestickSeries()` | `chart.addSeries(CandlestickSeries, {})` | v5.0.0 (2024) | All v4 chart code must be rewritten |
| `npx shadcn-ui@latest add` | `npx shadcn@latest add` | 2024 rename | Old command still works but deprecated |
| Passlib as primary hash lib | passlib + argon2-cffi (or pwdlib 0.3.0) | 2024 (FastAPI Users v13) | bcrypt deprecated; argon2 is the standard |
| python-jose for JWT | PyJWT | Ongoing preference shift | python-jose has dead dependencies (ecdsa); PyJWT is simpler |
| Gunicorn + uvicorn workers | `uvicorn --workers N` directly | uvicorn 0.20+ | Uvicorn now manages worker processes natively |
| localStorage for JWT | httpOnly cookie | Ongoing (security practice) | XSS cannot steal httpOnly cookies |
| React Router v6 | React Router v7 | Late 2024 | Hook-based routing; `createBrowserRouter` is the standard |

**Deprecated/outdated:**
- `shadcn-ui` npm package name: replaced by `shadcn` (same library, new name)
- `python-jose` for new projects: use PyJWT (python-jose's ecdsa dep is unmaintained)
- `chart.addAreaSeries()`, `chart.addLineSeries()` as named methods: all replaced by unified `addSeries(SeriesClass)` in v5

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Node.js | Frontend build, Playwright | ✓ | v25.4.0 | — |
| npm | Frontend package management | ✓ | 11.7.0 | — |
| Docker | Container orchestration | ✓ | 27.5.1 | — |
| Python 3.11+ | Backend runtime | ✗ | 3.10.12 (pyenv) | uv manages venv Python; project specifies >=3.11 |
| PyJWT | JWT auth | ✓ (system) | 2.10.1 | — |
| argon2-cffi | Password hashing | ✓ (system) | 25.1.0 | — |
| passlib | CryptContext | ✓ (system) | 1.7.4 | — |
| slowapi | Rate limiting | ✗ (not installed) | 0.1.9 on PyPI | — |
| secure | Security headers | ✗ (not installed) | 1.0.1 on PyPI | — |
| Redis | WebSocket pub/sub (multi-worker) | ✗ | — | Single worker: in-process ConnectionManager (sufficient for 100 users) |

**Missing dependencies with no fallback:**
- `slowapi`, `secure`, `fastapi-csrf-protect`, `redis` — must be added to `pyproject.toml` via `uv add`

**Missing dependencies with fallback:**
- Redis: not required for single-worker deployment. For 100 concurrent users, single uvicorn worker with async handles ~10K WebSocket connections; Redis is only needed when scaling to multiple workers.
- Python 3.10.12: The backend `pyproject.toml` specifies `>=3.11`. The uv lockfile creates a project-level venv; system Python version doesn't matter as long as uv can download 3.11+.

---

## Validation Architecture

### Test Framework — Backend (pytest, existing)
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | `backend/pyproject.toml` `[tool.pytest]` section |
| Quick run | `cd backend && uv run pytest tests/ -x -q` |
| Full suite | `cd backend && uv run pytest tests/ -v` |

### Test Framework — Frontend (Vitest + Playwright, new)
| Property | Value |
|----------|-------|
| Unit/component framework | Vitest 4.1.3 |
| E2E framework | Playwright 1.59.1 |
| Config file | `frontend/vite.config.ts` (Vitest) + `frontend/playwright.config.ts` (E2E) |
| Quick unit run | `cd frontend && npm run test` |
| E2E run | `cd frontend && npx playwright test` |
| Full suite | backend pytest + frontend vitest + playwright |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | Candlestick chart renders with correct symbol | Playwright (visual) | `npx playwright test e2e/dashboard.spec.ts` | ❌ Wave 0 |
| DASH-01 | Chart series created with v5 API, no console errors | Playwright | `npx playwright test e2e/dashboard.spec.ts` | ❌ Wave 0 |
| DASH-02 | Signal feed shows top signals ranked by confidence | Playwright | `npx playwright test e2e/signals.spec.ts` | ❌ Wave 0 |
| DASH-02 | Signal card shows direction, confidence, entry, stop-loss | Playwright | `npx playwright test e2e/signals.spec.ts` | ❌ Wave 0 |
| DASH-03 | Portfolio view renders positions and P&L | Playwright | `npx playwright test e2e/portfolio.spec.ts` | ❌ Wave 0 |
| DASH-03 | Allocation pie chart renders | Playwright | `npx playwright test e2e/portfolio.spec.ts` | ❌ Wave 0 |
| DASH-04 | Backtest results page renders equity curve | Playwright | `npx playwright test e2e/backtest.spec.ts` | ❌ Wave 0 |
| DASH-05 | WebSocket message updates signal feed without refresh | Playwright (routeWebSocket mock) | `npx playwright test e2e/dashboard.spec.ts` | ❌ Wave 0 |
| AUTH | Login form accepts credentials, sets cookie | Playwright | `npx playwright test e2e/auth.spec.ts` | ❌ Wave 0 |
| AUTH | Invalid credentials shows error message | Playwright | `npx playwright test e2e/auth.spec.ts` | ❌ Wave 0 |
| AUTH | Logout clears session, redirects to /login | Playwright | `npx playwright test e2e/auth.spec.ts` | ❌ Wave 0 |
| AUTH | Unauthenticated access to /dashboard redirects to /login | Playwright | `npx playwright test e2e/auth.spec.ts` | ❌ Wave 0 |
| SECURITY | Rate limit returns 429 after 5 login attempts | Backend pytest | `cd backend && uv run pytest tests/test_auth.py -x` | ❌ Wave 0 |
| SECURITY | CORS rejects request from unlisted origin | Backend pytest | `cd backend && uv run pytest tests/test_auth.py` | ❌ Wave 0 |
| SECURITY | Security headers present in all responses | Backend pytest | `cd backend && uv run pytest tests/test_auth.py` | ❌ Wave 0 |
| LANDING | Landing page hero section renders | Playwright | `npx playwright test e2e/landing.spec.ts` | ❌ Wave 0 |
| LANDING | CTA button navigates to /login | Playwright | `npx playwright test e2e/landing.spec.ts` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit (backend):** `cd backend && uv run pytest tests/test_auth.py -x -q`
- **Per task commit (frontend):** `cd frontend && npm run test -- --run`
- **Per wave merge:** Full backend pytest + `npx playwright test`
- **Phase gate:** All suites green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_auth.py` — covers AUTH + SECURITY backend requirements
- [ ] `frontend/e2e/auth.spec.ts` — covers full auth flow Playwright
- [ ] `frontend/e2e/dashboard.spec.ts` — covers DASH-01, DASH-05
- [ ] `frontend/e2e/signals.spec.ts` — covers DASH-02
- [ ] `frontend/e2e/portfolio.spec.ts` — covers DASH-03
- [ ] `frontend/e2e/backtest.spec.ts` — covers DASH-04
- [ ] `frontend/e2e/landing.spec.ts` — covers LANDING
- [ ] `frontend/playwright.config.ts` — webServer + baseURL config
- [ ] `frontend/vite.config.ts` — Vitest configuration block
- [ ] Vitest install: `npm install -D vitest @vitest/ui`
- [ ] Playwright install: `npm install -D @playwright/test && npx playwright install`

---

## Open Questions

1. **User model and registration flow**
   - What we know: No User table exists in the current schema (Phases 1–4 are single-user, unauthenticated)
   - What's unclear: Does Phase 5 need a full registration flow (name/email/password) or just a single hardcoded dev user from environment variables?
   - Recommendation: For MVP with a single operator, use env-var credentials (`ADMIN_USERNAME`, `ADMIN_PASSWORD`) seeded at startup. Full registration is v2. This avoids building a User ORM model and email verification in Phase 5.

2. **Backtest Phase 3 completion status**
   - What we know: ROADMAP shows Phase 3 plan 03-02-PLAN.md as "not started" (POST /api/backtest route). However, the backtest route IS implemented in `backend/app/api/routes/backtest.py` (verified from source). STATE.md says "Completed 04-paper-trading-simulator/04-02-PLAN.md".
   - What's unclear: Is `POST /api/backtest` actually working and tested? The source exists but the plan is marked incomplete.
   - Recommendation: Dashboard Wave 1 should smoke-test `/api/backtest` with a curl/pytest call before building the frontend backtest page against it.

3. **Finnhub WebSocket → backend WebSocket bridge**
   - What we know: Finnhub provides live stock price ticks via WebSocket (Phase 1). The `/ws/live` endpoint needs to re-broadcast these to dashboard clients.
   - What's unclear: How should the backend bridge the Finnhub incoming WS connection to the outgoing dashboard WS? The Finnhub WebSocketApp runs in a thread (websocket-client); the dashboard WS runs in asyncio.
   - Recommendation: Use asyncio Queue as the bridge. The Finnhub callback puts ticks into `asyncio.Queue`; the `ConnectionManager.broadcast()` coroutine reads from it in a background task started in the lifespan.

4. **SameSite=Strict vs Lax during local development**
   - What we know: `SameSite=Strict` prevents cookie sending to cross-origin WebSocket in Chrome during dev (localhost:5173 → localhost:8000).
   - What's unclear: Whether to use Strict or Lax depends on whether WS will be same-origin in production (behind nginx, same domain).
   - Recommendation: Use `SameSite=Lax` in development (set via `ENVIRONMENT=dev` env var), `SameSite=Strict` in production. Pass cookie via response from a `/ws/token` endpoint that issues a short-lived WS token as a URL param during development only.

---

## Sources

### Primary (HIGH confidence)
- `backend/app/api/routes/` (read directly) — all existing API shapes and response formats
- `backend/pyproject.toml` (read directly) — exact installed versions
- npm registry (`npm view <pkg> version`) — verified frontend library versions
- PyPI (`pip3 index versions <pkg>`) — verified Python library versions
- https://tradingview.github.io/lightweight-charts/docs/series-types — v5 `addSeries(CandlestickSeries)` API (fetched directly)
- https://tradingview.github.io/lightweight-charts/tutorials/react/simple — React integration pattern (fetched)
- https://tradingview.github.io/lightweight-charts/tutorials/react/advanced — multi-series + resize pattern (fetched)
- https://playwright.dev/docs/test-webserver — webServer config pattern (referenced from WebSearch)
- https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ — FastAPI JWT tutorial

### Secondary (MEDIUM confidence)
- WebSearch results for: slowapi integration, secure library headers, CORSMiddleware credentials, WebSocket connection manager pattern, Playwright WebSocket route mocking — all cross-verified with official library documentation links in search results
- https://tradingview.github.io/lightweight-charts/docs/release-notes — v5 breaking changes summary (fetched)

### Tertiary (LOW confidence — flag for validation)
- Playwright WebSocket + Chromium extraHTTPHeaders bug: reported in community forum, not in official Playwright docs. Validate during Wave 3 test implementation.
- 100 concurrent users handled by single uvicorn async worker: based on FastAPI documentation general guidance (10K connections per async worker). Not load-tested against this specific application.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against npm registry and PyPI; no training-data-only assertions
- Architecture: HIGH — backend API contracts read directly from source; frontend patterns verified from official docs
- Pitfalls: MEDIUM-HIGH — v5 breaking change confirmed via official release notes; cookie/CORS pitfalls confirmed via FastAPI official docs; WS/Chromium bug is MEDIUM (community reports only)
- Security: HIGH — OWASP guidance + FastAPI official security tutorial; argon2-cffi/passlib versions confirmed installed

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (30 days — stack is stable; lightweight-charts v5 API and Playwright APIs are mature)
