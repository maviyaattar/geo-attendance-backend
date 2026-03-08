"""
config.py
---------
Flask application configuration.

Settings are read from environment variables with sensible defaults so the
app works out-of-the-box for local development and can be overridden on
deployment platforms like Render.
"""

import os


class Config:
    """Base configuration shared by all environments."""

    # Secret key used for signing tokens (itsdangerous) and Flask sessions.
    # Override via SECRET_KEY environment variable in production.
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me-in-production-supersecret")

    # SQLAlchemy database URI.
    # Defaults to a local SQLite file; override with a Postgres URL on Render.
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        "sqlite:///geo_attendance.db",
    )

    # Suppress SQLAlchemy modification tracking overhead.
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Token expiration in seconds (default: 24 hours).
    TOKEN_EXPIRY_SECONDS: int = int(os.environ.get("TOKEN_EXPIRY_SECONDS", 86400))


class DevelopmentConfig(Config):
    """Development-specific configuration."""

    DEBUG: bool = True


class ProductionConfig(Config):
    """Production-specific configuration."""

    DEBUG: bool = False


# Map string names to config classes so app.py can select the right one.
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
