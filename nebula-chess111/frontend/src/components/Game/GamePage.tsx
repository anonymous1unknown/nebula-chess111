import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Flag, Handshake, RotateCcw, Share2,
  Eye, MessageSquare, List, X, Users, LogIn,
} from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

import ChessBoard from '../Board/ChessBoard'
import Clock from './Clock'
import MoveList from './MoveList'
import ChatPanel from '../Chat/ChatPanel'
import EvalBar from '../Board/EvalBar'
import { useGameWebSocket } from '../../hooks/useGameWebSocket'
import { useGameStore } from '../../store/gameStore'
import { useAuthStore } from '../../store/authStore'
import { gamesApi } from '../../api/client'
import type { GameState } from '../../types'

type Panel = 'moves' | 'chat'

// ── Waiting lobby — shown to the CREATOR before the opponent joins ─────────────
function WaitingLobby({
  gameId,
  myColor,
  isConnected,
  inviteCode,
}: {
  gameId: string
  myColor: string | null
  isConnected: boolean
  inviteCode: string | null
}) {
  const navigate = useNavigate()

  // Build invite link — always includes the code so visitors can join
  const inviteLink = inviteCode
    ? `${window.location.origin}/game/${gameId}?code=${inviteCode}`
    : `${window.location.origin}/game/${gameId}`

  const handleCopy = () => {
    navigator.clipboard.writeText(inviteLink)
    toast.success('Invite link copied!')
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-nebula-gradient">
      <div className="starfield" />
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 card max-w-md w-full mx-4 text-center"
      >
        {/* Spinner */}
        <div className="flex justify-center mb-6">
          <div className="relative w-20 h-20">
            <div className="absolute inset-0 rounded-full border-4 border-nebula-700" />
            <div className="absolute inset-0 rounded-full border-4 border-t-nebula-400 animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <Users size={28} className="text-nebula-300" />
            </div>
          </div>
        </div>

        <h2 className="text-2xl font-display font-bold text-nebula-100 mb-2">
          Waiting for Opponent
        </h2>
        <p className="text-nebula-400 text-sm mb-1">
          You are playing as{' '}
          <span className={clsx(
            'font-semibold',
            myColor === 'white' ? 'text-nebula-50' : 'text-nebula-300',
          )}>
            {myColor === 'white' ? '♔ White' : myColor === 'black' ? '♚ Black' : '…'}
          </span>
        </p>
        <p className="text-nebula-500 text-xs mb-8">
          Share the link below — your opponent clicks it to join instantly
        </p>

        {/* Invite link */}
        <div className="bg-nebula-900/60 border border-nebula-600/30 rounded-xl px-4 py-3 mb-4 flex items-center gap-3">
          <span className="text-nebula-300 text-xs font-mono truncate flex-1 text-left">
            {inviteLink}
          </span>
          <button onClick={handleCopy} className="btn-primary py-1.5 px-3 text-xs shrink-0">
            <Share2 size={13} /> Copy
          </button>
        </div>

        {/* Invite code label */}
        {inviteCode && (
          <p className="text-nebula-500 text-xs mb-6">
            Or share the code manually:{' '}
            <span className="font-mono font-bold text-nebula-300 tracking-widest">
              {inviteCode}
            </span>
          </p>
        )}

        {/* Connection pill */}
        <div className="flex items-center justify-center gap-2 mb-6">
          <div className={clsx(
            'w-2 h-2 rounded-full',
            isConnected ? 'bg-cosmic-green animate-pulse' : 'bg-cosmic-red',
          )} />
          <span className="text-xs text-nebula-400">
            {isConnected ? 'Connected — waiting…' : 'Reconnecting…'}
          </span>
        </div>

        <button
          onClick={() => navigate('/')}
          className="btn-secondary w-full justify-center py-2.5 text-sm"
        >
          Cancel & return to lobby
        </button>
      </motion.div>
    </div>
  )
}

