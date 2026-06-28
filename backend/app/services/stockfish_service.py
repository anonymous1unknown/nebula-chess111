"""
Stockfish integration — AI moves and post-game analysis.
Falls back gracefully if Stockfish is not installed.
"""
import asyncio
from typing import Optional
import structlog

from app.config import settings

log = structlog.get_logger()

_stockfish_available = False

try:
    from stockfish import Stockfish as _SF
    _stockfish_available = True
except Exception:
    log.warning("stockfish.not_available", msg="Install stockfish binary for AI/analysis")


def _get_engine(skill_level: int = 20) -> Optional[object]:
    if not _stockfish_available:
        return None
    try:
        sf = _SF(path=settings.STOCKFISH_PATH, depth=settings.STOCKFISH_DEPTH,
                 parameters={"Threads": settings.STOCKFISH_THREADS, "Skill Level": skill_level})
        return sf
    except Exception as e:
        log.error("stockfish.init_error", error=str(e))
        return None


async def get_ai_move(fen: str, difficulty: int = 10) -> Optional[str]:
    """
    Get best move from Stockfish for given FEN.
    difficulty: 1-20 (Stockfish skill level)
    Returns UCI move string or None.
    """
    def _sync():
        sf = _get_engine(skill_level=difficulty)
        if sf is None:
            return None
        try:
            sf.set_fen_position(fen)
            return sf.get_best_move()
        except Exception as e:
            log.error("stockfish.get_move_error", error=str(e))
            return None

    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def evaluate_position(fen: str, depth: int = 15) -> Optional[dict]:
    """
    Evaluate a position.
    Returns {score_cp: int, best_move: str, mate: int|None}
    """
    def _sync():
        sf = _get_engine(skill_level=20)
        if sf is None:
            return None
        try:
            sf.set_depth(depth)
            sf.set_fen_position(fen)
            best = sf.get_best_move()
            eval_info = sf.get_evaluation()
            return {
                "score_cp": eval_info.get("value", 0) if eval_info.get("type") == "cp" else 0,
                "mate": eval_info.get("value") if eval_info.get("type") == "mate" else None,
                "best_move": best,
            }
        except Exception as e:
            log.error("stockfish.eval_error", error=str(e))
            return None

    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def analyze_moves(fens_before: list[str]) -> list[Optional[dict]]:
    """
    Batch analysis for post-game move annotation.
    Returns list of {score_cp, best_move, mate} per position.
    """
    results = []
    for fen in fens_before:
        result = await evaluate_position(fen, depth=12)
        results.append(result)
    return results
