import { create } from 'zustand'
import { getMe } from '@/api/auth'

interface AuthState {
  isAuthenticated: boolean
  username: string | null
  isLoading: boolean
  checkAuth: () => Promise<void>
  setAuthenticated: (username: string) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  username: null,
  isLoading: true,

  checkAuth: async () => {
    set({ isLoading: true })
    try {
      const user = await getMe()
      if (user?.username) {
        set({ isAuthenticated: true, username: user.username, isLoading: false })
      } else {
        set({ isAuthenticated: false, username: null, isLoading: false })
      }
    } catch {
      set({ isAuthenticated: false, username: null, isLoading: false })
    }
  },

  setAuthenticated: (username: string) => {
    set({ isAuthenticated: true, username, isLoading: false })
  },

  clearAuth: () => {
    set({ isAuthenticated: false, username: null, isLoading: false })
  },
}))
