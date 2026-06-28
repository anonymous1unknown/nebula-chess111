import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const api = axios.create({
  baseURL: '/api',
  timeout: 10_000,
})

// ── Request interceptor: מצרף טוקן לכל בקשה ────────────────────────────────
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().getAccessToken()
  if (token) {
    // שימוש ב-.set() במקום השמה ישירה — מונע התעלמות מה-Header
    // ב-Axios v1+ השמה ישירה עלולה להיבלע אם config.headers הוא AxiosHeaders instance
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})

// ── Response interceptor: רענון אוטומטי על 401 ───────────────────────────────
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      const { tokens, setAuth, setTokens, logout, user } = useAuthStore.getState()
      if (!tokens?.refresh_token) {
        logout()
        return Promise.reject(err)
      }
      try {
        const { data } = await axios.post('/api/auth/refresh', {
          refresh_token: tokens.refresh_token,
        })
        // שמור טוקנים חדשים לפני שניסיון ה-retry נשלח
        if (user) {
          setAuth(user, data)
        } else {
          setTokens(data)
        }
        original.headers.set('Authorization', `Bearer ${data.access_token}`)
        return api(original)
      } catch {
        logout()
      }
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (username: string, email: string, password: string) =>
    api.post('/auth/register', { username, email, password }),
  login: (username_or_email: string, password: string) =>
    api.post('/auth/login', { username_or_email, password }),
  logout: (refresh_token: string) =>
    api.post('/auth/logout', { refresh_token }),
}

// ── Users ─────────────────────────────────────────────────────────────────────
export const usersApi = {
  me: () => api.get('/users/me'),
  getUser: (username: string) => api.get(`/users/${username}`),
  updateMe: (data: Record<string, unknown>) => api.patch('/users/me', data),
}

// ── Games ─────────────────────────────────────────────────────────────────────
export const gamesApi = {
  create: (opts: {
    mode?: string
    time_seconds?: number
    increment?: number
    color?: string
    vs_ai?: boolean
    ai_difficulty?: number
    fen?: string
  }) => api.post('/games/create', opts),

  join: (invite_code: string) => api.post(`/games/join/${invite_code}`),
  getState: (gameId: string) => api.get(`/games/${gameId}/state`),
  getLegalMoves: (gameId: string) => api.get(`/games/${gameId}/legal-moves`),
  getMoves: (gameId: string) => api.get(`/games/${gameId}/moves`),
  myHistory: (limit = 20, offset = 0) =>
    api.get(`/games/history/me?limit=${limit}&offset=${offset}`),
}

// ── Leaderboard ───────────────────────────────────────────────────────────────
export const leaderboardApi = {
  get: (limit = 50, offset = 0) =>
    api.get(`/leaderboard/?limit=${limit}&offset=${offset}`),
}

// ── Puzzles ───────────────────────────────────────────────────────────────────
export const puzzlesApi = {
  daily: () => api.get('/puzzles/daily'),
  list: (limit = 10) => api.get(`/puzzles/?limit=${limit}`),
}

export default api
