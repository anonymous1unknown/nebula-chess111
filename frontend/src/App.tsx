import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import Layout from './components/Layout/Layout'
import LobbyPage from './components/Lobby/LobbyPage'
import GamePage from './components/Game/GamePage'
import LoginPage from './components/Auth/LoginPage'
import RegisterPage from './components/Auth/RegisterPage'
import ProfilePage from './components/Profile/ProfilePage'
import LeaderboardPage from './components/Leaderboard/LeaderboardPage'
import PuzzlePage from './components/Puzzle/PuzzlePage'
import AnalysisPage from './components/Analysis/AnalysisPage'
import SettingsPage from './components/Profile/SettingsPage'
import { useAuthStore } from './store/authStore'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const user = useAuthStore(s => s.user)
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const { loadFromStorage } = useAuthStore()

  useEffect(() => {
    loadFromStorage()
  }, [loadFromStorage])

  return (
    <Routes>
      <Route path="/login"    element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<Layout />}>
        <Route path="/"             element={<LobbyPage />} />
        <Route path="/game/:gameId" element={<GamePage />} />
        <Route path="/leaderboard"  element={<LeaderboardPage />} />
        <Route path="/puzzle"       element={<PuzzlePage />} />
        <Route path="/analysis"     element={<AnalysisPage />} />
        <Route path="/profile/:username" element={<ProfilePage />} />
        <Route path="/settings" element={
          <RequireAuth><SettingsPage /></RequireAuth>
        } />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
