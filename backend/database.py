"""
database.py
-----------
Creates the shared SQLAlchemy instance.

Importing ``db`` from this module (instead of from ``app``) prevents circular
imports between models, routes, and the application factory.
"""

from flask_sqlalchemy import SQLAlchemy

# Single SQLAlchemy instance used across the entire application.
db: SQLAlchemy = SQLAlchemy()
