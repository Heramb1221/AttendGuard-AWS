"""
Centralized application configuration.

All configuration is sourced from environment variables so that no secrets
are ever hardcoded in source control. See .env.example for the full list of
variables this application expects.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class BaseConfig:
    """Shared configuration across all environments."""

    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "Copy .env.example to .env and set a strong random value."
        )

    # ---- Database ----
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    if all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@"
            f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )
    else:
        # Falls back to a local sqlite file only when RDS credentials are not
        # supplied, so the app can still be smoke-tested without AWS access.
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "..", "instance", "dev.db"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # ---- AWS ----
    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
    S3_REPORTS_BUCKET = os.getenv("S3_REPORTS_BUCKET")

    # ---- Geofencing / anomaly detection tuning ----
    GEOFENCE_RADIUS_METERS = float(os.getenv("GEOFENCE_RADIUS_METERS", "100"))
    ANOMALY_TRUST_THRESHOLD = float(os.getenv("ANOMALY_TRUST_THRESHOLD", "50"))
    ANOMALY_WINDOW_SECONDS = int(os.getenv("ANOMALY_WINDOW_SECONDS", "60"))

    # ---- Session / cookies ----
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool_env("SESSION_COOKIE_SECURE", True)

    # ---- Logging ----
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    DEBUG = False


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
