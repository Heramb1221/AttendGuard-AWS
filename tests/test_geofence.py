"""Unit tests for the haversine-based geofence service."""
from app.services.geofence import haversine_distance_m, check_within_geofence


def test_same_point_has_zero_distance():
    distance = haversine_distance_m(19.0760, 72.8777, 19.0760, 72.8777)
    assert distance == 0.0


def test_known_distance_mumbai_to_pune_is_approximately_correct():
    # Mumbai to Pune is roughly 120-150 km depending on the exact points used.
    distance_m = haversine_distance_m(19.0760, 72.8777, 18.5204, 73.8567)
    distance_km = distance_m / 1000.0
    assert 100 < distance_km < 170


def test_within_geofence_true_when_inside_radius():
    within, distance = check_within_geofence(
        student_lat=19.07605, student_lon=72.87775,
        center_lat=19.07600, center_lon=72.87770,
        radius_m=100,
    )
    assert within is True
    assert distance < 100


def test_within_geofence_false_when_outside_radius():
    within, distance = check_within_geofence(
        student_lat=19.0900, student_lon=72.9000,
        center_lat=19.0760, center_lon=72.8777,
        radius_m=100,
    )
    assert within is False
    assert distance > 100
