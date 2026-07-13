from datetime import timedelta, timezone

from pydantic_settings import BaseSettings, SettingsConfigDict

MSK = timezone(timedelta(hours=3))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/luna-payments"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    outbox_poll_interval: float = 1.0  # интервал опроса outbox
    consumer_log_path: str = "logs/consumer.log"
    payments_queue: str = "payments.new"
    payments_dlx: str = "payments.new.dlx"
    payments_dlq: str = "payments.new.dlq"
    consumer_max_retries: int = 3
    api_key: str = "test-key"


settings = Settings()
