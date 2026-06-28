import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { BarChart2, ChevronLeft, ChevronRight, SkipBack, SkipForward, Upload } from 'lucide-react'
import { Chess } from 'chess.js'
import ChessBoard from '../Board/ChessBoard'
import MoveList from '../Game/MoveList'
import EvalBar from '../Board/EvalBar'
import clsx from 'clsx'

const STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

function parsePgn(pgn: string): string[] {
  // Strip headers and comments, extract SAN moves
  const stripped = pgn.replace(/\[.*?\]/g, '').replace(/\{.*?\}/g, '').trim()
  const tokens = stripped.split(/\s+/)
  const moves: string[] = []
  for (const t of tokens) {
    if (!t || /^\d+\./.test(t) || ['1-0','0-1','1/2-1/2','*'].includes(t)) continue
    moves.push(t)
  }
  return moves
}

function buildPositions(moves: string[]): { fen: string; san: string }[] {
  const game = new Chess()
  const positions: { fen: string; san: string }[] = [{ fen: game.fen(), san: '' }]
  for (const san of moves) {
    try {
      game.move(san)
      positions.push({ fen: game.fen(), san })
    } catch { break }
  }
  return positions
}

export default function AnalysisPage() {
  const [pgn, setPgn] = useState('')
  const [pgnInput, setPgnInput] = useState('')
  const [positions, setPositions] = useState<{ fen: string; san: string }[]>([
    { fen: STARTING_FEN, san: '' },
  ])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [orientation, setOrientation] = useState<'white' | 'black'>('white')
  const [fenInput, setFenInput] = useState('')
  const [inputError, setInputError] = useState('')

  const currentPos = positions[currentIdx]
  const chess = new Chess(currentPos.fen)
  const legalMoves = chess.moves({ verbose: true }).map(m => m.from + m.to + (m.promotion ?? ''))

  const lastMove = currentIdx > 0
    ? (() => {
        const prev = positions[currentIdx - 1]
        const cur = positions[currentIdx]
        // Find what changed between FENs
        const from = pgn || prev.san ? extractFromTo(prev.fen, cur.fen) : null
        return from
      })()
    : null

  function extractFromTo(fenBefore: string, fenAfter: string): { from: string; to: string } | null {
    try {
      const b1 = new Chess(fenBefore)
      const b2 = new Chess(fenAfter)
      const files = 'abcdefgh'
      let from = '', to = ''
      for (let r = 1; r <= 8; r++) {
        for (const f of files) {
          const sq = `${f}${r}` as import('chess.js').Square
          const p1 = b1.get(sq)
          const p2 = b2.get(sq)
          if (p1 && !p2) from = sq
          else if (!p1 && p2) to = sq
        }
      }
      return from && to ? { from, to } : null
    } catch { return null }
  }

  const loadPgn = () => {
    setInputError('')
    try {
      const moves = parsePgn(pgnInput)
      if (moves.length === 0) { setInputError('No valid moves found'); return }
      const pos = buildPositions(moves)
      setPositions(pos)
      setCurrentIdx(0)
      setPgn(pgnInput)
    } catch {
      setInputError('Invalid PGN')
    }
  }

  const loadFen = () => {
    setInputError('')
    try {
      const g = new Chess(fenInput)
      setPositions([{ fen: g.fen(), san: '' }])
      setCurrentIdx(0)
      setFenInput('')
    } catch {
      setInputError('Invalid FEN string')
    }
  }

  const goTo = useCallback((idx: number) => {
    setCurrentIdx(Math.max(0, Math.min(positions.length - 1, idx)))
  }, [positions.length])

  const handleBoardMove = (uci: string) => {
    const from = uci.slice(0, 2)
    const to = uci.slice(2, 4)
    const prom = uci[4]
    try {
      const g = new Chess(currentPos.fen)
      const move = g.move({ from, to, promotion: prom ?? 'q' })
      if (!move) return
      const newPos = { fen: g.fen(), san: move.san }
      // Truncate future and append
      const newPositions = [...positions.slice(0, currentIdx + 1), newPos]
      setPositions(newPositions)
      setCurrentIdx(newPositions.length - 1)
    } catch {}
  }

  // Keyboard navigation
  const handleKey = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowLeft') goTo(currentIdx - 1)
    if (e.key === 'ArrowRight') goTo(currentIdx + 1)
    if (e.key === 'ArrowUp') goTo(0)
    if (e.key === 'ArrowDown') goTo(positions.length - 1)
  }, [currentIdx, goTo, positions.length])

  const movesSan = positions.slice(1).map(p => p.san)

  return (
    <div className="container mx-auto px-4 py-10 max-w-7xl" onKeyDown={handleKey} tabIndex={0} style={{ outline: 'none' }}>
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-3 mb-8">
          <BarChart2 className="text-cosmic-cyan" size={26} />
          <h1 className="text-2xl font-display font-bold text-nebula-100">Analysis Board</h1>
          <span className="text-xs text-nebula-400 ml-2">Use ← → arrows to navigate</span>
        </div>

        <div className="flex flex-col xl:flex-row gap-6 items-start">
          {/* Eval + Board */}
          <div className="flex gap-3 items-end flex-shrink-0 mx-auto xl:mx-0">
            <EvalBar height={520} />
            <div className="flex flex-col gap-3">
              <ChessBoard
                fen={currentPos.fen}
                orientation={orientation}
                onMove={handleBoardMove}
                lastMove={lastMove ?? undefined}
                legalMoves={legalMoves}
                size={520}
                interactive
              />

              {/* Navigation controls */}
              <div className="flex items-center justify-center gap-2">
                <button onClick={() => goTo(0)} className="btn-secondary p-2 rounded-lg" title="Start">
                  <SkipBack size={16} />
                </button>
                <button onClick={() => goTo(currentIdx - 1)} className="btn-secondary p-2 rounded-lg" title="Previous (←)">
                  <ChevronLeft size={16} />
                </button>
                <span className="text-sm font-mono text-nebula-400 min-w-[80px] text-center">
                  {currentIdx} / {positions.length - 1}
                </span>
                <button onClick={() => goTo(currentIdx + 1)} className="btn-secondary p-2 rounded-lg" title="Next (→)">
                  <ChevronRight size={16} />
                </button>
                <button onClick={() => goTo(positions.length - 1)} className="btn-secondary p-2 rounded-lg" title="End">
                  <SkipForward size={16} />
                </button>
                <button
                  onClick={() => setOrientation(o => o === 'white' ? 'black' : 'white')}
                  className="btn-secondary px-3 py-2 rounded-lg text-xs"
                >
                  Flip
                </button>
              </div>
            </div>
          </div>

          {/* Side panels */}
          <div className="flex-1 flex flex-col gap-4 min-w-0 w-full xl:w-auto">

            {/* FEN display */}
            <div className="card">
              <p className="text-xs text-nebula-400 uppercase tracking-wide font-semibold mb-2">Current FEN</p>
              <p className="font-mono text-xs text-nebula-200 break-all bg-nebula-900/60 rounded-lg px-3 py-2">
                {currentPos.fen}
              </p>
            </div>

            {/* Load PGN */}
            <div className="card">
              <h3 className="font-semibold text-nebula-200 mb-3 flex items-center gap-2">
                <Upload size={15} className="text-nebula-400" /> Load Game (PGN)
              </h3>
              <textarea
                className="input resize-none h-28 text-xs font-mono"
                placeholder={`Paste PGN here…\n\ne.g. 1. e4 e5 2. Nf3 Nc6 3. Bb5`}
                value={pgnInput}
                onChange={e => setPgnInput(e.target.value)}
              />
              {inputError && <p className="text-cosmic-red text-xs mt-1">{inputError}</p>}
              <button onClick={loadPgn} className="btn-primary w-full justify-center py-2.5 text-sm mt-3">
                Load PGN
              </button>
            </div>

            {/* Load FEN */}
            <div className="card">
              <h3 className="font-semibold text-nebula-200 mb-3">Load Position (FEN)</h3>
              <input
                className="input text-xs font-mono"
                placeholder="rnbqkbnr/pppppppp/8/…"
                value={fenInput}
                onChange={e => setFenInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && loadFen()}
              />
              <button onClick={loadFen} className="btn-secondary w-full justify-center py-2.5 text-sm mt-2">
                Set Position
              </button>
            </div>

            {/* Move list */}
            <div className="card flex-1 p-0 overflow-hidden" style={{ maxHeight: 280 }}>
              <div className="px-4 py-3 border-b border-nebula-700/30">
                <h3 className="font-semibold text-nebula-200 text-sm">Moves</h3>
              </div>
              <MoveList
                moves={movesSan}
                currentMove={currentIdx - 1}
                onSelectMove={idx => goTo(idx + 1)}
              />
            </div>

            {/* Position info */}
            <div className="card">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-nebula-400 text-xs mb-1">Turn</p>
                  <p className="font-semibold text-nebula-100 capitalize">
                    {chess.turn() === 'w' ? '♔ White' : '♚ Black'}
                  </p>
                </div>
                <div>
                  <p className="text-nebula-400 text-xs mb-1">Status</p>
                  <p className={clsx('font-semibold text-sm',
                    chess.isCheckmate() ? 'text-cosmic-red' :
                    chess.isCheck() ? 'text-cosmic-gold' : 'text-cosmic-green'
                  )}>
                    {chess.isCheckmate() ? 'Checkmate' :
                     chess.isStalemate() ? 'Stalemate' :
                     chess.isCheck() ? '⚠ Check' : 'Normal'}
                  </p>
                </div>
                <div>
                  <p className="text-nebula-400 text-xs mb-1">Castling</p>
                  <p className="text-nebula-200 font-mono text-xs">
                    {currentPos.fen.split(' ')[2] || '-'}
                  </p>
                </div>
                <div>
                  <p className="text-nebula-400 text-xs mb-1">Half-moves</p>
                  <p className="text-nebula-200 font-mono text-xs">
                    {currentPos.fen.split(' ')[4] || '0'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