// ── Join prompt — shown to a VISITOR who arrives via the invite link ──────────
function JoinPrompt({
  gameId,
  inviteCode,
  waitingState,
  isConnected,
}: {
  gameId: string
  inviteCode: string
  waitingState: GameState
  isConnected: boolean
}) {
  const navigate   = useNavigate()
  const { user }   = useAuthStore()
  const [loading, setLoading] = useState(false)

  const handleJoin = async () => {
    if (!user) {
      toast.error('Log in first to join a game')
      navigate(`/login?next=/game/${gameId}?code=${inviteCode}`)
      return
    }

    setLoading(true)
    try {
      const { data } = await gamesApi.join(inviteCode)
      // Re-navigate to the clean game URL (no ?code=) so the WS reconnects
      // with the correct role now that the player is in the DB/Redis state.
      navigate(`/game/${data.game_id}`, { replace: true })
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        .response?.data?.detail
      toast.error(detail ?? 'Could not join game — it may be full or expired')
      setLoading(false)
    }
  }

  const creatorName = waitingState.white_username ?? waitingState.black_username ?? '…'

  return (
    <div className="min-h-screen flex items-center justify-center bg-nebula-gradient">
      <div className="starfield" />
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 card max-w-sm w-full mx-4 text-center"
      >
        {/* Chess piece icon */}
        <div className="text-5xl mb-4">♟</div>

        <h2 className="text-2xl font-display font-bold text-nebula-100 mb-2">
          You're Invited!
        </h2>
        <p className="text-nebula-300 text-sm mb-1">
          <span className="font-semibold text-nebula-100">{creatorName}</span>{' '}
          is challenging you to a game of chess
        </p>
        <p className="text-nebula-500 text-xs mb-8">
          Code:{' '}
          <span className="font-mono font-bold text-nebula-300 tracking-widest">
            {inviteCode}
          </span>
        </p>

        {/* Join button */}
        <button
          onClick={handleJoin}
          disabled={loading || !isConnected}
          className="btn-primary w-full justify-center py-3.5 text-base font-bold mb-3 disabled:opacity-50"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              Joining…
            </>
          ) : !user ? (
            <><LogIn size={18} /> Log in to Join</>
          ) : (
            <><Users size={18} /> Accept Challenge</>
          )}
        </button>

        <button
          onClick={() => navigate('/')}
          className="btn-secondary w-full justify-center py-2.5 text-sm"
        >
          Decline & go to lobby
        </button>

        {/* Connection status */}
        <div className="flex items-center justify-center gap-2 mt-4">
          <div className={clsx(
            'w-1.5 h-1.5 rounded-full',
            isConnected ? 'bg-cosmic-green' : 'bg-cosmic-red animate-pulse',
          )} />
          <span className="text-[11px] text-nebula-500">
            {isConnected ? 'Connected' : 'Reconnecting…'}
          </span>
        </div>
      </motion.div>
    </div>
  )
}

// ── Player info strip ─────────────────────────────────────────────────────────
function PlayerInfo({
  username, active, isMe,
}: { username: string; active: boolean; isMe: boolean }) {
  return (
    <div className={clsx(
      'flex items-center gap-2 px-3 py-1.5 rounded-xl transition-all duration-300',
      active && 'bg-nebula-700/40',
    )}>
      <div className={clsx(
        'w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0',
        isMe ? 'bg-nebula-500 text-white' : 'bg-nebula-800 text-nebula-300',
      )}>
        {username?.[0]?.toUpperCase() ?? '?'}
      </div>
      <div>
        <p className={clsx(
          'text-sm font-semibold leading-tight',
          isMe ? 'text-nebula-100' : 'text-nebula-200',
        )}>
          {username}
        </p>
        {active && <p className="text-[10px] text-cosmic-green font-mono">thinking…</p>}
      </div>
    </div>
  )
}

