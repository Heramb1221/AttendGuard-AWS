"""
Unit tests for the anomaly detection engine. Exercises each rule
(duplicate device, duplicate GPS, impossible travel) in isolation using an
in-memory SQLite database (see tests/conftest.py).
"""
from datetime import datetime, timedelta

from app.extensions import db as _db
from app.models.user import User
from app.models.course import Course
from app.models.session import AttendanceSession
from app.models.attendance import Attendance
from app.services import anomaly


def _make_faculty_and_course(db):
    faculty = User(name="Dr. Test", email="fac@example.edu", role="faculty")
    faculty.set_password("password123")
    db.session.add(faculty)
    db.session.flush()

    course = Course(name="Test Course", code="TC101", faculty_id=faculty.id)
    db.session.add(course)
    db.session.flush()
    return course


def _make_session(db, course, minutes_ago=5):
    now = datetime.utcnow()
    session = AttendanceSession(
        course_id=course.id,
        title="Test Session",
        center_latitude=19.0760,
        center_longitude=72.8777,
        radius_meters=100,
        opens_at=now - timedelta(minutes=minutes_ago),
        closes_at=now + timedelta(minutes=30),
    )
    db.session.add(session)
    db.session.flush()
    return session


def _make_student(db, email):
    student = User(name="Student " + email, email=email, role="student",
                    roll_number=email.split("@")[0])
    student.set_password("password123")
    db.session.add(student)
    db.session.flush()
    return student


def test_no_anomalies_for_first_clean_submission(app, db):
    with app.app_context():
        course = _make_faculty_and_course(db)
        session = _make_session(db, course)
        student = _make_student(db, "s1@example.edu")

        result = anomaly.evaluate(
            student_id=student.id, session_id=session.id, course_id=course.id,
            latitude=19.0760, longitude=72.8777,
            device_fingerprint="device-A",
            submitted_at=datetime.utcnow(),
            window_seconds=60, trust_threshold=50,
            db_session=db.session,
        )
        assert result.trust_score == 100.0
        assert result.flagged is False
        assert result.reasons == []


def test_duplicate_device_flagged(app, db):
    with app.app_context():
        course = _make_faculty_and_course(db)
        session = _make_session(db, course)
        student1 = _make_student(db, "s1@example.edu")
        student2 = _make_student(db, "s2@example.edu")

        now = datetime.utcnow()

        record1 = Attendance(
            session_id=session.id, student_id=student1.id,
            latitude=19.0760, longitude=72.8777, distance_from_center_m=5,
            device_fingerprint="shared-device", submitted_at=now,
            within_geofence=True, trust_score=100,
        )
        db.session.add(record1)
        db.session.commit()

        result = anomaly.evaluate(
            student_id=student2.id, session_id=session.id, course_id=course.id,
            latitude=19.0761, longitude=72.8778,
            device_fingerprint="shared-device",
            submitted_at=now + timedelta(seconds=10),
            window_seconds=60, trust_threshold=50,
            db_session=db.session,
        )
        assert "DUPLICATE_DEVICE" in result.reasons
        assert result.trust_score <= 40
        assert result.flagged is True


def test_duplicate_gps_flagged(app, db):
    with app.app_context():
        course = _make_faculty_and_course(db)
        session = _make_session(db, course)
        student1 = _make_student(db, "s1@example.edu")
        student2 = _make_student(db, "s2@example.edu")

        now = datetime.utcnow()

        record1 = Attendance(
            session_id=session.id, student_id=student1.id,
            latitude=19.076000, longitude=72.877700, distance_from_center_m=5,
            device_fingerprint="device-A", submitted_at=now,
            within_geofence=True, trust_score=100,
        )
        db.session.add(record1)
        db.session.commit()

        result = anomaly.evaluate(
            student_id=student2.id, session_id=session.id, course_id=course.id,
            latitude=19.076000, longitude=72.877701,  # ~0.1m away
            device_fingerprint="device-B",
            submitted_at=now + timedelta(seconds=5),
            window_seconds=60, trust_threshold=50,
            db_session=db.session,
        )
        assert "DUPLICATE_GPS" in result.reasons
        assert result.flagged is True


def test_impossible_travel_flagged(app, db):
    with app.app_context():
        course = _make_faculty_and_course(db)
        session1 = _make_session(db, course)
        session2 = _make_session(db, course)
        student = _make_student(db, "s1@example.edu")

        now = datetime.utcnow()

        # First record: Mumbai coordinates
        record1 = Attendance(
            session_id=session1.id, student_id=student.id,
            latitude=19.0760, longitude=72.8777, distance_from_center_m=5,
            device_fingerprint="device-A", submitted_at=now,
            within_geofence=True, trust_score=100,
        )
        db.session.add(record1)
        db.session.commit()

        # Second record 2 minutes later: Delhi coordinates (~1150km away) —
        # physically impossible to travel in 2 minutes.
        result = anomaly.evaluate(
            student_id=student.id, session_id=session2.id, course_id=course.id,
            latitude=28.7041, longitude=77.1025,
            device_fingerprint="device-A",
            submitted_at=now + timedelta(minutes=2),
            window_seconds=60, trust_threshold=50,
            db_session=db.session,
        )
        assert "IMPOSSIBLE_TRAVEL" in result.reasons
        assert result.flagged is True
