import { useEffect, useRef, useCallback } from 'react'
import { useGameStore } from '../store/gameStore'
import { useAuthStore } from '../store/authStore'
import { WsMessage, GameState, MoveData, ChatMsg } from '../types'
import toast from 'react-hot-toast'

const WS_RECONNECT_DELAY = 2000
const WS_MAX_RETRIES = 5

export function useGameWebSocket(gameId: string | undefined) {
  const wsRef = useRef<WebSocket | null>(null)
  const retriesRef = useRef(0)
  const mountedRef = useRef(true)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()

  const {
    setState, applyMove, setMyColor, addChat,
    setConnected, setDrawOffered, setSpectatorCount,
  } = useGameStore()

  const { tokens } = useAuthStore()

  const connect = useCallback(() => {
    if (!gameId || !mountedRef.current) return

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const token = tokens?.access_token ?? ''
    const url = `${proto}//${host}/ws/game/${gameId}?token=${token}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      retriesRef.current = 0
      setConnected(true)
      ws.send(JSON.stringify({ type: 'request_state' }))
    }

    ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data)
        handleMessage(msg)
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = () => {
      setConnected(false)
      if (mountedRef.current && retriesRef.current < WS_MAX_RETRIES) {
        retriesRef.current++
        reconnectTimer.current = setTimeout(connect, WS_RECONNECT_DELAY)
      }
    }

    ws.onerror = () => ws.close()
  }, [gameId, tokens?.access_token]) // eslint-disable-line

  const handleMessage = (msg: WsMessage) => {
    switch (msg.type) {
      case 'game_state':
        setState(msg.data as GameState)
        break

      case 'move':
        applyMove(msg.data as MoveData)
        playMoveSound((msg.data as MoveData).is_check)
        break

      case 'move_rejected':
        toast.error(`Move rejected: ${(msg.data as { reason: string }).reason}`)
        break

      case 'chat':
        addChat(msg.data as ChatMsg)
        break

      case 'game_over': {
        const d = msg.data as { result: string; termination: string; resigned_by?: string }
        const msg2 = d.resigned_by
          ? `${d.resigned_by} resigned`
          : `Game over — ${d.result?.replace('_', ' ')}`
        toast.success(msg2, { duration: 5000 })
        break
      }

      case 'draw_offered': {
        const d = msg.data as { by: string }
        setDrawOffered(true)
        addChat({ username: 'System', message: `${d.by} offers a draw`, ts: new Date().toISOString(), system: true })
        break
      }

      case 'draw_declined':
        setDrawOffered(false)
        break

      case 'player_disconnected': {
        const d = msg.data as { username: string }
        addChat({ username: 'System', message: `${d.username} disconnected`, ts: new Date().toISOString(), system: true })
        break
      }

      case 'room_info': {
        const d = msg.data as { count: number }
        setSpectatorCount(d.count)
        break
      }
    }
  }

  const sendMove = useCallback((uci: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'move', data: { uci } }))
    }
  }, [])

  const sendChat = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'chat', data: { message } }))
    }
  }, [])

  const sendResign = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'resign' }))
    }
  }, [])

  const sendDrawOffer = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'offer_draw' }))
    }
  }, [])

  const sendDrawAccept = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'accept_draw' }))
    }
  }, [])

  const sendDrawDecline = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'decline_draw' }))
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { sendMove, sendChat, sendResign, sendDrawOffer, sendDrawAccept, sendDrawDecline }
}

// Simple audio feedback
let audioCtx: AudioContext | null = null

function playMoveSound(isCheck = false) {
  try {
    if (!audioCtx) audioCtx = new AudioContext()
    const osc = audioCtx.createOscillator()
    const gain = audioCtx.createGain()
    osc.connect(gain)
    gain.connect(audioCtx.destination)
    osc.frequency.value = isCheck ? 880 : 440
    gain.gain.setValueAtTime(0.1, audioCtx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.1)
    osc.start()
    osc.stop(audioCtx.currentTime + 0.1)
  } catch {
    // audio not available
  }
}
