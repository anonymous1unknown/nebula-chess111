import { create } from 'zustand'
import { GameState, MoveData, ChatMsg, Color } from '../types'

interface GameStore {
  state: GameState | null
  myColor: Color | null
  pendingMove: string | null
  lastMove: { from: string; to: string } | null
  chat: ChatMsg[]
  spectatorCount: number
  isConnected: boolean
  drawOffered: boolean

  setState: (s: GameState) => void
  applyMove: (move: MoveData) => void
  setMyColor: (c: Color) => void
  addChat: (msg: ChatMsg) => void
  setConnected: (v: boolean) => void
  setSpectatorCount: (n: number) => void
  setDrawOffered: (v: boolean) => void
  reset: () => void
}

export const useGameStore = create<GameStore>((set, get) => ({
  state: null,
  myColor: null,
  pendingMove: null,
  lastMove: null,
  chat: [],
  spectatorCount: 0,
  isConnected: false,
  drawOffered: false,

  setState: (s) => set({ state: s }),

  applyMove: (move) => {
    set((prev) => {
      const newState: GameState | null = prev.state
        ? {
            ...prev.state,
            fen: move.fen,
            turn: move.turn,
            white_time_ms: move.white_time_ms,
            black_time_ms: move.black_time_ms,
            move_count: move.move_number,
            moves_san: [...prev.state.moves_san, move.san],
            result: move.game_over?.result ?? prev.state.result,
            termination: move.game_over?.termination ?? prev.state.termination,
            status: move.game_over ? 'finished' : prev.state.status,
          }
        : null

      const uci = move.uci
      const from = uci.slice(0, 2)
      const to = uci.slice(2, 4)

      return { state: newState, lastMove: { from, to }, drawOffered: false }
    })
  },

  setMyColor: (c) => set({ myColor: c }),
  addChat: (msg) => set(s => ({ chat: [...s.chat.slice(-199), msg] })),
  setConnected: (v) => set({ isConnected: v }),
  setSpectatorCount: (n) => set({ spectatorCount: n }),
  setDrawOffered: (v) => set({ drawOffered: v }),
  reset: () => set({
    state: null, myColor: null, pendingMove: null,
    lastMove: null, chat: [], spectatorCount: 0,
    isConnected: false, drawOffered: false,
  }),
}))
