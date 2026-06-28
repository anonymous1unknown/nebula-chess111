"""
Anti-cheat engine for Nebula Chess.
Uses statistical analysis of move quality vs engine suggestions.
Safe flow: auto-flag → human review → appeal. No blind banning.
"""
import json
from dataclasses import dataclass
from typing import Optional
import structlog

from app.config import settings

log = structlog.get_logger()


@dataclass
class CheatReport:
    user_id: str
    game_id: str
    engine_correlation: float        # fraction of moves matching engine top-1
    accuracy_score: float            # 0-1 (1 = perfect)
    time_anomaly_score: float        # 0-1 (1 = very suspicious timing)
    overall_suspicion_score: float   # combined weighted score
    engine_match_count: int
    total_moves: int
    avg_centipawn_loss: float
    suspicious_moves: list[dict]
    should_flag: bool
    reason: str


def analyze_game(
    user_id: str,
    game_id: str,
    moves: list[dict],          # {uci, best_move, centipawn_loss, time_spent_ms, engine_match}
) -> CheatReport:
    """
    Analyze a completed game for suspicious patterns.

    moves items:
      uci: str
      best_move: str
      centipawn_loss: float
      time_spent_ms: int
      engine_match: bool
    """
    if len(moves) < settings.ANTICHEAT_MIN_MOVES_TO_EVALUATE:
        return CheatReport(
            user_id=user_id, game_id=game_id,
            engine_correlation=0.0, accuracy_score=0.0,
            time_anomaly_score=0.0, overall_suspicion_score=0.0,
            engine_match_count=0, total_moves=len(moves),
            avg_centipawn_loss=0.0, suspicious_moves=[],
            should_flag=False, reason="insufficient_moves",
        )

    n = len(moves)
    engine_matches = sum(1 for m in moves if m.get("engine_match"))
    engine_correlation = engine_matches / n

    losses = [m.get("centipawn_loss") or 0 for m in moves]
    avg_loss = sum(losses) / n

    # Accuracy: perfect move = 0 loss, blunder = 300+ loss
    # Score per move: max(0, 1 - loss/300)
    accuracy_score = sum(max(0, 1 - l / 300) for l in losses) / n

    # Time anomaly: detect constant very-fast moves (< 1 second for complex positions)
    times = [m.get("time_spent_ms") or 5000 for m in moves]
    very_fast = sum(1 for t in times if t < 800)
    time_anomaly_score = very_fast / n

    # Suspicious individual moves (engine match + fast time + no centipawn loss)
    suspicious_moves = []
    for i, m in enumerate(moves):
        if m.get("engine_match") and (m.get("time_spent_ms") or 9999) < 1000:
            suspicious_moves.append({
                "move_number": i + 1,
                "uci": m.get("uci"),
                "time_ms": m.get("time_spent_ms"),
                "centipawn_loss": m.get("centipawn_loss"),
            })

    # Weighted overall score
    overall = (
        0.45 * engine_correlation +
        0.30 * accuracy_score +
        0.25 * time_anomaly_score
    )

    should_flag = (
        engine_correlation >= settings.ANTICHEAT_ENGINE_CORRELATION_THRESHOLD or
        (accuracy_score >= settings.ANTICHEAT_ACCURACY_THRESHOLD and n >= 20)
    )

    reason = ""
    if should_flag:
        if engine_correlation >= settings.ANTICHEAT_ENGINE_CORRELATION_THRESHOLD:
            reason = f"Engine correlation {engine_correlation:.1%} exceeds threshold"
        else:
            reason = f"Accuracy {accuracy_score:.1%} unusually high over {n} moves"

    report = CheatReport(
        user_id=user_id, game_id=game_id,
        engine_correlation=round(engine_correlation, 4),
        accuracy_score=round(accuracy_score, 4),
        time_anomaly_score=round(time_anomaly_score, 4),
        overall_suspicion_score=round(overall, 4),
        engine_match_count=engine_matches,
        total_moves=n,
        avg_centipawn_loss=round(avg_loss, 2),
        suspicious_moves=suspicious_moves,
        should_flag=should_flag,
        reason=reason,
    )

    if should_flag:
        log.warning("anticheat.flag", user_id=user_id, game_id=game_id,
                    correlation=engine_correlation, accuracy=accuracy_score)

    return report
