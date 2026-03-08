# Smart Location-Based Attendance Management System – Backend

A production-ready REST API backend for managing employee attendance through
GPS-based geofencing.  Built with Python 3.11, Flask, and SQLAlchemy; deployable
on [Render](https://render.com) out of the box.

---

## Architecture

```
Client (mobile / web)
        │  HTTPS / JSON
        ▼
   Flask (WSGI)          ← Gunicorn in production
        │
   Blueprints ─────────────────────────────────────────────┐
   ├── auth_routes       /api/register, /api/login         │
   ├── admin_routes      /api/admin/*                      │
   └── attendance_routes /api/mark-attendance, /api/dashboard
        │
   SQLAlchemy ORM
        │
   SQLite (dev) / PostgreSQL (prod)
```

### Key design decisions

| Concern | Choice |
|---|---|
| Auth | Signed tokens via `itsdangerous.URLSafeTimedSerializer` (stateless) |
| Password storage | `werkzeug.security.generate_password_hash` (PBKDF2-SHA256) |
| Geofencing | `geopy.distance.geodesic` (great-circle distance) |
| CORS | `flask-cors` – all origins allowed by default |
| DB bootstrapping | `db.create_all()` on startup – no migrations needed for dev |

---

## Folder Structure

```
├── app.py                    # Application factory & Gunicorn entry point
├── config.py                 # Environment-aware configuration
├── database.py               # Shared SQLAlchemy instance
├── models.py                 # ORM models: Organization, User, Attendance
├── routes/
│   ├── __init__.py
│   ├── auth_routes.py        # /api/register, /api/login
│   ├── admin_routes.py       # /api/admin/* (admin-only)
│   └── attendance_routes.py  # /api/mark-attendance, /api/dashboard
├── utils/
│   ├── __init__.py
│   ├── location_utils.py     # GPS distance helpers (Geopy)
│   └── attendance_utils.py   # Working-day & percentage helpers
├── requirements.txt
└── README.md
```

---

## API Reference

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/register` | Create a new user account |
| `POST` | `/api/login` | Authenticate and receive a Bearer token |

### User

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/mark-attendance` | Check in using GPS co-ordinates |
| `GET`  | `/api/dashboard` | Personal attendance summary |

### Admin *(requires `role: admin` token)*

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/admin/create-organization` | Create an organisation |
| `GET`  | `/api/admin/dashboard` | Organisation-level summary |
| `GET`  | `/api/admin/users` | List users in the admin's org |
| `GET`  | `/api/admin/attendance-report` | Full attendance report |

All protected endpoints expect an `Authorization: Bearer <token>` header.

---

## Database Design

### `organizations`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `name` | VARCHAR(255) | Organisation name |
| `location_lat` | FLOAT | Latitude of site |
| `location_lon` | FLOAT | Longitude of site |
| `radius` | FLOAT | Allowed check-in radius (metres) |
| `start_date` | DATE | Working period start |
| `end_date` | DATE | Working period end |
| `off_days` | VARCHAR(255) | e.g. `"Saturday,Sunday"` |

### `users`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `name` | VARCHAR(255) | Full name |
| `email` | VARCHAR(255) UNIQUE | Login e-mail |
| `password_hash` | VARCHAR(512) | Werkzeug PBKDF2 hash |
| `role` | VARCHAR(10) | `"admin"` or `"user"` |
| `organization_id` | INTEGER FK | → `organizations.id` |

### `attendance`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `user_id` | INTEGER FK | → `users.id` |
| `organization_id` | INTEGER FK | → `organizations.id` |
| `date` | DATE | Calendar date |
| `time` | TIME | Wall-clock time of check-in |
| `latitude` | FLOAT | GPS latitude from device |
| `longitude` | FLOAT | GPS longitude from device |

---

## Installation

### Prerequisites

- Python 3.11+
- pip

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/maviyaattar/geo-attendance-backend.git
cd geo-attendance-backend

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running Locally

```bash
# Development server (auto-reload)
flask run

# Or with Gunicorn
gunicorn app:app
```

The SQLite database file (`geo_attendance.db`) is created automatically on first
start-up.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `change-me-in-production-supersecret` | Token signing key |
| `DATABASE_URL` | `sqlite:///geo_attendance.db` | SQLAlchemy DB URI |
| `FLASK_ENV` | `development` | `development` or `production` |
| `TOKEN_EXPIRY_SECONDS` | `86400` | Token lifetime (seconds) |

Copy `.env.example` (or create a `.env` file) to set these:

```dotenv
SECRET_KEY=your-super-secret-key
DATABASE_URL=sqlite:///geo_attendance.db
FLASK_ENV=development
```

---

## Deploying on Render

1. Push your code to GitHub (already done).

2. Create a new **Web Service** on [render.com](https://render.com):
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

3. Add the following **Environment Variables** in the Render dashboard:
   - `SECRET_KEY` – a long random string
   - `DATABASE_URL` – your Render PostgreSQL connection string (or leave blank
     for SQLite during testing)
   - `FLASK_ENV` – `production`

4. Deploy!  Render will run `gunicorn app:app` and expose the service on a
   public URL.

> **Tip**: For production, use Render's managed PostgreSQL database and set
> `DATABASE_URL` to the provided connection string.  The app works with both
> SQLite (dev) and PostgreSQL (prod) without any code changes.