# Frontend — Developer Guide

React 19 SPA dashboard for the AI trading bot.

## Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Vite | 8+ | Build tool, HMR, dev proxy |
| React | 19+ | UI framework |
| TypeScript | 6+ | Language |
| Tailwind CSS | 4+ | Utility-first styling |
| shadcn/ui | 4+ | Pre-built components (Base UI + Tailwind) |
| TradingView Lightweight Charts | 5.1+ | Candlestick charts |
| TanStack Query | 5+ | Server state, REST data fetching |
| Zustand | 5+ | Auth + portfolio state |
| React Router | 7+ | SPA routing |
| Recharts | 3+ | Win-rate, equity curve charts |
| Playwright | 1.59+ | E2E browser tests |
| Vitest | 4+ | Unit tests |

## Running

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # production build to dist/
npm run lint     # ESLint
```

## Running Tests

```bash
# E2E tests (requires backend running at localhost:8000)
npx playwright test

# Unit tests
npx vitest run

# Unit tests with UI
npx vitest --ui
```

## Dev Proxy

`vite.config.ts` proxies `/api` and `/ws` to `http://localhost:8000`, so the frontend makes requests to the same origin and cookies work without CORS issues in dev.

## Directory Structure

```
src/
  pages/            # Top-level route components
    Landing.tsx     # Public landing page
    Login.tsx       # Auth form
    Dashboard.tsx   # Main app shell with tab navigation
  components/
    chart/          # TradingView Lightweight Charts wrappers
    signals/        # Signal table, signal card, confidence badge
    portfolio/      # Paper trading positions, equity curve
    backtest/       # Backtest result display, equity chart
    education/      # Lesson viewer
    ui/             # shadcn/ui primitives (button, card, table, etc.)
  hooks/
    useWebSocket.ts # Finnhub live tick WebSocket → TanStack Query cache
  store/            # Zustand stores (auth, portfolio)
  api/              # Typed fetch wrappers (one file per API domain)
  router/           # React Router config, PrivateRoute wrapper
  types/            # Shared TypeScript interfaces
  lib/              # Utility functions (cn(), formatters)
```

## Auth Flow

1. User submits credentials at `/login`
2. POST `/auth/login` → backend sets httpOnly `access_token` cookie
3. Zustand `useAuthStore` updates `isAuthenticated = true`
4. `PrivateRoute` wrapper in `router/` checks auth store — redirects to `/login` if false
5. All subsequent API requests send the cookie automatically (same-origin or with `credentials: 'include'`)
6. POST `/auth/logout` → backend clears cookie; Zustand resets to `isAuthenticated = false`

## TradingView Lightweight Charts v5

**Critical API change in v5:** `addCandlestickSeries` was removed.

```typescript
// CORRECT (v5)
import { createChart, CandlestickSeries } from 'lightweight-charts'
const chart = createChart(containerRef.current, options)
const series = chart.addSeries(CandlestickSeries, {})
series.setData(candles)

// WRONG (v4 API — will throw in v5)
const series = chart.addCandlestickSeries({})  // does not exist in v5
```

**Candle data direction:** Backend returns candles in DESC order (newest first). Must reverse before passing to TradingView:

```typescript
const candles = await fetchCandles(symbol, interval)
series.setData([...candles].reverse())  // TradingView requires ASC order
```

## WebSocket Hook

`src/hooks/useWebSocket.ts` connects to `ws://localhost:8000/ws/live` and receives Finnhub live ticks. Ticks are injected into the TanStack Query cache so components using `useQuery` for candle data automatically see live updates without polling.

```typescript
// Usage in a component
useWebSocket()  // starts connection, updates cache automatically
```

## TanStack Query

All REST data fetching goes through TanStack Query:

```typescript
import { useQuery } from '@tanstack/react-query'
import { fetchSignals } from '@/api/signals'

const { data, isLoading, error } = useQuery({
  queryKey: ['signals'],
  queryFn: fetchSignals,
  refetchInterval: 30_000,
})
```

Query keys match the API resource path for easy cache invalidation.

## Adding a New Page

1. Create `src/pages/MyPage.tsx` as a default export component
2. Add a route in `src/router/index.tsx`:
   ```tsx
   <Route path="/my-page" element={<PrivateRoute><MyPage /></PrivateRoute>} />
   ```
3. Add a navigation tab in `src/pages/Dashboard.tsx` (the app shell)

## Zustand Stores

```typescript
// Auth store
import { useAuthStore } from '@/store/auth'
const { isAuthenticated, user, login, logout } = useAuthStore()

// Portfolio store (paper trading state)
import { usePortfolioStore } from '@/store/portfolio'
const { cash, positions, equity } = usePortfolioStore()
```

## Styling Conventions

- Use Tailwind utility classes only — no custom CSS files except `index.css` for globals
- Use `cn()` from `@/lib/utils` to merge conditional class names:
  ```typescript
  import { cn } from '@/lib/utils'
  className={cn('base-class', isActive && 'active-class')}
  ```
- shadcn/ui components are copied into `src/components/ui/` — edit them directly if needed
