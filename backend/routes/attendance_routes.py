"""
routes/attendance_routes.py
---------------------------
User-facing attendance endpoints:

    POST /api/mark-attendance  – Check in using GPS co-ordinates.
    GET  /api/dashboard        – Personal attendance summary.

All endpoints require a valid Bearer token (any role may use them, but only
users with ``role == "user"`` make practical use of mark-attendance).
"""

from datetime import date, datetime

from flask import Blueprint, request, jsonify
from itsdangerous import BadSignature, SignatureExpired

from database import db
from models import Attendance, Organization, User
from utils.location_utils import is_within_radius
from utils.attendance_utils import count_working_days, calculate_attendance_percentage

attendance_bp = Blueprint("attendance", __name__)


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _get_current_user():
    """
    Extract and verify the Bearer token from the ``Authorization`` header.

    Returns:
        ``(user, None)`` on success or ``(None, error_response_tuple)`` on failure.
    """
    from routes.auth_routes import decode_token

    auth_header: str = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({"error": "Missing or invalid Authorization header."}), 401)

    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except SignatureExpired:
        return None, (jsonify({"error": "Token has expired. Please log in again."}), 401)
    except BadSignature:
        return None, (jsonify({"error": "Invalid token."}), 401)

    user = User.query.get(payload.get("user_id"))
    if not user:
        return None, (jsonify({"error": "User not found."}), 401)

    return user, None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@attendance_bp.route("/api/mark-attendance", methods=["POST"])
def mark_attendance():
    """
    Mark attendance for the authenticated user.

    The client must send the device's current GPS co-ordinates.  The backend
    verifies that the user is within the organisation's allowed radius before
    saving the record.  Only one record per user per calendar day is allowed.

    Request JSON body::

        {
            "latitude": 12.9716,
            "longitude": 77.5946
        }

    Returns:
        201 with the attendance record on success.
        400 on validation failure or if outside radius.
        401 / 403 on auth failure.
        409 if attendance already marked for today.
    """
    user, err = _get_current_user()
    if err:
        return err

    if not user.organization_id:
        return jsonify({"error": "You are not assigned to an organisation."}), 400

    org: Organization = Organization.query.get(user.organization_id)
    if not org:
        return jsonify({"error": "Organisation not found."}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    # --- Validate co-ordinates ---
    try:
        user_lat = float(data["latitude"])
        user_lon = float(data["longitude"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "'latitude' and 'longitude' are required numeric fields."}), 400

    if not (-90 <= user_lat <= 90):
        return jsonify({"error": "'latitude' must be between -90 and 90."}), 400
    if not (-180 <= user_lon <= 180):
        return jsonify({"error": "'longitude' must be between -180 and 180."}), 400

    # --- GPS proximity check ---
    if not is_within_radius(user_lat, user_lon, org.location_lat, org.location_lon, org.radius):
        return jsonify({
            "error": "You are not within the allowed radius of your organisation's site."
        }), 400

    today = date.today()

    # --- Duplicate check (one record per day) ---
    existing = Attendance.query.filter_by(
        user_id=user.id, organization_id=org.id, date=today
    ).first()
    if existing:
        return jsonify({"error": "Attendance already marked for today."}), 409

    # --- Persist ---
    record = Attendance(
        user_id=user.id,
        organization_id=org.id,
        date=today,
        time=datetime.now().time(),
        latitude=user_lat,
        longitude=user_lon,
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "message": "Attendance marked successfully.",
        "attendance": record.to_dict(),
    }), 201


@attendance_bp.route("/api/dashboard", methods=["GET"])
def user_dashboard():
    """
    Return the authenticated user's personal attendance summary.

    Includes:
        - User profile
        - Organisation details
        - Working days in the period
        - Present days (total check-ins)
        - Attendance percentage
        - Recent attendance records (last 10)

    Returns:
        200 with summary dict.
        401 on auth failure.
        400 if the user has no organisation.
    """
    user, err = _get_current_user()
    if err:
        return err

    if not user.organization_id:
        return jsonify({"error": "You are not assigned to an organisation."}), 400

    org: Organization = Organization.query.get(user.organization_id)
    if not org:
        return jsonify({"error": "Organisation not found."}), 404

    working_days = count_working_days(org.start_date, org.end_date, org.off_days)
    present_days = Attendance.query.filter_by(
        user_id=user.id, organization_id=org.id
    ).count()
    percentage = calculate_attendance_percentage(present_days, working_days)

    recent_records = (
        Attendance.query.filter_by(user_id=user.id, organization_id=org.id)
        .order_by(Attendance.date.desc(), Attendance.time.desc())
        .limit(10)
        .all()
    )

    return jsonify({
        "user": user.to_dict(),
        "organization": org.to_dict(),
        "working_days": working_days,
        "present_days": present_days,
        "attendance_percentage": percentage,
        "recent_records": [r.to_dict() for r in recent_records],
    }), 200
