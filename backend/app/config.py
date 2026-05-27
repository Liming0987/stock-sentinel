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

    # AWS — used by Secrets Manager client
    # All third-party API credentials live in a single secret:
    # stock-sentinel/credentials. See app/services/secrets.py.
    aws_region: str = "us-east-1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
