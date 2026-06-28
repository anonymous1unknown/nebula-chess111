import { useState } from 'react'
import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Trophy, Puzzle, User, Settings, LogOut, Menu, X, ChevronDown } from 'lucide-react'
import clsx from 'clsx'
import { useAuthStore } from '../../store/authStore'
import { authApi } from '../../api/client'
import toast from 'react-hot-toast'

const NAV_LINKS = [
  { label: 'Leaderboard', path: '/leaderboard', icon: Trophy },
  { label: 'Puzzles', path: '/puzzle', icon: Puzzle },
]

function Navbar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, tokens, logout } = useAuthStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  const handleLogout = async () => {
    try {
      if (tokens?.refresh_token) await authApi.logout(tokens.refresh_token)
    } catch { /* ignore */ }
    logout()
    toast.success('Signed out')
    navigate('/')
    setUserMenuOpen(false)
  }

  return (
    <nav className="glass-strong sticky top-0 z-40 border-b border-nebula-700/30">
      <div className="container mx-auto px-4 h-14 flex items-center justify-between max-w-7xl">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 font-display font-bold text-lg text-gradient hover:opacity-80 transition-opacity">
          <span className="text-2xl">♟</span>
          Nebula Chess
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(({ label, path, icon: Icon }) => (
            <Link
              key={path}
              to={path}
              className={clsx(
                'flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                location.pathname === path
                  ? 'bg-nebula-700/60 text-nebula-100'
                  : 'text-nebula-400 hover:text-nebula-200 hover:bg-nebula-800/40'
              )}
            >
              <Icon size={15} /> {label}
            </Link>
          ))}
        </div>

        {/* User section */}
        <div className="flex items-center gap-2">
          {user ? (
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(o => !o)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-nebula-800/50 hover:bg-nebula-700/60 border border-nebula-600/30 transition-all"
              >
                <div className="w-7 h-7 rounded-full bg-nebula-500 flex items-center justify-center text-sm font-bold text-white">
                  {user.username[0].toUpperCase()}
                </div>
                <span className="text-sm font-medium text-nebula-200 hidden sm:block">{user.username}</span>
                <span className="text-xs text-nebula-400 font-mono hidden sm:block">{user.elo}</span>
                <ChevronDown size={14} className={clsx('text-nebula-400 transition-transform', userMenuOpen && 'rotate-180')} />
              </button>

              <AnimatePresence>
                {userMenuOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -8, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -8, scale: 0.96 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 mt-2 w-48 glass-strong rounded-xl shadow-card border border-nebula-600/30 overflow-hidden"
                    onMouseLeave={() => setUserMenuOpen(false)}
                  >
                    {[
                      { label: 'Profile', icon: User, action: () => { navigate(`/profile/${user.username}`); setUserMenuOpen(false) } },
                      { label: 'Settings', icon: Settings, action: () => { navigate('/settings'); setUserMenuOpen(false) } },
                    ].map(({ label, icon: Icon, action }) => (
                      <button key={label} onClick={action}
                        className="w-full flex items-center gap-3 px-4 py-3 text-sm text-nebula-200 hover:bg-nebula-700/50 transition-colors">
                        <Icon size={15} className="text-nebula-400" /> {label}
                      </button>
                    ))}
                    <div className="border-t border-nebula-700/40" />
                    <button onClick={handleLogout}
                      className="w-full flex items-center gap-3 px-4 py-3 text-sm text-cosmic-red/80 hover:text-cosmic-red hover:bg-cosmic-red/10 transition-colors">
                      <LogOut size={15} /> Sign Out
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login" className="btn-secondary py-1.5 px-4 text-sm">Sign In</Link>
              <Link to="/register" className="btn-primary py-1.5 px-4 text-sm">Register</Link>
            </div>
          )}

          {/* Mobile menu */}
          <button
            className="md:hidden p-2 rounded-lg text-nebula-400 hover:text-nebula-200 hover:bg-nebula-800/40"
            onClick={() => setMenuOpen(o => !o)}
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile nav */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="md:hidden border-t border-nebula-700/30 overflow-hidden"
          >
            <div className="px-4 py-3 space-y-1">
              {NAV_LINKS.map(({ label, path, icon: Icon }) => (
                <Link
                  key={path}
                  to={path}
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-nebula-300 hover:text-white hover:bg-nebula-700/40 transition-all"
                >
                  <Icon size={16} /> {label}
                </Link>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  )
}

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-nebula-950">
      <Navbar />
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  )
}
