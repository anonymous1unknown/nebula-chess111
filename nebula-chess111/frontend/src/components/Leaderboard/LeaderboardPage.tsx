import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Trophy, TrendingUp, Sword } from 'lucide-react'
import { leaderboardApi } from '../../api/client'
import { LeaderboardEntry } from '../../types'

export default function LeaderboardPage() {
  const navigate = useNavigate()
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    leaderboardApi.get(50, 0)
      .then(r => setEntries(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const medalColor = (rank: number) => {
    if (rank === 1) return 'text-yellow-400'
    if (rank === 2) return 'text-gray-300'
    if (rank === 3) return 'text-amber-600'
    return 'text-nebula-400'
  }

  return (
    <div className="container mx-auto px-4 py-10 max-w-4xl">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-3 mb-8">
          <Trophy className="text-cosmic-gold" size={28} />
          <h1 className="text-3xl font-display font-bold text-gradient">Leaderboard</h1>
        </div>

        <div className="card overflow-hidden p-0">
          {/* Header */}
          <div className="grid grid-cols-[2.5rem_1fr_6rem_6rem_6rem] gap-4 px-5 py-3 text-xs uppercase tracking-widest text-nebula-400 font-semibold border-b border-nebula-700/40 bg-nebula-900/40">
            <div>#</div>
            <div>Player</div>
            <div className="text-right">ELO</div>
            <div className="text-right">Games</div>
            <div className="text-right">Win%</div>
          </div>

          {loading && (
            <div className="py-16 text-center">
              <div className="w-8 h-8 border-2 border-nebula-400 border-t-transparent rounded-full animate-spin mx-auto" />
            </div>
          )}

          {entries.map((entry, i) => (
            <motion.button
              key={entry.username}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03 }}
              onClick={() => navigate(`/profile/${entry.username}`)}
              className="w-full grid grid-cols-[2.5rem_1fr_6rem_6rem_6rem] gap-4 px-5 py-3.5 text-sm hover:bg-nebula-800/40 transition-colors border-b border-nebula-800/30 last:border-0 text-left"
            >
              <div className={`font-bold font-mono ${medalColor(entry.rank)}`}>
                {entry.rank <= 3 ? ['🥇','🥈','🥉'][entry.rank - 1] : entry.rank}
              </div>
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-full bg-nebula-700 flex items-center justify-center text-sm font-bold shrink-0">
                  {entry.username[0].toUpperCase()}
                </div>
                <div className="min-w-0">
                  <p className="font-semibold text-nebula-100 truncate">{entry.username}</p>
                  {entry.country && <p className="text-xs text-nebula-500">{entry.country}</p>}
                </div>
              </div>
              <div className="text-right font-bold font-mono text-nebula-100 flex items-center justify-end gap-1">
                {entry.rank <= 3 && <TrendingUp size={12} className="text-cosmic-green" />}
                {entry.elo}
              </div>
              <div className="text-right text-nebula-300 font-mono">{entry.games_played}</div>
              <div className={`text-right font-semibold font-mono ${
                entry.win_rate >= 60 ? 'text-cosmic-green' :
                entry.win_rate >= 45 ? 'text-nebula-200' : 'text-cosmic-red'
              }`}>
                {entry.win_rate}%
              </div>
            </motion.button>
          ))}

          {!loading && entries.length === 0 && (
            <div className="py-16 text-center">
              <Sword size={40} className="text-nebula-600 mx-auto mb-3" />
              <p className="text-nebula-400">No ranked players yet — play 5 games to appear!</p>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  )
}
