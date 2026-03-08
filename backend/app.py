"""
app.py
------
Flask application factory and entry point.

Run locally::

    cd backend
    flask run

Run with Gunicorn (production / Render)::

    cd backend
    gunicorn app:app

Environment variables (override via .env or Render dashboard):
    SECRET_KEY          – Token signing key (change in production!).
    DATABASE_URL        – Full SQLAlchemy DB URI.  Defaults to SQLite.
    FLASK_ENV           – "development" (default) or "production".
    TOKEN_EXPIRY_SECONDS – Signed token lifetime in seconds (default 86400).
"""

import os

from flask import Flask
from flask_cors import CORS

from config import config_map
from database import db


def create_app(config_name=None) -> Flask:
    """
    Flask application factory.

    Args:
        config_name: Key into ``config_map`` (e.g. ``"development"`` or
                     ``"production"``).  Reads ``FLASK_ENV`` env var when
                     *None*.

    Returns:
        A fully configured :class:`flask.Flask` application instance.
    """
    app = Flask(__name__)

    # --- Configuration ---
    env = config_name or os.environ.get("FLASK_ENV", "default")
    app.config.from_object(config_map.get(env, config_map["default"]))

    # --- Extensions ---
    CORS(app)          # Allow all origins; restrict in production if needed.
    db.init_app(app)

    # --- Blueprints ---
    from routes.auth_routes import auth_bp
    from routes.admin_routes import admin_bp
    from routes.attendance_routes import attendance_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(attendance_bp)

    # --- Database bootstrap (SQLite dev – no migration needed) ---
    with app.app_context():
        db.create_all()

    return app


# ---------------------------------------------------------------------------
# Module-level app instance used by Gunicorn (gunicorn app:app).
# ---------------------------------------------------------------------------
app: Flask = create_app()
