"""
routes/admin_routes.py
----------------------
Admin-only API endpoints:

    POST /api/admin/create-organization  – Create a new organisation.
    GET  /api/admin/dashboard            – Summary statistics.
    GET  /api/admin/users                – List users in the admin's org.
    GET  /api/admin/attendance-report    – Full attendance report for the org.

All endpoints require a valid Bearer token with ``role == "admin"``.
"""

from datetime import date

from flask import Blueprint, request, jsonify
from itsdangerous import BadSignature, SignatureExpired

from database import db
from models import Organization, User, Attendance
from utils.attendance_utils import count_working_days, calculate_attendance_percentage

admin_bp = Blueprint("admin", __name__)


# ---------------------------------------------------------------------------
# Auth helpers (local to this blueprint)
# ---------------------------------------------------------------------------

def _get_current_user():
    """
    Extract and verify the Bearer token from the ``Authorization`` header.

    Returns:
        The :class:`~models.User` instance on success, or a Flask response
        tuple ``(json_response, status_code)`` on failure.
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


def _require_admin():
    """
    Verify that the request is made by an admin user.

    Returns:
        ``(admin_user, None)`` on success or ``(None, error_response)`` on failure.
    """
    user, err = _get_current_user()
    if err:
        return None, err
    if user.role != "admin":
        return None, (jsonify({"error": "Admin access required."}), 403)
    return user, None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/create-organization", methods=["POST"])
def create_organization():
    """
    Create a new organisation.

    Request JSON body::

        {
            "name": "Acme Corp",
            "location_lat": 12.9716,
            "location_lon": 77.5946,
            "radius": 200,
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "off_days": "Saturday,Sunday"
        }

    Returns:
        201 with the created organisation on success.
        400 / 401 / 403 on validation or auth failure.
    """
    admin, err = _require_admin()
    if err:
        return err

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    required = ["name", "location_lat", "location_lon", "radius", "start_date", "end_date"]
    for field in required:
        if data.get(field) is None:
            return jsonify({"error": f"'{field}' is required."}), 400

    # --- Type validation ---
    try:
        location_lat = float(data["location_lat"])
        location_lon = float(data["location_lon"])
        radius = float(data["radius"])
    except (ValueError, TypeError):
        return jsonify({"error": "'location_lat', 'location_lon', and 'radius' must be numbers."}), 400

    if not (-90 <= location_lat <= 90):
        return jsonify({"error": "'location_lat' must be between -90 and 90."}), 400
    if not (-180 <= location_lon <= 180):
        return jsonify({"error": "'location_lon' must be between -180 and 180."}), 400
    if radius <= 0:
        return jsonify({"error": "'radius' must be a positive number."}), 400

    try:
        start_date = date.fromisoformat(data["start_date"])
        end_date = date.fromisoformat(data["end_date"])
    except ValueError:
        return jsonify({"error": "'start_date' and 'end_date' must be ISO-format dates (YYYY-MM-DD)."}), 400

    if end_date < start_date:
        return jsonify({"error": "'end_date' must be on or after 'start_date'."}), 400

    off_days: str = data.get("off_days", "Sunday").strip()

    org = Organization(
        name=data["name"].strip(),
        location_lat=location_lat,
        location_lon=location_lon,
        radius=radius,
        start_date=start_date,
        end_date=end_date,
        off_days=off_days,
    )
    db.session.add(org)
    db.session.commit()

    return jsonify({"message": "Organisation created successfully.", "organization": org.to_dict()}), 201


@admin_bp.route("/api/admin/dashboard", methods=["GET"])
def admin_dashboard():
    """
    Return a summary of the admin's organisation.

    Returns organisation details, total users, total attendance records, and
    overall attendance percentage for the organisation.

    Returns:
        200 with summary dict.
        401 / 403 on auth failure.
        404 if the admin has no organisation.
    """
    admin, err = _require_admin()
    if err:
        return err

    if not admin.organization_id:
        return jsonify({"error": "Admin is not linked to any organisation."}), 404

    org: Organization = Organization.query.get(admin.organization_id)
    if not org:
        return jsonify({"error": "Organisation not found."}), 404

    total_users = User.query.filter_by(organization_id=org.id, role="user").count()
    total_records = Attendance.query.filter_by(organization_id=org.id).count()
    working_days = count_working_days(org.start_date, org.end_date, org.off_days)

    # Present days per user then average – or total records vs total expected.
    expected_total = working_days * total_users if total_users else 0
    overall_percentage = calculate_attendance_percentage(total_records, expected_total)

    return jsonify({
        "organization": org.to_dict(),
        "total_users": total_users,
        "total_attendance_records": total_records,
        "working_days": working_days,
        "overall_attendance_percentage": overall_percentage,
    }), 200


@admin_bp.route("/api/admin/users", methods=["GET"])
def list_users():
    """
    List all users belonging to the admin's organisation.

    Returns:
        200 with list of user dicts.
        401 / 403 on auth failure.
        404 if admin has no organisation.
    """
    admin, err = _require_admin()
    if err:
        return err

    if not admin.organization_id:
        return jsonify({"error": "Admin is not linked to any organisation."}), 404

    users = User.query.filter_by(organization_id=admin.organization_id, role="user").all()
    return jsonify({"users": [u.to_dict() for u in users]}), 200


@admin_bp.route("/api/admin/attendance-report", methods=["GET"])
def attendance_report():
    """
    Return an attendance report for every user in the admin's organisation.

    Query parameters (optional):
        user_id (int): Filter report to a single user.

    Each entry includes present days, working days, and attendance percentage.

    Returns:
        200 with report list.
        401 / 403 on auth failure.
        404 if admin has no organisation.
    """
    admin, err = _require_admin()
    if err:
        return err

    if not admin.organization_id:
        return jsonify({"error": "Admin is not linked to any organisation."}), 404

    org: Organization = Organization.query.get(admin.organization_id)
    if not org:
        return jsonify({"error": "Organisation not found."}), 404

    working_days = count_working_days(org.start_date, org.end_date, org.off_days)

    # Optional filter by user_id
    filter_user_id = request.args.get("user_id", type=int)

    users_query = User.query.filter_by(organization_id=org.id, role="user")
    if filter_user_id:
        users_query = users_query.filter_by(id=filter_user_id)

    report = []
    for user in users_query.all():
        present_days = Attendance.query.filter_by(
            user_id=user.id, organization_id=org.id
        ).count()
        percentage = calculate_attendance_percentage(present_days, working_days)
        report.append({
            "user": user.to_dict(),
            "present_days": present_days,
            "working_days": working_days,
            "attendance_percentage": percentage,
        })

    return jsonify({"report": report}), 200