// ── Main GamePage ─────────────────────────────────────────────────────────────
export default function GamePage() {
  const { gameId }  = useParams<{ gameId: string }>()
  const navigate    = useNavigate()
  const { user }    = useAuthStore()

  const {
    state, myColor, lastMove, chat, isConnected,
    drawOffered, setMyColor, reset,
  } = useGameStore()

  const {
    sendMove, sendChat, sendResign,
    sendDrawOffer, sendDrawAccept, sendDrawDecline,
  } = useGameWebSocket(gameId)

  const [legalMoves,    setLegalMoves]    = useState<string[]>([])
  const [panel,         setPanel]          = useState<Panel>('moves')
  const [boardSize,     setBoardSize]      = useState(520)
  const [confirmResign, setConfirmResign]  = useState(false)
  const [flipped,       setFlipped]        = useState(false)

  // Determine which colour the local user plays
  useEffect(() => {
    if (!state || !user) return
    if (state.white_username === user.username) setMyColor('white')
    else if (state.black_username === user.username) setMyColor('black')
  }, [state?.white_username, state?.black_username, user?.username]) // eslint-disable-line

  // Fetch server-validated legal moves on each new position
  useEffect(() => {
    if (!gameId || !state || state.status !== 'active') return
    gamesApi.getLegalMoves(gameId)
      .then(r => setLegalMoves(r.data.moves))
      .catch(() => {})
  }, [gameId, state?.fen]) // eslint-disable-line

  // Responsive board size
  useEffect(() => {
    const update = () => {
      const size = Math.min(window.innerWidth - 400, window.innerHeight - 140, 640)
      setBoardSize(Math.max(280, size))
    }
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])

  useEffect(() => () => reset(), [reset])

  const handleMove = useCallback((uci: string) => {
    if (!state || state.status !== 'active') return
    if (state.turn !== myColor) { toast.error('Not your turn'); return }
    sendMove(uci)
  }, [state, myColor, sendMove])

  const handleResign = () => {
    if (!confirmResign) { setConfirmResign(true); return }
    sendResign()
    setConfirmResign(false)
  }

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href)
    toast.success('Game link copied!')
  }

  // ── Connecting ──────────────────────────────────────────────────────────────
  if (!isConnected && !state) {
    return (
      <div className="flex items-center justify-center h-screen bg-nebula-gradient">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-nebula-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-nebula-300">Connecting…</p>
        </div>
      </div>
    )
  }

  // ── Waiting game ────────────────────────────────────────────────────────────
  if (state?.status === 'waiting') {
    const inviteCode = state.invite_code ?? null

    // Read ?code= from the URL — visitors arrive via the shareable link
    const urlCode = new URLSearchParams(window.location.search).get('code')

    const isCreator = myColor === 'white' || myColor === 'black'

    if (isCreator) {
      // Show the shareable waiting room to the creator
      return (
        <WaitingLobby
          gameId={gameId ?? ''}
          myColor={myColor}
          isConnected={isConnected}
          inviteCode={inviteCode}
        />
      )
    }

    // Non-creator — show join prompt if we have a code (from URL or from state)
    const joinCode = urlCode ?? inviteCode
    if (joinCode) {
      return (
        <JoinPrompt
          gameId={gameId ?? ''}
          inviteCode={joinCode}
          waitingState={state}
          isConnected={isConnected}
        />
      )
    }

    // Visitor with no code — generic "game not started" screen
    return (
      <div className="flex items-center justify-center h-screen bg-nebula-gradient">
        <div className="card text-center max-w-sm mx-4">
          <div className="text-4xl mb-4">⏳</div>
          <h2 className="text-xl font-display font-bold text-nebula-100 mb-2">
            Game hasn't started
          </h2>
          <p className="text-nebula-400 text-sm mb-6">
            You need an invite link to join this game
          </p>
          <button onClick={() => navigate('/')} className="btn-primary w-full justify-center">
            Back to Lobby
          </button>
        </div>
      </div>
    )
  }

  // ── Active / finished game ──────────────────────────────────────────────────
  const gameOver     = state?.status === 'finished'
  const isMyTurn     = state?.turn === myColor
  const orientation  = flipped
    ? (myColor === 'white' ? 'black' : 'white')
    : (myColor ?? 'white')

  const topColor     = orientation === 'white' ? 'black' : 'white'
  const topPlayer    = orientation === 'white' ? state?.black_username : state?.white_username
  const bottomPlayer = orientation === 'white' ? state?.white_username : state?.black_username
  const topTimeMs    = orientation === 'white' ? state?.black_time_ms  : state?.white_time_ms
  const bottomTimeMs = orientation === 'white' ? state?.white_time_ms  : state?.black_time_ms
  const topActive    = state?.turn === topColor    && !gameOver
  const bottomActive = state?.turn === orientation && !gameOver

  const resultText = () => {
    if (state?.result === 'white_wins') return '1-0'
    if (state?.result === 'black_wins') return '0-1'
    if (state?.result === 'draw')       return '½-½'
    return ''
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-nebula-gradient">
      <div className="flex gap-4 w-full max-w-7xl items-center justify-center">

        {/* Eval bar */}
        <div className="hidden lg:flex self-stretch items-stretch py-2">
          <EvalBar height={boardSize} />
        </div>

        {/* Board column */}
        <div className="flex flex-col items-center gap-3">

          {/* Top player + clock */}
          <div className="w-full flex items-center justify-between px-1">
            <PlayerInfo
              username={topPlayer ?? '…'}
              active={!!topActive}
              isMe={topPlayer === user?.username}
            />
            <Clock
              timeMs={topTimeMs ?? 0}
              isActive={!!topActive}
              label={topColor === 'white' ? 'White' : 'Black'}
              color={topColor as 'white' | 'black'}
            />
          </div>

          {/* Board */}
          <div className="relative">
            {!isConnected && (
              <div className="absolute inset-0 flex items-center justify-center z-30 rounded-lg bg-nebula-950/70 backdrop-blur">
                <div className="text-center">
                  <div className="w-8 h-8 border-2 border-nebula-400 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                  <p className="text-sm text-nebula-300">Reconnecting…</p>
                </div>
              </div>
            )}

            <ChessBoard
              fen={state?.fen ?? 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'}
              orientation={orientation as 'white' | 'black'}
              onMove={handleMove}
              disabled={!isMyTurn || gameOver || !isConnected}
              lastMove={lastMove}
              legalMoves={isMyTurn && !gameOver ? legalMoves : []}
              size={boardSize}
            />

            {/* Game-over overlay */}
            <AnimatePresence>
              {gameOver && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="absolute inset-0 flex items-center justify-center z-20 rounded-lg"
                  style={{ background: 'rgba(9,6,24,0.78)', backdropFilter: 'blur(4px)' }}
                >
                  <div className="text-center card p-8">
                    <div className="text-5xl font-display font-bold text-gradient mb-2">
                      {resultText()}
                    </div>
                    <p className="text-nebula-300 text-sm capitalize mb-1">
                      {state?.termination?.replace(/_/g, ' ')}
                    </p>
                    <div className="flex gap-3 mt-5 justify-center">
                      <button className="btn-secondary" onClick={() => navigate('/')}>
                        New Game
                      </button>
                      <button className="btn-primary" onClick={handleShare}>
                        <Share2 size={14} /> Share
                      </button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Bottom player + clock */}
          <div className="w-full flex items-center justify-between px-1">
            <PlayerInfo
              username={bottomPlayer ?? '…'}
              active={!!bottomActive}
              isMe={bottomPlayer === user?.username}
            />
            <Clock
              timeMs={bottomTimeMs ?? 0}
              isActive={!!bottomActive}
              label={orientation === 'white' ? 'White' : 'Black'}
              color={orientation as 'white' | 'black'}
            />
          </div>

          {/* Controls */}
          {!gameOver && myColor && (
            <div className="flex items-center gap-2 mt-1">
              <button
                onClick={sendDrawOffer}
                className="btn-secondary text-xs py-1.5 px-3"
                title="Offer draw"
              >
                <Handshake size={14} /> Draw
              </button>
              <button
                onClick={handleResign}
                className={clsx(
                  'text-xs py-1.5 px-3 rounded-lg font-semibold transition-all border',
                  confirmResign
                    ? 'bg-cosmic-red/20 border-cosmic-red/50 text-cosmic-red'
                    : 'bg-white/5 border-white/10 text-nebula-300 hover:bg-white/10',
                )}
              >
                <Flag size={14} className="inline mr-1" />
                {confirmResign ? 'Confirm?' : 'Resign'}
              </button>
              {confirmResign && (
                <button
                  onClick={() => setConfirmResign(false)}
                  className="text-xs py-1.5 px-2 rounded-lg bg-white/5 border border-white/10 text-nebula-400 hover:bg-white/10 transition-all"
                >
                  <X size={14} />
                </button>
              )}
              <button
                onClick={() => setFlipped(f => !f)}
                className="btn-secondary text-xs py-1.5 px-3"
                title="Flip board"
              >
                <RotateCcw size={14} />
              </button>
              <button onClick={handleShare} className="btn-secondary text-xs py-1.5 px-3">
                <Share2 size={14} />
              </button>
            </div>
          )}

          {/* Draw offer banner */}
          <AnimatePresence>
            {drawOffered && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="card p-3 flex items-center gap-3 w-full border-cosmic-gold/40"
              >
                <span className="text-sm text-nebula-200 flex-1">Draw offered</span>
                <button onClick={sendDrawAccept}  className="btn-primary  py-1.5 px-3 text-xs">Accept</button>
                <button onClick={sendDrawDecline} className="btn-secondary py-1.5 px-3 text-xs">Decline</button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Side panel */}
        <div
          className="hidden md:flex flex-col glass rounded-2xl overflow-hidden"
          style={{ width: 280, height: boardSize + 120 }}
        >
          <div className="flex border-b border-nebula-700/40">
            {([['moves', List], ['chat', MessageSquare]] as const).map(([key, Icon]) => (
              <button
                key={key}
                onClick={() => setPanel(key)}
                className={clsx(
                  'flex-1 flex items-center justify-center gap-1.5 py-3 text-xs font-semibold uppercase tracking-wide transition-all',
                  panel === key
                    ? 'text-nebula-200 border-b-2 border-nebula-400'
                    : 'text-nebula-500 hover:text-nebula-300',
                )}
              >
                <Icon size={13} /> {key}
              </button>
            ))}
            <div className="flex items-center px-3 gap-1 text-xs text-nebula-500">
              <Eye size={12} />
              {useGameStore.getState().spectatorCount}
            </div>
          </div>

          <div className="flex-1 overflow-hidden">
            {panel === 'moves' && <MoveList moves={state?.moves_san ?? []} />}
            {panel === 'chat'  && (
              <ChatPanel messages={chat} onSend={sendChat} disabled={!user} />
            )}
          </div>

          <div className="border-t border-nebula-700/40 px-4 py-2 flex items-center gap-2">
            <div className={clsx(
              'w-2 h-2 rounded-full',
              isConnected ? 'bg-cosmic-green' : 'bg-cosmic-red animate-pulse',
            )} />
            <span className="text-xs text-nebula-400">
              {isConnected ? 'Connected' : 'Reconnecting…'}
            </span>
            <span className="ml-auto text-xs text-nebula-500 font-mono">
              #{gameId?.slice(0, 8)}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
