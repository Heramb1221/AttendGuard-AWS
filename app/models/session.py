"""
AttendanceSession model — represents one lecture instance for which faculty
opens a geofenced attendance window.
"""
from datetime import datetime

from app.extensions import db


class AttendanceSession(db.Model):
    __tablename__ = "attendance_sessions"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    course = db.relationship("Course", back_populates="sessions")

    title = db.Column(db.String(150), nullable=False)

    # Geofence center point (classroom / hall location) and allowed radius.
    center_latitude = db.Column(db.Float, nullable=False)
    center_longitude = db.Column(db.Float, nullable=False)
    radius_meters = db.Column(db.Float, nullable=False, default=100.0)

    # Attendance can only be marked between opens_at and closes_at.
    opens_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    closes_at = db.Column(db.DateTime, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    attendance_records = db.relationship(
        "Attendance", back_populates="session", cascade="all, delete-orphan"
    )

    def is_open(self, at_time: datetime = None) -> bool:
        at_time = at_time or datetime.utcnow()
        return self.opens_at <= at_time <= self.closes_at

    def __repr__(self):
        return f"<AttendanceSession {self.title} ({self.course.code if self.course else '?'})>"
