"""
Anomaly detection engine.

This is the differentiator of AttendGuard: rather than trusting every
geofence-valid submission at face value, each attendance record is scored
for signs of proxy attendance (one student marking present for another).

Detection rules (each rule that fires subtracts points from a starting
trust score of 100):

  1. DUPLICATE_DEVICE   - the same device fingerprint was used to submit
                           attendance for a *different* student in the same
                           session within the configured time window. This
                           is the strongest signal of one phone being passed
                           around a classroom.

  2. DUPLICATE_GPS      - two or more students submitted GPS coordinates
                           that match to within ~2 meters in the same
                           session within the time window. Real GPS reads
                           always carry small consumer-grade jitter, so
                           near-identical readings across different people
                           are suspicious.

  3. IMPOSSIBLE_TRAVEL  - the same student has an attendance record in a
                           *different* session shortly before this one, at a
                           location that would require an implausible speed
                           to travel between (a simple proxy for "the phone
                           moved, but did the student?").

A record is flagged for faculty review when the final trust score drops
below `ANOMALY_TRUST_THRESHOLD` (see app/config.py).
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List

from app.services.geofence import haversine_distance_m

DUPLICATE_DEVICE_PENALTY = 60
DUPLICATE_GPS_PENALTY = 50
IMPOSSIBLE_TRAVEL_PENALTY = 70
DUPLICATE_GPS_EPSILON_METERS = 2.0
IMPLAUSIBLE_SPEED_KMH = 150.0


@dataclass
class AnomalyResult:
    trust_score: float
    flagged: bool
    reasons: List[str] = field(default_factory=list)


def evaluate(
    *,
    student_id: int,
    session_id: int,
    course_id: int,
    latitude: float,
    longitude: float,
    device_fingerprint: str,
    submitted_at: datetime,
    window_seconds: int,
    trust_threshold: float,
    db_session,
) -> AnomalyResult:
    """
    Run all anomaly rules for a new attendance submission and return the
    computed AnomalyResult. Must be called BEFORE the new record is
    committed, so that "recent" queries only see prior submissions.
    """
    from app.models.attendance import Attendance
    from app.models.session import AttendanceSession

    score = 100.0
    reasons: List[str] = []

    window_start = submitted_at - timedelta(seconds=window_seconds)

    # ---- Rule 1: duplicate device fingerprint used by a different student ----
    duplicate_device = (
        db_session.query(Attendance)
        .filter(
            Attendance.session_id == session_id,
            Attendance.student_id != student_id,
            Attendance.device_fingerprint == device_fingerprint,
            Attendance.submitted_at >= window_start,
        )
        .first()
    )
    if duplicate_device is not None:
        score -= DUPLICATE_DEVICE_PENALTY
        reasons.append("DUPLICATE_DEVICE")

    # ---- Rule 2: near-identical GPS coordinates from a different student ----
    recent_in_session = (
        db_session.query(Attendance)
        .filter(
            Attendance.session_id == session_id,
            Attendance.student_id != student_id,
            Attendance.submitted_at >= window_start,
        )
        .all()
    )
    for record in recent_in_session:
        distance = haversine_distance_m(
            latitude, longitude, record.latitude, record.longitude
        )
        if distance <= DUPLICATE_GPS_EPSILON_METERS:
            score -= DUPLICATE_GPS_PENALTY
            reasons.append("DUPLICATE_GPS")
            break

    # ---- Rule 3: impossible travel between this student's recent sessions ----
    previous_record = (
        db_session.query(Attendance, AttendanceSession)
        .join(AttendanceSession, Attendance.session_id == AttendanceSession.id)
        .filter(
            Attendance.student_id == student_id,
            Attendance.session_id != session_id,
        )
        .order_by(Attendance.submitted_at.desc())
        .first()
    )
    if previous_record is not None:
        prev_attendance, _prev_session = previous_record
        elapsed_hours = (
            submitted_at - prev_attendance.submitted_at
        ).total_seconds() / 3600.0
        if elapsed_hours > 0:
            distance_km = haversine_distance_m(
                latitude, longitude,
                prev_attendance.latitude, prev_attendance.longitude,
            ) / 1000.0
            required_speed_kmh = distance_km / elapsed_hours
            if required_speed_kmh > IMPLAUSIBLE_SPEED_KMH:
                score -= IMPOSSIBLE_TRAVEL_PENALTY
                reasons.append("IMPOSSIBLE_TRAVEL")

    score = max(0.0, min(100.0, score))
    flagged = score <= trust_threshold

    return AnomalyResult(trust_score=score, flagged=flagged, reasons=reasons)
