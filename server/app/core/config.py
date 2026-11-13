import os

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    REDIS_URL: str
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_MAX_CONNECTIONS: int = 20
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    REDIS_RETRY_ON_TIMEOUT: bool = True
    REDIS_HEALTH_CHECK_INTERVAL: int = 30
    RATE_LIMIT_DEFAULT: int = 100
    RATE_LIMIT_AUTH: int = 10
    RATE_LIMIT_REFRESH: int = 5
    RATE_LIMIT_WINDOW: int = 60           # seconds
    # Optional role-based overrides
    RATE_LIMIT_AUTHENTICATED: int = 300
    RATE_LIMIT_ADMIN: int = 1000
    MAX_WAIT_MINUTES: int = 30
    ENV: str = "development"
    # REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_URL: str = "redis://redis:6379/0"
    CORS_ORIGINS: str
    DEBUG: str = "development"

    # Public URLs. PayFast must be able to reach PUBLIC_API_URL from the internet
    # (use an ngrok / cloudflared tunnel in development).
    FRONTEND_URL: str = "http://localhost:5173"
    PUBLIC_API_URL: str = "http://localhost:8000"

    # PayFast account of the PLATFORM (https://developers.payfast.co.za).
    # Used only to collect restaurant subscriptions. Money for food orders goes
    # to each restaurant's own PayFast account, which the restaurant enters in
    # its settings screen.
    PAYFAST_MERCHANT_ID: str | None = None
    PAYFAST_MERCHANT_KEY: str | None = None
    PAYFAST_PASSPHRASE: str | None = None
    PAYFAST_SANDBOX: bool = True

    # Default delivery fee (rands) for restaurants that have not set their own.
    # Each restaurant sets its real fee, flat or per km, in its settings screen.
    DELIVERY_FEE: float = 0.0

    # Where uploaded images (restaurant logos) are stored
    UPLOAD_DIR: str = "uploads"

    # First platform owner account, created by `python -m app.db.init_db`.
    # No defaults on purpose: there must never be a built-in login.
    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None
    ADMIN_NAME: str = "Platform"
    ADMIN_SURNAME: str = "Owner"
    ADMIN_CONTACT_NUMBER: str | None = None

    # Name used in SMS and email
    APP_NAME: str = "L'vovo"

    # SMS: Africa's Talking (https://africastalking.com). Leave empty to switch SMS off.
    AT_USERNAME: str | None = None      # "sandbox" while testing
    AT_API_KEY: str | None = None
    AT_SENDER_ID: str | None = None     # optional registered sender name / short code
    AT_SANDBOX: bool = False            # true = sandbox API (messages go to the simulator)
    DEFAULT_COUNTRY_CODE: str = "+27"   # for numbers typed as 072...

    # Email: Resend (https://resend.com). Leave empty to switch email off.
    RESEND_API_KEY: str | None = None
    EMAIL_FROM: str | None = None       # e.g. "L'vovo <orders@yourdomain.co.za>" (verified domain)

    PASSWORD_RESET_MINUTES: int = 30

    # Secret used to encrypt restaurants' PayFast keys in the database.
    ENCRYPTION_KEY: str | None = None

    # Subscriptions. While this is False nothing is blocked, so existing
    # restaurants keep trading while you create plans and assign them.
    SUBSCRIPTIONS_ENFORCED: bool = False
    # Days a restaurant stays open after its paid period ends
    SUBSCRIPTION_GRACE_DAYS: int = 5

    @field_validator("DATABASE_URL")
    @classmethod
    def use_installed_postgres_driver(cls, url: str) -> str:
        """
        Pin the Postgres driver to psycopg2, the one in requirements.txt.

        A plain "postgresql://" URL lets SQLAlchemy choose, and SQLAlchemy 2.1
        switched its default to psycopg 3, which is not installed: the server
        then crashed at import with "No module named 'psycopg'". Hosting
        providers also hand out "postgres://", which SQLAlchemy rejects.
        """
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+psycopg2://" + url[len(prefix):]
        return url

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    model_config = SettingsConfigDict(
        # Real environment variables always win over the file
        env_file=".env.prod" if os.getenv("ENV", "development").lower() == "production" else ".env.dev",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
