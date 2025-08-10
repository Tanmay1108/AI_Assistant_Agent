import os
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost/aiagent"
    REDIS_URL: str = "redis://localhost:6379"

    # AI Providers
    OPENAI_API_KEY: Optional[str] = "test_key"
    ANTHROPIC_API_KEY: Optional[str] = None
    DEFAULT_AI_PROVIDER: str = "openai"

    # External Services
    SMS_API_KEY: Optional[str] = None
    EMAIL_SERVICE_URL: Optional[str] = None

    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Logging
    LOG_LEVEL: str = "INFO"

    # Feature Flags
    ENABLE_FEEDBACK_LEARNING: bool = True
    ENABLE_ACCESSIBILITY_FEATURES: bool = True

    # PostgreSQL settings
    POSTGRES_DB_URL: str
    DB_ECHO_LOG: bool
    PG_POOL_SIZE: int
    PG_MAX_OVERFLOW: int
    PG_POOL_TIMEOUT: int
    PG_POOL_RECYCLE: int
    PING_INTERVAL: int

    # Queue Settings
    TASK_QUEUE_HIGH_PRIORITY: str = "tasks:high"
    TASK_QUEUE_NORMAL_PRIORITY: str = "tasks:normal"
    TASK_QUEUE_LOW_PRIORITY: str = "tasks:low"
    MAX_WORKERS: int = 4
    CONSUMER_GROUP: str = "ai_agent_workers"
    CONSUMER_TIMEOUT: int = 5000  # milliseconds

    # Webhook Settings
    WEBHOOK_BASE_URL: Optional[str] = None
    WEBHOOK_TIMEOUT: int = 30
    WEBHOOK_URL: str = "https://webhook.site/6ffe726d-1b5f-4d3e-a8da-0555e3a0f7d1"

    # Reminder Settings
    REMINDER_CHECK_INTERVAL: int = 60  # seconds

    GPT_Model: str = "testing"

    class Config:
        env_file = ".env"


settings = Settings()
