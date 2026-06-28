// ── User ─────────────────────────────────────────────────────────────────────
export interface User {
  id: string
  username: string
  email?: string
  elo: number
  elo_rapid: number
  elo_blitz: number
  elo_bullet: number
  peak_elo: number
  games_played: number
  games_won: number
  games_lost: number
  games_drawn: number
  puzzles_solved: number
  puzzle_streak: number
  avatar_url?: string
  bio?: string
  country?: string
  theme: string
  board_theme: string
  piece_set: string
  show_coordinates: boolean
  auto_promote_queen: boolean
  sound_enabled: boolean
  created_at: string
  last_seen: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  user_id: string
  username: string
}

// ── Game ──────────────────────────────────────────────────────────────────────
export type Color = 'white' | 'black'
export type GameStatus = 'waiting' | 'active' | 'finished' | 'abandoned'
export type GameResult = 'white_wins' | 'black_wins' | 'draw' | 'in_progress' | 'aborted'
export type GameTermination =
  | 'checkmate' | 'resignation' | 'timeout' | 'stalemate'
  | 'insufficient_material' | 'threefold_repetition'
  | 'fifty_move_rule' | 'agreement' | 'abandoned'

export type TimeControl = 'bullet' | 'blitz' | 'rapid' | 'classical'
export type GameMode = 'ranked' | 'casual' | 'ai' | 'tournament' | 'daily'

export interface GameState {
  game_id: string
  fen: string
  turn: Color
  status: GameStatus
  result: GameResult | null
  termination: GameTermination | null
  white_time_ms: number
  black_time_ms: number
  move_count: number
  moves_san: string[]
  white_username: string
  black_username: string
  draw_offered_by: Color | null
}

export interface MoveData {
  uci: string
  san: string
  fen: string
  is_check: boolean
  is_checkmate: boolean
  captured?: string
  white_time_ms: number
  black_time_ms: number
  turn: Color
  move_number: number
  game_over?: { result: GameResult; termination: GameTermination }
}

// ── WebSocket Messages ────────────────────────────────────────────────────────
export type WsMessageType =
  | 'game_state' | 'move' | 'move_rejected' | 'chat'
  | 'game_over' | 'player_disconnected' | 'room_info'
  | 'draw_offered' | 'draw_declined' | 'resign' | 'pong'

export interface WsMessage<T = unknown> {
  type: WsMessageType
  data?: T
  ts?: number
}

// ── Chat ──────────────────────────────────────────────────────────────────────
export interface ChatMsg {
  username: string
  message: string
  ts: string
  system?: boolean
}

// ── Leaderboard ───────────────────────────────────────────────────────────────
export interface LeaderboardEntry {
  rank: number
  username: string
  elo: number
  games_played: number
  win_rate: number
  country?: string
  avatar_url?: string
}

// ── Piece ─────────────────────────────────────────────────────────────────────
export type PieceType = 'p' | 'n' | 'b' | 'r' | 'q' | 'k'
export type PieceColor = 'w' | 'b'

export interface Piece {
  type: PieceType
  color: PieceColor
}

// ── Square ────────────────────────────────────────────────────────────────────
export type File = 'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'g' | 'h'
export type Rank = '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8'
export type Square = `${File}${Rank}`

// ── History ───────────────────────────────────────────────────────────────────
export interface GameHistoryItem {
  id: string
  result: GameResult
  termination: GameTermination
  mode: GameMode
  time_control: TimeControl
  initial_time: number
  increment: number
  move_count: number
  played_as: Color
  elo_change?: number
  finished_at: string
}

// ── Puzzle ────────────────────────────────────────────────────────────────────
export interface Puzzle {
  id: string
  fen: string
  solution: string[]
  rating: number
  theme: string
  description: string
}
