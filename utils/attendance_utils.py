"""
utils/attendance_utils.py
-------------------------
Business logic helpers for working-day calculation and attendance statistics.
"""

from datetime import date, timedelta
from typing import List


def get_working_days(
    start_date: date,
    end_date: date,
    off_days: str,
) -> List[date]:
    """
    Return a list of working days between *start_date* and *end_date* (inclusive).

    Non-working days are determined by *off_days*, a comma-separated string of
    full weekday names (e.g. ``"Sunday"`` or ``"Saturday,Sunday"``).

    Args:
        start_date: First day of the working period.
        end_date:   Last day of the working period (inclusive).
        off_days:   Comma-separated weekday names to exclude, case-insensitive.

    Returns:
        List of :class:`datetime.date` objects that are working days.
    """
    # Normalise off-day names to title-case for consistent comparison.
    off_day_names = {day.strip().title() for day in off_days.split(",") if day.strip()}

    working_days: List[date] = []
    current = start_date
    while current <= end_date:
        # strftime("%A") returns the full weekday name, e.g. "Monday".
        if current.strftime("%A") not in off_day_names:
            working_days.append(current)
        current += timedelta(days=1)

    return working_days


def count_working_days(start_date: date, end_date: date, off_days: str) -> int:
    """
    Return the total number of working days in the given period.

    Args:
        start_date: First day of the working period.
        end_date:   Last day of the working period (inclusive).
        off_days:   Comma-separated weekday names to exclude.

    Returns:
        Integer count of working days.
    """
    return len(get_working_days(start_date, end_date, off_days))


def calculate_attendance_percentage(present_days: int, working_days: int) -> float:
    """
    Calculate the attendance percentage for a user.

    Formula: ``(present_days / working_days) * 100``

    Args:
        present_days: Number of days the user was present.
        working_days: Total number of scheduled working days.

    Returns:
        Attendance percentage as a float, or ``0.0`` if *working_days* is zero
        (to avoid division by zero).
    """
    if working_days == 0:
        return 0.0
    return round((present_days / working_days) * 100, 2)
