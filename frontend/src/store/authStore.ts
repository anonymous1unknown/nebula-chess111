import { create } from 'zustand'
import { User, AuthTokens } from '../types'

interface AuthState {
  user: User | null
  tokens: AuthTokens | null
  isLoading: boolean
  setAuth: (user: User, tokens: AuthTokens) => void
  updateUser: (partial: Partial<User>) => void
  logout: () => void
  loadFromStorage: () => void
  getAccessToken: () => string | null
}

const STORAGE_KEY = 'nebula_auth'

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  tokens: null,
  isLoading: true,

  setAuth: (user, tokens) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ user, tokens }))
    set({ user, tokens, isLoading: false })
  },

  updateUser: (partial) => {
    const { user, tokens } = get()
    if (!user) return
    const updated = { ...user, ...partial }
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ user: updated, tokens }))
    set({ user: updated })
  },

  logout: () => {
    localStorage.removeItem(STORAGE_KEY)
    set({ user: null, tokens: null })
  },

  loadFromStorage: () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const { user, tokens } = JSON.parse(raw)
        set({ user, tokens })
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY)
    } finally {
      set({ isLoading: false })
    }
  },

  getAccessToken: () => get().tokens?.access_token ?? null,
}))
