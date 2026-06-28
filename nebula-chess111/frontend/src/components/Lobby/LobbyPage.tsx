import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, Clock, Crown, Bot, Link2, Users, Trophy, Puzzle } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

import { gamesApi } from '../../api/client'
import { useAuthStore } from '../../store/authStore'

interface TimePreset { label: string; seconds: number; increment: number; icon: React.ReactNode }

const TIME_PRESETS: TimePreset[] = [
  { label: '1+0', seconds: 60,   increment: 0, icon: <Zap size={16} /> },
  { label: '2+1', seconds: 120,  increment: 1, icon: <Zap size={16} /> },
  { label: '3+0', seconds: 180,  increment: 0, icon: <Zap size={16} /> },
  { label: '3+2', seconds: 180,  increment: 2, icon: <Zap size={16} /> },
  { label: '5+0', seconds: 300,  increment: 0, icon: <Clock size={16} /> },
  { label: '5+3', seconds: 300,  increment: 3, icon: <Clock size={16} /> },
  { label: '10+0', seconds: 600, increment: 0, icon: <Clock size={16} /> },
  { label: '10+5', seconds: 600, increment: 5, icon: <Clock size={16} /> },
  { label: '15+10', seconds: 900, increment: 10, icon: <Crown size={16} /> },
  { label: '30+0', seconds: 1800, increment: 0, icon: <Crown size={16} /> },
]

const AI_LEVELS = [
  { label: 'Beginner', level: 1, description: 'Random moves, great for learning' },
  { label: 'Easy',     level: 5, description: 'Basic tactics awareness' },
  { label: 'Medium',   level: 10, description: 'Solid opening and endgame' },
  { label: 'Hard',     level: 15, description: 'Advanced positional play' },
  { label: 'Master',   level: 20, description: 'Near-perfect Stockfish strength' },
]

type Mode = 'pvp' | 'ai' | 'join'

