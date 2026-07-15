"""
Geofence validation service.

Uses the haversine formula to compute great-circle distance between a
student's reported GPS coordinates and a session's registered classroom
center point, in meters.
"""
import math
from typing import Tuple

EARTH_RADIUS_METERS = 6371000.0


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the distance in meters between two lat/lon points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_METERS * c


def check_within_geofence(
    student_lat: float,
    student_lon: float,
    center_lat: float,
    center_lon: float,
    radius_m: float,
) -> Tuple[bool, float]:
    """
    Return (is_within, distance_m) for the given student coordinates against
    the session's geofence.
    """
    distance_m = haversine_distance_m(student_lat, student_lon, center_lat, center_lon)
    return distance_m <= radius_m, distance_m
