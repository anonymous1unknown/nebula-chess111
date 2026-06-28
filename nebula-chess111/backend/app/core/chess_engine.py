"""
Server-authoritative chess logic powered by python-chess.
The client never determines legality — this module is the single source of truth.
"""
from dataclasses import dataclass, field
from typing import Optional
import chess
import chess.pgn
import chess.svg
import io


@dataclass
class MoveResult:
    valid: bool
    san: str = ""
    uci: str = ""
    fen_after: str = ""
    is_check: bool = False
    is_checkmate: bool = False
    is_stalemate: bool = False
    is_game_over: bool = False
    game_result: Optional[str] = None   # "white_wins" | "black_wins" | "draw"
    termination: Optional[str] = None
    error: str = ""
    captured_piece: Optional[str] = None
    is_promotion: bool = False


def make_move(fen: str, uci_move: str) -> MoveResult:
    """Validate and apply a move. Returns full state."""
    try:
        board = chess.Board(fen)
    except ValueError:
        return MoveResult(valid=False, error="Invalid FEN")

    try:
        move = chess.Move.from_uci(uci_move)
    except ValueError:
        return MoveResult(valid=False, error="Invalid UCI move format")

    if move not in board.legal_moves:
        return MoveResult(valid=False, error="Illegal move")

    # Capture info
    captured = None
    if board.is_capture(move):
        cap_sq = move.to_square
        if board.is_en_passant(move):
            cap_sq = move.to_square + (8 if board.turn == chess.WHITE else -8)
        piece = board.piece_at(cap_sq)
        captured = piece.symbol() if piece else None

    is_promotion = move.promotion is not None
    san = board.san(move)
    board.push(move)

    fen_after = board.fen()
    is_check = board.is_check()
    is_checkmate = board.is_checkmate()
    is_stalemate = board.is_stalemate()
    is_game_over = board.is_game_over()

    game_result = None
    termination = None
    if is_game_over:
        outcome = board.outcome()
        if outcome:
            if outcome.winner == chess.WHITE:
                game_result = "white_wins"
            elif outcome.winner == chess.BLACK:
                game_result = "black_wins"
            else:
                game_result = "draw"

            term_map = {
                chess.Termination.CHECKMATE: "checkmate",
                chess.Termination.STALEMATE: "stalemate",
                chess.Termination.INSUFFICIENT_MATERIAL: "insufficient_material",
                chess.Termination.THREEFOLD_REPETITION: "threefold_repetition",
                chess.Termination.FIFTY_MOVES: "fifty_move_rule",
            }
            termination = term_map.get(outcome.termination, "unknown")

    return MoveResult(
        valid=True,
        san=san,
        uci=uci_move,
        fen_after=fen_after,
        is_check=is_check,
        is_checkmate=is_checkmate,
        is_stalemate=is_stalemate,
        is_game_over=is_game_over,
        game_result=game_result,
        termination=termination,
        captured_piece=captured,
        is_promotion=is_promotion,
    )


def get_legal_moves(fen: str) -> list[str]:
    """Return all legal UCI moves from a FEN position."""
    try:
        board = chess.Board(fen)
        return [m.uci() for m in board.legal_moves]
    except ValueError:
        return []


def build_pgn(moves_san: list[str], white: str, black: str, result: str, event: str = "Nebula Chess") -> str:
    """Build a PGN string from a list of SAN moves."""
    game = chess.pgn.Game()
    game.headers["Event"] = event
    game.headers["White"] = white
    game.headers["Black"] = black
    game.headers["Result"] = result

    node = game
    board = chess.Board()
    for san in moves_san:
        try:
            move = board.parse_san(san)
            board.push(move)
            node = node.add_variation(move)
        except Exception:
            break

    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=False)
    return game.accept(exporter)


def validate_fen(fen: str) -> bool:
    try:
        chess.Board(fen)
        return True
    except ValueError:
        return False


def fen_to_piece_map(fen: str) -> dict:
    """Return {square: piece_symbol} from a FEN."""
    try:
        board = chess.Board(fen)
        return {chess.square_name(sq): board.piece_at(sq).symbol()
                for sq in chess.SQUARES if board.piece_at(sq)}
    except Exception:
        return {}


def is_in_check(fen: str) -> bool:
    try:
        return chess.Board(fen).is_check()
    except Exception:
        return False


STARTING_FEN = chess.STARTING_FEN
