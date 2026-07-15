"""Course model — a subject taught by one faculty member, enrolling students."""
from datetime import datetime

from app.extensions import db

# Association table for many-to-many enrollment of students in courses.
enrollments = db.Table(
    "enrollments",
    db.Column("student_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("course_id", db.Integer, db.ForeignKey("courses.id"), primary_key=True),
)


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)

    faculty_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    faculty = db.relationship(
        "User", back_populates="courses_taught", foreign_keys=[faculty_id]
    )

    students = db.relationship(
        "User", secondary=enrollments, backref=db.backref("enrolled_courses", lazy="dynamic")
    )

    sessions = db.relationship("AttendanceSession", back_populates="course",
                                cascade="all, delete-orphan")

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Course {self.code}: {self.name}>"
