import { useState, useCallback, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Chess } from 'chess.js'
import type { Square, Color, Piece } from '../../types'

// ── Piece SVG renders ─────────────────────────────────────────────────────────
const PIECE_UNICODE: Record<string, string> = {
  wk: '♔', wq: '♕', wr: '♖', wb: '♗', wn: '♘', wp: '♙',
  bk: '♚', bq: '♛', br: '♜', bb: '♝', bn: '♞', bp: '♟',
}

const PIECE_COLORS: Record<string, { text: string; shadow: string }> = {
  w: { text: '#f0ecff', shadow: 'rgba(0,0,0,0.9)' },
  b: { text: '#1a1030', shadow: 'rgba(255,255,255,0.2)' },
}

function PieceIcon({ piece, size }: { piece: Piece; size: number }) {
  const key = `${piece.color}${piece.type}`
  const clr = PIECE_COLORS[piece.color]
  return (
    <span
      style={{
        fontSize: size * 0.72,
        lineHeight: 1,
        color: clr.text,
        textShadow: `0 1px 3px ${clr.shadow}, 0 0 8px ${clr.shadow}`,
        userSelect: 'none',
        display: 'block',
        filter: piece.color === 'w'
          ? 'drop-shadow(0 2px 4px rgba(0,0,0,0.8))'
          : 'drop-shadow(0 2px 4px rgba(0,0,0,0.6))',
      }}
    >
      {PIECE_UNICODE[key]}
    </span>
  )
}

// ── Board colors ──────────────────────────────────────────────────────────────
const THEMES: Record<string, { light: string; dark: string; border: string }> = {
  cosmic: {
    light: '#c8b8e8',
    dark: '#4a3570',
    border: '#7c63e8',
  },
  classic: {
    light: '#f0d9b5',
    dark: '#b58863',
    border: '#8b6914',
  },
  midnight: {
    light: '#8ca0b8',
    dark: '#2c3e50',
    border: '#34495e',
  },
  emerald: {
    light: '#a8c8a0',
    dark: '#3a7d44',
    border: '#2d6a35',
  },
}

// ── Types ─────────────────────────────────────────────────────────────────────
interface ChessBoardProps {
  fen: string
  orientation?: Color
  onMove?: (uci: string) => void
  disabled?: boolean
  lastMove?: { from: string; to: string } | null
  legalMoves?: string[]
  boardTheme?: string
  showCoordinates?: boolean
  size?: number
  interactive?: boolean
}

const FILES = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
const RANKS = ['8', '7', '6', '5', '4', '3', '2', '1']