export default function LobbyPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [mode, setMode] = useState<Mode>('pvp')
  const [selectedPreset, setSelectedPreset] = useState(6) // 10+0
  const [selectedAiLevel, setSelectedAiLevel] = useState(1) // Easy
  const [color, setColor] = useState<'white' | 'black' | 'random'>('random')
  const [inviteCode, setInviteCode] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const preset = TIME_PRESETS[selectedPreset]

  const handleCreateGame = async () => {
    if (!user) { toast.error('Log in to play'); navigate('/login'); return }
    setIsLoading(true)
    try {
      const { data } = await gamesApi.create({
        time_seconds: preset.seconds,
        increment: preset.increment,
        color: color === 'random' ? undefined : color,
        vs_ai: mode === 'ai',
        ai_difficulty: AI_LEVELS[selectedAiLevel].level,
        mode: mode === 'ai' ? 'ai' : 'casual',
      })
      navigate(`/game/${data.game_id}`)
    } catch (err: unknown) {
      toast.error('Failed to create game')
    } finally {
      setIsLoading(false)
    }
  }

  const handleJoin = async () => {
    const code = inviteCode.trim().toUpperCase()
    if (!code) return
    if (!user) { toast.error('Log in to play'); navigate('/login'); return }
    setIsLoading(true)
    try {
      const { data } = await gamesApi.join(code)
      navigate(`/game/${data.game_id}`)
    } catch {
      toast.error('Game not found or already full')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-nebula-gradient relative overflow-hidden">
      {/* Background nebula glow */}
      <div className="starfield" />
      <div className="absolute top-20 left-1/4 w-96 h-96 rounded-full opacity-10 blur-3xl"
        style={{ background: 'radial-gradient(circle, #7c63e8 0%, transparent 70%)' }} />
      <div className="absolute bottom-20 right-1/4 w-64 h-64 rounded-full opacity-8 blur-3xl"
        style={{ background: 'radial-gradient(circle, #22d3ee 0%, transparent 70%)' }} />

      <div className="relative z-10 container mx-auto px-4 py-12 max-w-5xl">

        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <h1 className="text-6xl font-display font-bold text-gradient mb-3 glow-text">
            Nebula Chess
          </h1>
          <p className="text-nebula-300 text-lg">
            Premium online chess — server-authoritative, beautifully crafted
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-6">

          {/* Main game creator */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-2 card"
          >
            {/* Mode tabs */}
            <div className="flex gap-2 mb-6">
              {([
                ['pvp', Users, 'Play Online'],
                ['ai', Bot, 'vs Computer'],
                ['join', Link2, 'Join Game'],
              ] as const).map(([m, Icon, label]) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={clsx(
                    'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all',
                    mode === m
                      ? 'bg-nebula-500 text-white shadow-nebula'
                      : 'bg-nebula-800/60 text-nebula-400 hover:bg-nebula-700/60 hover:text-nebula-200'
                  )}
                >
                  <Icon size={15} /> {label}
                </button>
              ))}
            </div>

            <AnimatePresence mode="wait">
              {mode === 'join' ? (
                <motion.div
                  key="join"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-4"
                >
                  <div>
                    <label className="text-sm text-nebula-300 font-semibold mb-2 block">
                      Enter Invite Code
                    </label>
                    <input
                      className="input text-center text-xl font-mono tracking-widest uppercase"
                      placeholder="XXXXXXXX"
                      value={inviteCode}
                      onChange={e => setInviteCode(e.target.value.toUpperCase().slice(0, 12))}
                      onKeyDown={e => e.key === 'Enter' && handleJoin()}
                    />
                  </div>
                  <button
                    onClick={handleJoin}
                    disabled={!inviteCode.trim() || isLoading}
                    className="btn-primary w-full justify-center py-3.5 text-base disabled:opacity-50"
                  >
                    {isLoading ? 'Joining…' : 'Join Game'}
                  </button>
                </motion.div>
              ) : (
                <motion.div
                  key="create"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-5"
                >
                  {/* Time control */}
                  <div>
                    <label className="text-sm text-nebula-300 font-semibold mb-3 block uppercase tracking-wide">
                      Time Control
                    </label>
                    <div className="grid grid-cols-5 gap-1.5">
                      {TIME_PRESETS.map((p, i) => (
                        <button
                          key={i}
                          onClick={() => setSelectedPreset(i)}
                          className={clsx(
                            'flex flex-col items-center py-2.5 px-1 rounded-xl text-xs font-semibold transition-all',
                            selectedPreset === i
                              ? 'bg-nebula-500 text-white shadow-nebula scale-105'
                              : 'bg-nebula-800/60 text-nebula-400 hover:bg-nebula-700/40 hover:text-nebula-200'
                          )}
                        >
                          <span className="mb-0.5 opacity-70">{p.icon}</span>
                          {p.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* AI level */}
                  {mode === 'ai' && (
                    <div>
                      <label className="text-sm text-nebula-300 font-semibold mb-3 block uppercase tracking-wide">
                        Difficulty
                      </label>
                      <div className="grid grid-cols-5 gap-1.5">
                        {AI_LEVELS.map((l, i) => (
                          <button
                            key={i}
                            onClick={() => setSelectedAiLevel(i)}
                            className={clsx(
                              'flex flex-col items-center py-2.5 px-1 rounded-xl text-xs font-semibold transition-all',
                              selectedAiLevel === i
                                ? 'bg-nebula-500 text-white shadow-nebula scale-105'
                                : 'bg-nebula-800/60 text-nebula-400 hover:bg-nebula-700/40 hover:text-nebula-200'
                            )}
                          >
                            {l.label}
                          </button>
                        ))}
                      </div>
                      <p className="text-xs text-nebula-400 mt-2">
                        {AI_LEVELS[selectedAiLevel].description}
                      </p>
                    </div>
                  )}

                  {/* Color choice */}
                  <div>
                    <label className="text-sm text-nebula-300 font-semibold mb-3 block uppercase tracking-wide">
                      Play As
                    </label>
                    <div className="flex gap-2">
                      {(['white', 'random', 'black'] as const).map(c => (
                        <button
                          key={c}
                          onClick={() => setColor(c)}
                          className={clsx(
                            'flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all capitalize',
                            color === c
                              ? 'bg-nebula-500 text-white shadow-nebula'
                              : 'bg-nebula-800/60 text-nebula-400 hover:bg-nebula-700/40'
                          )}
                        >
                          {c === 'white' ? '♔ White' : c === 'black' ? '♚ Black' : '⚄ Random'}
                        </button>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={handleCreateGame}
                    disabled={isLoading}
                    className="btn-primary w-full justify-center py-4 text-base font-bold disabled:opacity-50"
                  >
                    {isLoading ? (
                      <><div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> Starting…</>
                    ) : (
                      mode === 'ai' ? <><Bot size={18} /> Play vs Computer</> : <><Users size={18} /> Create Game</>
                    )}
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* Quick links sidebar */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="flex flex-col gap-4"
          >
            {/* Stats card if logged in */}
            {user && (
              <div className="card">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 rounded-full bg-nebula-500 flex items-center justify-center text-xl font-bold">
                    {user.username[0].toUpperCase()}
                  </div>
                  <div>
                    <p className="font-semibold text-nebula-100">{user.username}</p>
                    <p className="text-sm text-nebula-400">{user.elo} ELO</p>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  {[
                    ['W', user.games_won, 'text-cosmic-green'],
                    ['D', user.games_drawn, 'text-cosmic-gold'],
                    ['L', user.games_lost, 'text-cosmic-red'],
                  ].map(([label, val, cls]) => (
                    <div key={String(label)} className="bg-nebula-800/60 rounded-lg py-2">
                      <p className={`font-bold text-lg ${cls}`}>{val}</p>
                      <p className="text-xs text-nebula-500">{label}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Navigation cards */}
            {[
              { icon: Trophy, label: 'Leaderboard', desc: 'Top players worldwide', path: '/leaderboard', color: 'text-cosmic-gold' },
              { icon: Puzzle, label: 'Daily Puzzle', desc: 'Train your tactics', path: '/puzzle', color: 'text-cosmic-cyan' },
            ].map(({ icon: Icon, label, desc, path, color: c }) => (
              <button
                key={path}
                onClick={() => navigate(path)}
                className="card hover:border-nebula-500/40 transition-all text-left group hover:scale-[1.01]"
              >
                <div className="flex items-center gap-3">
                  <div className={`${c} p-2 rounded-lg bg-nebula-800/60`}>
                    <Icon size={20} />
                  </div>
                  <div>
                    <p className="font-semibold text-nebula-100 group-hover:text-white transition-colors">{label}</p>
                    <p className="text-xs text-nebula-400">{desc}</p>
                  </div>
                </div>
              </button>
            ))}

            {!user && (
              <div className="card text-center">
                <p className="text-nebula-300 text-sm mb-3">Sign in to track ratings and history</p>
                <div className="flex flex-col gap-2">
                  <button onClick={() => navigate('/login')} className="btn-primary w-full justify-center py-2.5 text-sm">
                    Log In
                  </button>
                  <button onClick={() => navigate('/register')} className="btn-secondary w-full justify-center py-2.5 text-sm">
                    Register
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  )
}
