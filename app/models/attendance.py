"""
Attendance model — one row per student check-in, carrying both the raw
signal data (GPS, device fingerprint) and the computed trust score used by
the anomaly detection engine.
"""
from datetime import datetime

from app.extensions import db


class Attendance(db.Model):
    __tablename__ = "attendance"
    __table_args__ = (
        db.UniqueConstraint("session_id", "student_id", name="uq_session_student"),
    )

    id = db.Column(db.Integer, primary_key=True)

    session_id = db.Column(db.Integer, db.ForeignKey("attendance_sessions.id"), nullable=False)
    session = db.relationship("AttendanceSession", back_populates="attendance_records")

    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    student = db.relationship("User", back_populates="attendance_records",
                               foreign_keys=[student_id])

    # Raw signals captured at submission time.
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    distance_from_center_m = db.Column(db.Float, nullable=False)
    device_fingerprint = db.Column(db.String(128), nullable=False, index=True)
    ip_address = db.Column(db.String(64), nullable=True)

    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Result of geofence check.
    within_geofence = db.Column(db.Boolean, nullable=False, default=False)

    # Anomaly engine output.
    trust_score = db.Column(db.Float, nullable=False, default=100.0)
    flagged = db.Column(db.Boolean, nullable=False, default=False)
    flag_reasons = db.Column(db.Text, nullable=True)  # comma-separated reason codes

    # Faculty review outcome (nullable until reviewed).
    reviewed = db.Column(db.Boolean, nullable=False, default=False)
    review_decision = db.Column(db.String(20), nullable=True)  # 'approved' / 'rejected'

    def status_label(self) -> str:
        if not self.within_geofence:
            return "Rejected (outside geofence)"
        if self.flagged and not self.reviewed:
            return "Flagged - pending review"
        if self.flagged and self.reviewed:
            return f"Flagged - {self.review_decision}"
        return "Present"

    def __repr__(self):
        return f"<Attendance student={self.student_id} session={self.session_id} trust={self.trust_score}>"
