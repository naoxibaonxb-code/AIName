from datetime import timedelta
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pydantic import SecretStr

load_dotenv()


class Settings:
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = quote_plus(os.getenv("DB_PASSWORD", ""))
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "ainame")

    @property
    def db_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    MAIL_USERNAME: str | None = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD: SecretStr | None = SecretStr(os.getenv("MAIL_PASSWORD") or "")
    MAIL_SERVER: str | None = os.getenv("MAIL_SERVER")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587"))
    MAIL_FROM: str | None = os.getenv("MAIL_FROM")
    MAIL_STARTTLS: bool = os.getenv("MAIL_STARTTLS", "True").lower() == "true"
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", "False").lower() == "true"

    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", "change-this-development-secret-key"
    )
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(minutes=15)

    HISTORY_RETENTION_DAYS = max(1, int(os.getenv("HISTORY_RETENTION_DAYS", "30")))
    HISTORY_MAX_PER_USER = max(1, int(os.getenv("HISTORY_MAX_PER_USER", "100")))
    HISTORY_CLEANUP_INTERVAL_SECONDS = max(60, int(
        os.getenv("HISTORY_CLEANUP_INTERVAL_SECONDS", "21600")
    ))

    DAILY_FREE_GENERATIONS = max(1, int(os.getenv("DAILY_FREE_GENERATIONS", "3")))
    NAME_USER_RATE_LIMIT = max(1, int(os.getenv("NAME_USER_RATE_LIMIT", "6")))
    NAME_IP_RATE_LIMIT = max(1, int(os.getenv("NAME_IP_RATE_LIMIT", "20")))
    NAME_GLOBAL_RATE_LIMIT = max(1, int(os.getenv("NAME_GLOBAL_RATE_LIMIT", "120")))
    NAME_GENERATION_LOCK_SECONDS = max(90, int(
        os.getenv("NAME_GENERATION_LOCK_SECONDS", "120")
    ))

    DEEPSEEK_API_KEY: SecretStr | None = SecretStr(os.getenv("DEEPSEEK_API_KEY") or "")

    PG_NAME = os.getenv("PG_NAME", "postgresql")
    PG_USER = quote_plus(os.getenv("PG_USER", "postgres"))
    PG_PWD = os.getenv("PG_PWD", "")
    PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
    PG_PORT = int(os.getenv("PG_PORT", "5432"))
    PG_DB_NAME = os.getenv("PG_DB_NAME", "ainame")

    @property
    def pg_url(self) -> str:
        return f"{self.PG_NAME}://{self.PG_USER}:{self.PG_PWD}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB_NAME}"


settings = Settings()
