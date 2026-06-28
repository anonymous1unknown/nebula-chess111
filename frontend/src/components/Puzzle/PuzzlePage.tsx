import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Puzzle, CheckCircle, XCircle, RefreshCw, Lightbulb } from 'lucide-react'
import { Chess } from 'chess.js'
import ChessBoard from '../Board/ChessBoard'
import { puzzlesApi } from '../../api/client'
import type { Puzzle as PuzzleType } from '../../types'

type PuzzleState = 'idle' | 'playing' | 'correct' | 'wrong'

export default function PuzzlePage() {
  const [puzzle, setPuzzle] = useState<PuzzleType | null>(null)
  const [loading, setLoading] = useState(true)
  const [chess] = useState(new Chess())
  const [fen, setFen] = useState('')
  const [moveIdx, setMoveIdx] = useState(0)
  const [state, setState] = useState<PuzzleState>('idle')
  const [legalMoves, setLegalMoves] = useState<string[]>([])
  const [lastMove, setLastMove] = useState<{ from: string; to: string } | null>(null)
  const [showHint, setShowHint] = useState(false)
  const [orientation, setOrientation] = useState<'white' | 'black'>('white')

  const loadPuzzle = async () => {
    setLoading(true)
    setState('idle')
    setMoveIdx(0)
    setLastMove(null)
    setShowHint(false)
    try {
      const { data } = await puzzlesApi.daily()
      setPuzzle(data)
      chess.load(data.fen)
      setFen(chess.fen())
      // orientation = whose turn it is to move
      setOrientation(chess.turn() === 'w' ? 'white' : 'black')
      setLegalMoves(chess.moves({ verbose: true }).map(m => m.from + m.to + (m.promotion ?? '')))
      setState('playing')
    } catch {
      // fallback
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadPuzzle() }, []) // eslint-disable-line

  const handleMove = useCallback((uci: string) => {
    if (!puzzle || state !== 'playing') return

    const expected = puzzle.solution[moveIdx]
    const from = uci.slice(0, 2)
    const to = uci.slice(2, 4)

    if (uci === expected || uci.startsWith(expected)) {
      // Correct move
      const move = chess.move({ from, to, promotion: uci[4] ?? 'q' })
      if (!move) return
      setFen(chess.fen())
      setLastMove({ from, to })
      const nextIdx = moveIdx + 1

      if (nextIdx >= puzzle.solution.length) {
        setState('correct')
        return
      }

      // Play opponent's response after delay
      setTimeout(() => {
        const oppMove = puzzle.solution[nextIdx]
        const oppFrom = oppMove.slice(0, 2)
        const oppTo = oppMove.slice(2, 4)
        chess.move({ from: oppFrom, to: oppTo, promotion: oppMove[4] ?? 'q' })
        setFen(chess.fen())
        setLastMove({ from: oppFrom, to: oppTo })
        setMoveIdx(nextIdx + 1)
        setLegalMoves(chess.moves({ verbose: true }).map(m => m.from + m.to + (m.promotion ?? '')))
      }, 500)

      setMoveIdx(nextIdx)
    } else {
      // Wrong move
      setState('wrong')
      setTimeout(() => setState('playing'), 1500)
    }
  }, [puzzle, state, moveIdx, chess])

  const hintMove = puzzle?.solution[moveIdx]
  const hintFrom = hintMove?.slice(0, 2)

  return (
    <div className="container mx-auto px-4 py-10 max-w-4xl">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-3 mb-8">
          <Puzzle className="text-cosmic-cyan" size={26} />
          <h1 className="text-2xl font-display font-bold text-nebula-100">Daily Puzzle</h1>
        </div>

        <div className="flex flex-col lg:flex-row gap-6 items-start">
          {/* Board */}
          <div className="flex-shrink-0 mx-auto lg:mx-0">
            {loading ? (
              <div className="w-[480px] h-[480px] rounded-2xl shimmer-bg flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-nebula-400 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <ChessBoard
                fen={fen}
                orientation={orientation}
                onMove={handleMove}
                disabled={state !== 'playing'}
                lastMove={lastMove}
                legalMoves={state === 'playing' ? legalMoves : []}
                size={480}
              />
            )}
          </div>

          {/* Info panel */}
          <div className="flex-1 space-y-4">
            {puzzle && (
              <>
                <div className="card">
                  <h2 className="font-semibold text-nebula-100 mb-1">{puzzle.description}</h2>
                  <p className="text-sm text-nebula-400 capitalize">
                    Theme: <span className="text-nebula-300">{puzzle.theme.replace(/_/g, ' ')}</span>
                  </p>
                  <p className="text-sm text-nebula-400">
                    Rating: <span className="text-nebula-300 font-mono">{puzzle.rating}</span>
                  </p>
                  <p className="text-sm text-nebula-300 mt-3">
                    {orientation === 'white' ? '♔ White' : '♚ Black'} to move
                  </p>
                </div>

                {/* Status banner */}
                <AnimatePresence mode="wait">
                  {state === 'correct' && (
                    <motion.div
                      key="correct"
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="card border-cosmic-green/40 bg-cosmic-green/5 flex items-center gap-3"
                    >
                      <CheckCircle className="text-cosmic-green" size={24} />
                      <div>
                        <p className="font-semibold text-cosmic-green">Brilliant!</p>
                        <p className="text-sm text-nebula-300">Puzzle solved correctly</p>
                      </div>
                    </motion.div>
                  )}
                  {state === 'wrong' && (
                    <motion.div
                      key="wrong"
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="card border-cosmic-red/40 bg-cosmic-red/5 flex items-center gap-3"
                    >
                      <XCircle className="text-cosmic-red" size={24} />
                      <div>
                        <p className="font-semibold text-cosmic-red">Wrong move</p>
                        <p className="text-sm text-nebula-300">Try again!</p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <div className="flex gap-2">
                  <button
                    onClick={() => { setShowHint(true); setTimeout(() => setShowHint(false), 2000) }}
                    disabled={state !== 'playing' || showHint}
                    className="btn-secondary flex-1 justify-center py-2.5 text-sm disabled:opacity-40"
                  >
                    <Lightbulb size={15} />
                    {showHint ? `Move from ${hintFrom}` : 'Hint'}
                  </button>
                  <button onClick={loadPuzzle} className="btn-secondary flex-1 justify-center py-2.5 text-sm">
                    <RefreshCw size={15} /> New Puzzle
                  </button>
                </div>

                {state === 'correct' && (
                  <div className="card">
                    <p className="text-sm font-semibold text-nebula-200 mb-2">Solution</p>
                    <div className="flex flex-wrap gap-2">
                      {puzzle.solution.map((m, i) => (
                        <span key={i} className="px-2 py-1 bg-nebula-800 rounded text-xs font-mono text-nebula-300">
                          {m}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  )
}
