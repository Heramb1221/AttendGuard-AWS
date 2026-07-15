"""
JSON API blueprint. Currently exposes a single endpoint: submitting an
attendance record from the browser (GPS + device fingerprint captured by
app/static/js/geolocation.js and fingerprint.js).
"""
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.models.session import AttendanceSession
from app.models.attendance import Attendance
from app.services.geofence import check_within_geofence
from app.services import anomaly
from app.utils.decorators import role_required
from app.utils.validators import is_valid_latitude, is_valid_longitude, sanitize_text
from app.utils.logger import get_logger

api_bp = Blueprint("api", __name__)
logger = get_logger("routes.api")


@api_bp.route("/attendance/submit", methods=["POST"])
@login_required
@role_required("student")
def submit_attendance():
    payload = request.get_json(silent=True) or {}

    session_id = payload.get("session_id")
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    device_fingerprint = sanitize_text(payload.get("device_fingerprint"), 128)

    # ---- Input validation ----
    if not session_id:
        return jsonify(error="session_id is required"), 400
    if not is_valid_latitude(latitude):
        return jsonify(error="A valid latitude is required"), 400
    if not is_valid_longitude(longitude):
        return jsonify(error="A valid longitude is required"), 400
    if not device_fingerprint:
        return jsonify(error="device_fingerprint is required"), 400

    session = db.session.get(AttendanceSession, session_id)
    if session is None:
        return jsonify(error="Attendance session not found"), 404

    if session.course not in current_user.enrolled_courses:
        return jsonify(error="You are not enrolled in this course"), 403

    if not session.is_open():
        return jsonify(error="This attendance session is closed"), 409

    existing = Attendance.query.filter_by(
        session_id=session.id, student_id=current_user.id
    ).first()
    if existing is not None:
        return jsonify(error="Attendance already marked for this session"), 409

    latitude = float(latitude)
    longitude = float(longitude)

    within_geofence, distance_m = check_within_geofence(
        latitude, longitude,
        session.center_latitude, session.center_longitude,
        session.radius_meters,
    )

    submitted_at = datetime.utcnow()

    if not within_geofence:
        record = Attendance(
            session_id=session.id,
            student_id=current_user.id,
            latitude=latitude,
            longitude=longitude,
            distance_from_center_m=distance_m,
            device_fingerprint=device_fingerprint,
            ip_address=request.remote_addr,
            submitted_at=submitted_at,
            within_geofence=False,
            trust_score=0.0,
            flagged=True,
            flag_reasons="OUTSIDE_GEOFENCE",
        )
        db.session.add(record)
        db.session.commit()
        logger.warning(
            "Rejected attendance for student %s: %.1fm outside %.1fm radius",
            current_user.id, distance_m, session.radius_meters,
        )
        return jsonify(
            error=f"You are {distance_m:.0f}m from the classroom, outside the "
                  f"{session.radius_meters:.0f}m allowed radius.",
            status="rejected",
        ), 422

    result = anomaly.evaluate(
        student_id=current_user.id,
        session_id=session.id,
        course_id=session.course_id,
        latitude=latitude,
        longitude=longitude,
        device_fingerprint=device_fingerprint,
        submitted_at=submitted_at,
        window_seconds=current_app.config["ANOMALY_WINDOW_SECONDS"],
        trust_threshold=current_app.config["ANOMALY_TRUST_THRESHOLD"],
        db_session=db.session,
    )

    record = Attendance(
        session_id=session.id,
        student_id=current_user.id,
        latitude=latitude,
        longitude=longitude,
        distance_from_center_m=distance_m,
        device_fingerprint=device_fingerprint,
        ip_address=request.remote_addr,
        submitted_at=submitted_at,
        within_geofence=True,
        trust_score=result.trust_score,
        flagged=result.flagged,
        flag_reasons=",".join(result.reasons) if result.reasons else None,
    )
    db.session.add(record)
    db.session.commit()

    if result.flagged:
        logger.warning(
            "Flagged attendance for student %s in session %s: score=%.1f reasons=%s",
            current_user.id, session.id, result.trust_score, result.reasons,
        )
    else:
        logger.info(
            "Attendance recorded for student %s in session %s: score=%.1f",
            current_user.id, session.id, result.trust_score,
        )

    return jsonify(
        status="flagged" if result.flagged else "present",
        trust_score=result.trust_score,
        distance_m=round(distance_m, 1),
    ), 201
