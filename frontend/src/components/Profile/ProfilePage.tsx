import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Calendar, Swords, TrendingUp, TrendingDown, Minus, ChevronRight } from 'lucide-react'
import { usersApi, gamesApi } from '../../api/client'
import { User, GameHistoryItem } from '../../types'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

function StatCard({ label, value, color }: { label: string; value: number | string; color?: string }) {
  return (
    <div className="card py-4 text-center">
      <p className={clsx('text-2xl font-bold font-mono', color ?? 'text-nebula-100')}>{value}</p>
      <p className="text-xs text-nebula-400 mt-1 uppercase tracking-wide">{label}</p>
    </div>
  )
}

export default function ProfilePage() {
  const { username } = useParams<{ username: string }>()
  const [user, setUser] = useState<User | null>(null)
  const [history, setHistory] = useState<GameHistoryItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!username) return
    Promise.all([
      usersApi.getUser(username),
      gamesApi.myHistory(15, 0),
    ]).then(([u, g]) => {
      setUser(u.data)
      setHistory(g.data)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [username])

  if (loading) return (
    <div className="flex items-center justify-center py-32">
      <div className="w-8 h-8 border-2 border-nebula-400 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  if (!user) return (
    <div className="text-center py-32">
      <p className="text-nebula-400 text-lg">Player not found</p>
    </div>
  )

  const winRate = user.games_played > 0
    ? Math.round((user.games_won / user.games_played) * 100) : 0

  const resultIcon = (r: string) => {
    if (r === 'white_wins' || r === 'black_wins') return null // will use played_as
    return null
  }

  const gameOutcome = (g: GameHistoryItem) => {
    const myWin = (g.result === 'white_wins' && g.played_as === 'white') ||
      (g.result === 'black_wins' && g.played_as === 'black')
    const myLoss = (g.result === 'white_wins' && g.played_as === 'black') ||
      (g.result === 'black_wins' && g.played_as === 'white')
    if (myWin) return { label: 'Win', icon: TrendingUp, color: 'text-cosmic-green', bg: 'bg-cosmic-green/10 border-cosmic-green/30' }
    if (myLoss) return { label: 'Loss', icon: TrendingDown, color: 'text-cosmic-red', bg: 'bg-cosmic-red/10 border-cosmic-red/30' }
    return { label: 'Draw', icon: Minus, color: 'text-cosmic-gold', bg: 'bg-cosmic-gold/10 border-cosmic-gold/30' }
  }

  return (
    <div className="container mx-auto px-4 py-10 max-w-4xl">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>

        {/* Profile header */}
        <div className="card mb-6 flex items-start gap-5">
          <div className="w-20 h-20 rounded-2xl bg-nebula-500 flex items-center justify-center text-4xl font-bold shrink-0">
            {user.username[0].toUpperCase()}
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-display font-bold text-nebula-100">{user.username}</h1>
            {user.bio && <p className="text-nebula-300 text-sm mt-1">{user.bio}</p>}
            <div className="flex items-center gap-4 mt-2 text-xs text-nebula-400">
              {user.country && <span>{user.country}</span>}
              <span className="flex items-center gap-1">
                <Calendar size={12} />
                Joined {formatDistanceToNow(new Date(user.created_at), { addSuffix: true })}
              </span>
            </div>
          </div>
          <div className="text-right">
            <p className="text-3xl font-bold font-mono text-gradient">{user.elo}</p>
            <p className="text-xs text-nebula-400">ELO Rating</p>
            <p className="text-xs text-nebula-500 mt-0.5">Peak: {user.peak_elo}</p>
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <StatCard label="Games" value={user.games_played} />
          <StatCard label="Wins" value={user.games_won} color="text-cosmic-green" />
          <StatCard label="Losses" value={user.games_lost} color="text-cosmic-red" />
          <StatCard label="Win Rate" value={`${winRate}%`} color={winRate >= 50 ? 'text-cosmic-green' : 'text-nebula-200'} />
        </div>

        {/* Ratings by format */}
        <div className="card mb-6">
          <h2 className="font-semibold text-nebula-200 mb-4 flex items-center gap-2">
            <TrendingUp size={16} className="text-nebula-400" /> Ratings by Format
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              ['Bullet', user.elo_bullet, '⚡'],
              ['Blitz', user.elo_blitz, '⏱'],
              ['Rapid', user.elo_rapid, '♟'],
              ['Overall', user.elo, '♛'],
            ].map(([label, elo, icon]) => (
              <div key={String(label)} className="bg-nebula-800/50 rounded-xl p-3 text-center">
                <p className="text-xl mb-0.5">{icon}</p>
                <p className="font-bold font-mono text-lg text-nebula-100">{elo}</p>
                <p className="text-xs text-nebula-400">{label}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Game history */}
        <div className="card">
          <h2 className="font-semibold text-nebula-200 mb-4 flex items-center gap-2">
            <Swords size={16} className="text-nebula-400" /> Recent Games
          </h2>
          <div className="space-y-2">
            {history.length === 0 && (
              <p className="text-nebula-400 text-sm text-center py-6">No games played yet</p>
            )}
            {history.map((g) => {
              const out = gameOutcome(g)
              const Icon = out.icon
              return (
                <Link
                  key={g.id}
                  to={`/game/${g.id}`}
                  className={clsx(
                    'flex items-center gap-3 p-3 rounded-xl border transition-all hover:bg-nebula-800/40',
                    out.bg
                  )}
                >
                  <div className={clsx('flex items-center gap-1 font-semibold text-sm min-w-[52px]', out.color)}>
                    <Icon size={14} /> {out.label}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-nebula-200 font-medium capitalize">
                      {g.time_control} · {Math.floor(g.initial_time / 60)}+{g.increment}
                    </p>
                    <p className="text-xs text-nebula-400 capitalize">
                      {g.termination?.replace(/_/g, ' ')} · {g.move_count} moves
                    </p>
                  </div>
                  {g.elo_change != null && (
                    <span className={clsx(
                      'text-sm font-mono font-semibold shrink-0',
                      g.elo_change > 0 ? 'text-cosmic-green' : g.elo_change < 0 ? 'text-cosmic-red' : 'text-nebula-400'
                    )}>
                      {g.elo_change > 0 ? '+' : ''}{g.elo_change}
                    </span>
                  )}
                  <ChevronRight size={14} className="text-nebula-500 shrink-0" />
                </Link>
              )
            })}
          </div>
        </div>
      </motion.div>
    </div>
  )
}
