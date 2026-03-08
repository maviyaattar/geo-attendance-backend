"""
routes/auth_routes.py
---------------------
Authentication endpoints:
    POST /api/register  – Create a new user account.
    POST /api/login     – Authenticate and receive a signed token.

Tokens are signed with ``itsdangerous.URLSafeTimedSerializer`` and carry the
user's ID and role so downstream route guards can authorise requests without
a database round-trip.
"""

from flask import Blueprint, request, jsonify, current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash

from database import db
from models import User

auth_bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_token(user: User) -> str:
    """
    Create a signed, time-limited token encoding the user's ID and role.

    Args:
        user: The authenticated :class:`~models.User` instance.

    Returns:
        A URL-safe signed token string.
    """
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps({"user_id": user.id, "role": user.role})


def decode_token(token: str, app=None):
    """
    Decode and verify a signed token.

    Args:
        token: The token string received from the client.
        app:   Optional Flask app instance (uses ``current_app`` if omitted).

    Returns:
        The decoded payload dict on success.

    Raises:
        SignatureExpired: If the token has expired.
        BadSignature:     If the token is invalid or tampered.
    """
    from flask import current_app as _ca
    secret = (app or _ca).config["SECRET_KEY"]
    expiry = (app or _ca).config.get("TOKEN_EXPIRY_SECONDS", 86400)
    s = URLSafeTimedSerializer(secret)
    return s.loads(token, max_age=expiry)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@auth_bp.route("/api/register", methods=["POST"])
def register():
    """
    Register a new user.

    Request JSON body::

        {
            "name": "Alice",
            "email": "alice@example.com",
            "password": "s3cr3t",
            "role": "user",            // optional, defaults to "user"
            "organization_id": 1       // optional
        }

    Returns:
        201 with ``{"message": "...", "user": {...}}`` on success.
        400 with ``{"error": "..."}`` on validation failure.
        409 with ``{"error": "..."}`` if the e-mail is already registered.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    # --- Required field validation ---
    required_fields = ["name", "email", "password"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required."}), 400

    name: str = data["name"].strip()
    email: str = data["email"].strip().lower()
    password: str = data["password"]
    role: str = data.get("role", "user").strip().lower()
    organization_id = data.get("organization_id")

    # --- Type / constraint validation ---
    if role not in ("admin", "user"):
        return jsonify({"error": "'role' must be 'admin' or 'user'."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    if "@" not in email:
        return jsonify({"error": "Invalid e-mail address."}), 400

    # --- Duplicate check ---
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "E-mail address is already registered."}), 409

    # --- Persist ---
    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
        organization_id=organization_id,
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User registered successfully.", "user": user.to_dict()}), 201


@auth_bp.route("/api/login", methods=["POST"])
def login():
    """
    Authenticate a user and return a signed bearer token.

    Request JSON body::

        {
            "email": "alice@example.com",
            "password": "s3cr3t"
        }

    Returns:
        200 with ``{"token": "...", "user": {...}}`` on success.
        400 on missing fields.
        401 on invalid credentials.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    email: str = (data.get("email") or "").strip().lower()
    password: str = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "'email' and 'password' are required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid e-mail or password."}), 401

    token = _make_token(user)
    return jsonify({"token": token, "user": user.to_dict()}), 200
