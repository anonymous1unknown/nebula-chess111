import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Eye, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi, usersApi } from '../../api/client'
import { useAuthStore } from '../../store/authStore'

function AuthLayout({ children, title, subtitle }: {
  children: React.ReactNode; title: string; subtitle: string
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-nebula-gradient p-4 relative overflow-hidden">
      <div className="starfield" />
      <div className="absolute top-1/4 left-1/3 w-96 h-96 rounded-full opacity-10 blur-3xl"
        style={{ background: 'radial-gradient(circle, #7c63e8 0%, transparent 70%)' }} />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-full max-w-md"
      >
        <div className="text-center mb-8">
          <Link to="/" className="text-3xl font-display font-bold text-gradient">
            Nebula Chess
          </Link>
          <h1 className="text-2xl font-display font-bold text-nebula-100 mt-4 mb-1">{title}</h1>
          <p className="text-nebula-400 text-sm">{subtitle}</p>
        </div>
        <div className="card shadow-board">
          {children}
        </div>
      </motion.div>
    </div>
  )
}

export function LoginPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [form, setForm] = useState({ username_or_email: '', password: '' })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data: tokens } = await authApi.login(form.username_or_email, form.password)
      const { data: user } = await usersApi.me()
      setAuth(user, tokens)
      toast.success(`Welcome back, ${user.username}!`)
      navigate('/')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Login failed'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to your account">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-sm text-nebula-300 font-medium mb-1.5 block">Username or Email</label>
          <input
            className="input"
            placeholder="knight_rider or you@example.com"
            value={form.username_or_email}
            onChange={e => setForm(f => ({ ...f, username_or_email: e.target.value }))}
            required autoFocus
          />
        </div>
        <div>
          <label className="text-sm text-nebula-300 font-medium mb-1.5 block">Password</label>
          <div className="relative">
            <input
              className="input pr-10"
              type={showPass ? 'text' : 'password'}
              placeholder="••••••••"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              required
            />
            <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-nebula-400 hover:text-nebula-200"
              onClick={() => setShowPass(s => !s)}>
              {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>
        <button type="submit" disabled={loading} className="btn-primary w-full justify-center py-3.5 disabled:opacity-50">
          {loading ? 'Signing in…' : 'Sign In'}
        </button>
        <p className="text-center text-sm text-nebula-400">
          No account?{' '}
          <Link to="/register" className="text-nebula-300 hover:text-white font-semibold transition-colors">
            Create one
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}

export function RegisterPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [form, setForm] = useState({ username: '', email: '', password: '', confirm: '' })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.password !== form.confirm) { toast.error('Passwords do not match'); return }
    if (form.password.length < 8) { toast.error('Password must be at least 8 characters'); return }
    setLoading(true)
    try {
      const { data: tokens } = await authApi.register(form.username, form.email, form.password)
      const { data: user } = await usersApi.me()
      setAuth(user, tokens)
      toast.success(`Welcome to Nebula Chess, ${user.username}!`)
      navigate('/')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Registration failed'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Create account" subtitle="Join millions of players worldwide">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-sm text-nebula-300 font-medium mb-1.5 block">Username</label>
          <input
            className="input"
            placeholder="chess_wizard"
            value={form.username}
            onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
            required minLength={3} maxLength={32} autoFocus
          />
          <p className="text-xs text-nebula-500 mt-1">3-32 chars, letters/numbers/-/_</p>
        </div>
        <div>
          <label className="text-sm text-nebula-300 font-medium mb-1.5 block">Email</label>
          <input
            className="input"
            type="email"
            placeholder="you@example.com"
            value={form.email}
            onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
            required
          />
        </div>
        <div>
          <label className="text-sm text-nebula-300 font-medium mb-1.5 block">Password</label>
          <div className="relative">
            <input
              className="input pr-10"
              type={showPass ? 'text' : 'password'}
              placeholder="At least 8 characters"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              required minLength={8}
            />
            <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-nebula-400 hover:text-nebula-200"
              onClick={() => setShowPass(s => !s)}>
              {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>
        <div>
          <label className="text-sm text-nebula-300 font-medium mb-1.5 block">Confirm Password</label>
          <input
            className="input"
            type="password"
            placeholder="••••••••"
            value={form.confirm}
            onChange={e => setForm(f => ({ ...f, confirm: e.target.value }))}
            required
          />
        </div>
        <button type="submit" disabled={loading} className="btn-primary w-full justify-center py-3.5 disabled:opacity-50">
          {loading ? 'Creating account…' : 'Create Account'}
        </button>
        <p className="text-center text-sm text-nebula-400">
          Already have an account?{' '}
          <Link to="/login" className="text-nebula-300 hover:text-white font-semibold transition-colors">
            Sign in
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}

export default LoginPage
