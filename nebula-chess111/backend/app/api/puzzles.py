from fastapi import APIRouter
from datetime import date

router = APIRouter()

# Seed puzzles — extend with a real puzzle DB
PUZZLES = [
    {
        "id": "p001",
        "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "solution": ["f3g5"],
        "rating": 1200,
        "theme": "fork",
        "description": "Find the winning tactic!",
    },
    {
        "id": "p002",
        "fen": "6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1",
        "solution": ["e1e8"],
        "rating": 1100,
        "theme": "back_rank",
        "description": "Back rank checkmate",
    },
    {
        "id": "p003",
        "fen": "r1b1kb1r/ppppqppp/2n2n2/4p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 6 5",
        "solution": ["f3g5"],
        "rating": 1350,
        "theme": "attack",
        "description": "Attack the weak f7 square",
    },
]


@router.get("/daily")
async def daily_puzzle():
    idx = date.today().toordinal() % len(PUZZLES)
    return PUZZLES[idx]


@router.get("/")
async def list_puzzles(limit: int = 10):
    return PUZZLES[:limit]
