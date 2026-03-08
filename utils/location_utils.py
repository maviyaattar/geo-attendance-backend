"""
utils/location_utils.py
-----------------------
GPS / geolocation helpers.

Uses the Geopy library to calculate the great-circle distance between two
geographic co-ordinates and decide whether a user is within the allowed
radius of their organisation's site.
"""

from geopy.distance import geodesic


def calculate_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate the geodesic (great-circle) distance between two points.

    Args:
        lat1: Latitude of point 1 (decimal degrees).
        lon1: Longitude of point 1 (decimal degrees).
        lat2: Latitude of point 2 (decimal degrees).
        lon2: Longitude of point 2 (decimal degrees).

    Returns:
        Distance in **metres** between the two points.
    """
    point1 = (lat1, lon1)
    point2 = (lat2, lon2)
    return geodesic(point1, point2).meters


def is_within_radius(
    user_lat: float,
    user_lon: float,
    org_lat: float,
    org_lon: float,
    radius_meters: float,
) -> bool:
    """
    Check whether a user's GPS position is within the organisation's radius.

    Args:
        user_lat:      Latitude reported by the user's device.
        user_lon:      Longitude reported by the user's device.
        org_lat:       Latitude of the organisation's site.
        org_lon:       Longitude of the organisation's site.
        radius_meters: Maximum allowed distance from the site, in metres.

    Returns:
        ``True`` if the user is within the allowed radius, ``False`` otherwise.
    """
    distance = calculate_distance(user_lat, user_lon, org_lat, org_lon)
    return distance <= radius_meters
