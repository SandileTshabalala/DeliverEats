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
    DEBUG: str  

    model_config = SettingsConfigDict(
        env_file=".env.dev",
        env_file_encoding="utf-8"
    )

settings = Settings()
