from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_title: str = "Online Cinema API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = (
        "postgresql+asyncpg://cinema_user:cinema_pass@localhost:5432/cinema_db"
    )

    # JWT
    jwt_secret: str = "change-me-in-production-to-something-secure"
    jwt_access_ttl_minutes: int = 30
    jwt_refresh_ttl_days: int = 7

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_success_url: str = "http://localhost:8000/payment/success"
    stripe_cancel_url: str = "http://localhost:8000/payment/cancel"

    # S3 / MinIO
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "cinema-avatars"

    # Email
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    email_from: str = "noreply@cinema.com"

    # Logging
    log_level: str = "DEBUG"


settings = Settings()
