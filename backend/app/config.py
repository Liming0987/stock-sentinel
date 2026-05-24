from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://sentinel:sentinel_dev_pass@localhost:5432/stock_sentinel"
    redis_url: str = "redis://localhost:6379/0"

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "stock-sentinel/1.0"

    # Market Data
    finnhub_api_key: str = ""
    polygon_api_key: str = ""
    alpha_vantage_api_key: str = ""

    # Auth
    jwt_secret: str = "change-this-to-a-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # Frontend
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
