from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_VERSION: str = "1.0.0"
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    DATABASE_URL: str = "postgresql+asyncpg://nebula:nebula@localhost:5432/nebula_chess"
    REDIS_URL: str = "redis://localhost:6379/0"

    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Stockfish
    STOCKFISH_PATH: str = "/usr/games/stockfish"
    STOCKFISH_DEPTH: int = 15
    STOCKFISH_THREADS: int = 2

    # Game defaults
    DEFAULT_TIME_CONTROL_SECONDS: int = 600   # 10 min
    DEFAULT_INCREMENT_SECONDS: int = 5
    MAX_SPECTATORS_PER_GAME: int = 100
    MAX_CHAT_HISTORY: int = 200

    # Anti-cheat thresholds
    ANTICHEAT_ENGINE_CORRELATION_THRESHOLD: float = 0.85
    ANTICHEAT_ACCURACY_THRESHOLD: float = 0.92
    ANTICHEAT_MIN_MOVES_TO_EVALUATE: int = 10

    # Rate limits
    AUTH_RATE_LIMIT: str = "10/minute"
    API_RATE_LIMIT: str = "100/minute"
    WS_MAX_MESSAGE_RATE: int = 5  # messages per second

    # ELO
    ELO_K_FACTOR: int = 32
    DEFAULT_ELO: int = 1200

    # Puzzle
    DAILY_PUZZLE_REWARD_ELO: int = 0  # cosmetic only

    ENVIRONMENT: str = "development"


settings = Settings()
