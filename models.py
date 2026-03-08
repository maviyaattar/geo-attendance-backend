"""
models.py
---------
SQLAlchemy ORM models for the Geo Attendance system.

Tables:
    - Organization  – Defines attendance location and working period.
    - User          – Stores admin/user accounts linked to an organisation.
    - Attendance    – Individual attendance records with GPS co-ordinates.
"""

from datetime import date, time as time_type

from database import db


class Organization(db.Model):
    """
    Represents a company / team with a geofenced attendance location.

    Attributes:
        id           Primary key.
        name         Human-readable organisation name.
        location_lat Latitude of the office/site (decimal degrees).
        location_lon Longitude of the office/site (decimal degrees).
        radius       Allowed distance (metres) from the site for check-in.
        start_date   First day of the working period.
        end_date     Last day of the working period.
        off_days     Comma-separated weekday names that are non-working
                     (e.g. "Sunday" or "Saturday,Sunday").
    """

    __tablename__ = "organizations"

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(255), nullable=False)
    location_lat: float = db.Column(db.Float, nullable=False)
    location_lon: float = db.Column(db.Float, nullable=False)
    radius: float = db.Column(db.Float, nullable=False)  # metres
    start_date: date = db.Column(db.Date, nullable=False)
    end_date: date = db.Column(db.Date, nullable=False)
    off_days: str = db.Column(db.String(255), nullable=False, default="Sunday")

    # Relationships
    users = db.relationship("User", backref="organization", lazy=True)
    attendance_records = db.relationship("Attendance", backref="organization", lazy=True)

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dictionary of this organisation."""
        return {
            "id": self.id,
            "name": self.name,
            "location_lat": self.location_lat,
            "location_lon": self.location_lon,
            "radius": self.radius,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "off_days": self.off_days,
        }


class User(db.Model):
    """
    Application user – can be an admin or a regular employee.

    Attributes:
        id              Primary key.
        name            Full display name.
        email           Unique login e-mail.
        password_hash   Werkzeug-hashed password (never store plain text).
        role            Either ``"admin"`` or ``"user"``.
        organization_id Foreign key to :class:`Organization`.
    """

    __tablename__ = "users"

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(255), nullable=False)
    email: str = db.Column(db.String(255), unique=True, nullable=False)
    password_hash: str = db.Column(db.String(512), nullable=False)
    role: str = db.Column(db.String(10), nullable=False, default="user")
    organization_id: int = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=True
    )

    # Relationships
    attendance_records = db.relationship("Attendance", backref="user", lazy=True)

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dictionary (password hash excluded)."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "organization_id": self.organization_id,
        }


class Attendance(db.Model):
    """
    A single attendance check-in record.

    Attributes:
        id              Primary key.
        user_id         Foreign key to :class:`User`.
        organization_id Foreign key to :class:`Organization`.
        date            Calendar date of the check-in.
        time            Wall-clock time of the check-in.
        latitude        GPS latitude reported by the client.
        longitude       GPS longitude reported by the client.
    """

    __tablename__ = "attendance"

    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    organization_id: int = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    date: date = db.Column(db.Date, nullable=False)
    time: time_type = db.Column(db.Time, nullable=False)
    latitude: float = db.Column(db.Float, nullable=False)
    longitude: float = db.Column(db.Float, nullable=False)

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dictionary of this attendance record."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "date": self.date.isoformat(),
            "time": self.time.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
        }
