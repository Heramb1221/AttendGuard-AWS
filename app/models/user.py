"""
User model. A single table serves both faculty and student roles,
distinguished by the `role` column, since both share the same auth flow.
"""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'faculty' or 'student'

    # Only populated for students; used to identify them on attendance sheets.
    roll_number = db.Column(db.String(50), unique=True, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    courses_taught = db.relationship(
        "Course", back_populates="faculty", foreign_keys="Course.faculty_id"
    )
    attendance_records = db.relationship(
        "Attendance", back_populates="student", foreign_keys="Attendance.student_id"
    )

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def is_faculty(self) -> bool:
        return self.role == "faculty"

    def is_student(self) -> bool:
        return self.role == "student"

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
