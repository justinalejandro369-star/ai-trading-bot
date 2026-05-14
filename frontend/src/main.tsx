import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import { router } from './router/index'
import { useAuthStore } from './store/auth'
// Theme store is imported for its side-effect: it reads localStorage and applies
// the .dark class to <html> before React renders, preventing a flash of wrong theme.
import './store/theme'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

// Kick off session restore before first render
void useAuthStore.getState().checkAuth()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
