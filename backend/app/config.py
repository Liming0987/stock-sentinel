from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://sentinel:sentinel_dev_pass@localhost:5432/stock_sentinel"
    redis_url: str = "redis://localhost:6379/0"

    # Auth (JWT secret can stay in env since it's app-internal, not third-party)
    jwt_secret: str = "change-this-to-a-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # Trading
    # Near-close EOD buy limit = signal price × (1 + eod_limit_buffer).
    # Higher = more reliable fills but more slippage; lower = tighter entries,
    # more missed fills on volatile names. Override via EOD_LIMIT_BUFFER env var.
    eod_limit_buffer: float = 0.005

    # Exit levels. "atr" (default): each strategy sets its own ATR/structure-based
    # stop & target. "percent": override every buy with a fixed % around the entry
    # price — target = entry × (1 + target_pct), stop = entry × (1 - stop_pct).
    # Override via EXIT_MODE / TARGET_PCT / STOP_PCT env vars.
    exit_mode: str = "atr"     # "atr" | "percent"
    target_pct: float = 0.05   # +5% target above entry when exit_mode == "percent"
    stop_pct: float = 0.05     # -5% stop below entry when exit_mode == "percent"

    # Sentiment model. False (default) = VADER only (fast, tiny memory) — chosen to fit
    # a 2 GB t4g.small host. True = FinBERT (finance-tuned, needs torch + ~1.5 GB RAM, so a
    # 4 GB instance). Sentiment no longer drives trades; it feeds the trending/sentiment
    # dashboards only. Override via USE_FINBERT env var.
    use_finbert: bool = False

    # AWS — used by Secrets Manager client
    # All third-party API credentials live in a single secret:
    # stock-sentinel/credentials. See app/services/secrets.py.
    aws_region: str = "us-east-1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