export default function ChessBoard({
  fen,
  orientation = 'white',
  onMove,
  disabled = false,
  lastMove,
  legalMoves = [],
  boardTheme = 'cosmic',
  showCoordinates = true,
  size = 560,
  interactive = true,
}: ChessBoardProps) {
  const [selected, setSelected] = useState<string | null>(null)
  const [dragging, setDragging] = useState<string | null>(null)
  const [dragPos, setDragPos] = useState({ x: 0, y: 0 })
  const [promotionState, setPromotionState] = useState<{ from: string; to: string } | null>(null)
  const [animatingPiece, setAnimatingPiece] = useState<string | null>(null)

  const theme = THEMES[boardTheme] || THEMES.cosmic
  const sqSize = size / 8

  // Parse board from FEN
  const chess = useMemo(() => {
    try { return new Chess(fen) } catch { return new Chess() }
  }, [fen])

  const board = chess.board()

  // Legal destinations for selected piece
  const legalTargets = useMemo(() => {
    if (!selected) return new Set<string>()
    return new Set(
      legalMoves
        .filter(m => m.startsWith(selected))
        .map(m => m.slice(2, 4))
    )
  }, [selected, legalMoves])

  // Square coordinate helpers
  const squareName = (file: number, rank: number): string => {
    const f = orientation === 'white' ? file : 7 - file
    const r = orientation === 'white' ? 7 - rank : rank
    return `${FILES[f]}${r + 1}`
  }

  const getPiece = (sq: string): Piece | null => {
    const file = sq.charCodeAt(0) - 97
    const rank = parseInt(sq[1]) - 1
    const piece = board[7 - rank]?.[file]
    return piece ? { type: piece.type as Piece['type'], color: piece.color as Piece['color'] } : null
  }

  const handleSquareClick = useCallback((sq: string) => {
    if (!interactive || disabled) return
    const piece = getPiece(sq)

    if (selected) {
      if (legalTargets.has(sq)) {
        attemptMove(selected, sq)
        setSelected(null)
      } else if (piece && piece.color === (chess.turn() === 'w' ? 'w' : 'b')) {
        setSelected(sq)
      } else {
        setSelected(null)
      }
    } else {
      if (piece && piece.color === (chess.turn() === 'w' ? 'w' : 'b')) {
        setSelected(sq)
      }
    }
  }, [selected, legalTargets, chess, interactive, disabled]) // eslint-disable-line

  const attemptMove = useCallback((from: string, to: string) => {
    // Check if promotion
    const piece = getPiece(from)
    const isPromotion = piece?.type === 'p' && (to[1] === '8' || to[1] === '1')
    if (isPromotion) {
      setPromotionState({ from, to })
      return
    }
    setAnimatingPiece(`${from}${to}`)
    setTimeout(() => setAnimatingPiece(null), 200)
    onMove?.(`${from}${to}`)
  }, [onMove, getPiece]) // eslint-disable-line

  const handlePromotion = (piece: string) => {
    if (!promotionState) return
    onMove?.(`${promotionState.from}${promotionState.to}${piece}`)
    setPromotionState(null)
  }

  // Drag handlers
  const handleMouseDown = (e: React.MouseEvent, sq: string) => {
    if (!interactive || disabled) return
    const piece = getPiece(sq)
    if (!piece || piece.color !== (chess.turn() === 'w' ? 'w' : 'b')) return
    e.preventDefault()
    setDragging(sq)
    setSelected(sq)
    setDragPos({ x: e.clientX, y: e.clientY })
  }

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (dragging) setDragPos({ x: e.clientX, y: e.clientY })
  }, [dragging])

  const handleMouseUp = useCallback((e: MouseEvent) => {
    if (!dragging) return
    const el = document.elementFromPoint(e.clientX, e.clientY)
    const sq = el?.closest('[data-square]')?.getAttribute('data-square')
    if (sq && sq !== dragging && legalTargets.has(sq)) {
      attemptMove(dragging, sq)
      setSelected(null)
    }
    setDragging(null)
  }, [dragging, legalTargets, attemptMove])

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [handleMouseMove, handleMouseUp])

  // Touch support
  const handleTouchStart = (e: React.TouchEvent, sq: string) => {
    if (!interactive || disabled) return
    const piece = getPiece(sq)
    if (!piece || piece.color !== (chess.turn() === 'w' ? 'w' : 'b')) return
    const t = e.touches[0]
    setDragging(sq)
    setSelected(sq)
    setDragPos({ x: t.clientX, y: t.clientY })
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!dragging) return
    const t = e.touches[0]
    setDragPos({ x: t.clientX, y: t.clientY })
  }

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!dragging) return
    const t = e.changedTouches[0]
    const el = document.elementFromPoint(t.clientX, t.clientY)
    const sq = el?.closest('[data-square]')?.getAttribute('data-square')
    if (sq && sq !== dragging && legalTargets.has(sq)) {
      attemptMove(dragging, sq)
      setSelected(null)
    }
    setDragging(null)
  }

  const inCheck = chess.inCheck()
  const kingSq = inCheck
    ? (() => {
        const turn = chess.turn()
        for (let r = 0; r < 8; r++) {
          for (let f = 0; f < 8; f++) {
            const p = board[r][f]
            if (p?.type === 'k' && p.color === turn) {
              return `${FILES[f]}${8 - r}`
            }
          }
        }
        return null
      })()
    : null

  const renderSquares = () => {
    const squares = []
    for (let rank = 0; rank < 8; rank++) {
      for (let file = 0; file < 8; file++) {
        const sq = squareName(file, rank)
        const isLight = (file + rank) % 2 === 0
        const piece = getPiece(sq)
        const isSelected = selected === sq
        const isLastMove = lastMove && (lastMove.from === sq || lastMove.to === sq)
        const isLegal = legalTargets.has(sq)
        const isCaptureLegal = isLegal && !!piece
        const isKingCheck = sq === kingSq
        const isDraggingThis = dragging === sq

        const bgColor = isLight ? theme.light : theme.dark

        squares.push(
          <div
            key={sq}
            data-square={sq}
            onClick={() => handleSquareClick(sq)}
            onMouseDown={(e) => handleMouseDown(e, sq)}
            onTouchStart={(e) => handleTouchStart(e, sq)}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
            className="relative flex items-center justify-center cursor-pointer select-none"
            style={{
              width: sqSize,
              height: sqSize,
              backgroundColor: bgColor,
              boxShadow: isSelected
                ? `inset 0 0 0 3px rgba(240,180,41,0.9)`
                : isLastMove
                ? `inset 0 0 0 3px rgba(240,180,41,0.45)`
                : undefined,
              background: isKingCheck
                ? `radial-gradient(circle at center, rgba(248,113,113,0.85) 0%, ${bgColor} 70%)`
                : isLastMove
                ? `linear-gradient(135deg, rgba(240,180,41,0.35), transparent), ${bgColor}`
                : bgColor,
            }}
          >
            {/* Coordinates */}
            {showCoordinates && rank === 7 && (
              <span className="absolute bottom-0.5 right-1 text-[10px] font-mono font-semibold opacity-50 leading-none"
                style={{ color: isLight ? theme.dark : theme.light }}>
                {sq[0]}
              </span>
            )}
            {showCoordinates && file === 0 && (
              <span className="absolute top-0.5 left-1 text-[10px] font-mono font-semibold opacity-50 leading-none"
                style={{ color: isLight ? theme.dark : theme.light }}>
                {sq[1]}
              </span>
            )}

            {/* Legal move dot */}
            {isLegal && !isCaptureLegal && (
              <div
                className="absolute rounded-full pointer-events-none z-10"
                style={{
                  width: sqSize * 0.3,
                  height: sqSize * 0.3,
                  background: 'rgba(61, 45, 138, 0.65)',
                }}
              />
            )}

            {/* Legal capture ring */}
            {isCaptureLegal && (
              <div
                className="absolute inset-0 pointer-events-none z-10 rounded-none"
                style={{
                  boxShadow: `inset 0 0 0 ${sqSize * 0.09}px rgba(61,45,138,0.7)`,
                }}
              />
            )}

            {/* Piece */}
            {piece && (
              <motion.div
                key={`${sq}-${piece.type}${piece.color}`}
                initial={animatingPiece?.endsWith(sq) ? { scale: 0.8, opacity: 0 } : false}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.15 }}
                className="absolute inset-0 flex items-center justify-center z-20"
                style={{
                  opacity: isDraggingThis ? 0.3 : 1,
                  cursor: interactive && !disabled ? 'grab' : 'default',
                  transform: isDraggingThis ? 'scale(0.9)' : 'scale(1)',
                  transition: 'transform 0.1s',
                }}
              >
                <PieceIcon piece={piece} size={sqSize} />
              </motion.div>
            )}
          </div>
        )
      }
    }
    return squares
  }

  return (
    <div className="relative" style={{ width: size, height: size }}>
      {/* Board */}
      <div
        className="grid relative"
        style={{
          width: size,
          height: size,
          gridTemplateColumns: `repeat(8, ${sqSize}px)`,
          gridTemplateRows: `repeat(8, ${sqSize}px)`,
          borderRadius: 8,
          overflow: 'hidden',
          boxShadow: `0 0 0 2px ${theme.border}40, 0 20px 60px rgba(0,0,0,0.8)`,
        }}
      >
        {renderSquares()}
      </div>

      {/* Dragging ghost piece */}
      <AnimatePresence>
        {dragging && getPiece(dragging) && (
          <div
            className="fixed pointer-events-none z-50 flex items-center justify-center"
            style={{
              left: dragPos.x - sqSize / 2,
              top: dragPos.y - sqSize / 2,
              width: sqSize,
              height: sqSize,
              transform: 'scale(1.15)',
              filter: 'drop-shadow(0 8px 20px rgba(0,0,0,0.6))',
            }}
          >
            <PieceIcon piece={getPiece(dragging)!} size={sqSize} />
          </div>
        )}
      </AnimatePresence>

      {/* Promotion picker */}
      <AnimatePresence>
        {promotionState && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="absolute inset-0 flex items-center justify-center z-50"
            style={{ background: 'rgba(9,6,24,0.85)', backdropFilter: 'blur(8px)' }}
          >
            <div className="card p-4 flex flex-col items-center gap-3">
              <p className="text-nebula-200 font-semibold text-sm">Promote to</p>
              <div className="flex gap-2">
                {['q', 'r', 'b', 'n'].map(p => {
                  const color = chess.turn() === 'w' ? 'w' : 'b'
                  return (
                    <button
                      key={p}
                      onClick={() => handlePromotion(p)}
                      className="w-14 h-14 rounded-xl bg-nebula-800 hover:bg-nebula-600 border border-nebula-500/40 flex items-center justify-center transition-all hover:scale-110"
                    >
                      <PieceIcon piece={{ type: p as Piece['type'], color: color as Piece['color'] }} size={56} />
                    </button>
                  )
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
