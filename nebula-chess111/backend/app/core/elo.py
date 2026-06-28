from app.config import settings


def expected_score(rating_a: int, rating_b: int) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def new_ratings(white_elo: int, black_elo: int, result: str) -> tuple[int, int]:
    """
    result: 'white_wins' | 'black_wins' | 'draw'
    Returns (white_change, black_change)
    """
    K = settings.ELO_K_FACTOR
    exp_w = expected_score(white_elo, black_elo)
    exp_b = 1 - exp_w

    if result == "white_wins":
        score_w, score_b = 1.0, 0.0
    elif result == "black_wins":
        score_w, score_b = 0.0, 1.0
    else:
        score_w, score_b = 0.5, 0.5

    delta_w = round(K * (score_w - exp_w))
    delta_b = round(K * (score_b - exp_b))
    return delta_w, delta_b
