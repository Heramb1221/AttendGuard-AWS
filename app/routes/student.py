"""
Student-facing routes: dashboard of enrolled courses/open sessions, and the
attendance-marking page (the actual geofence + fingerprint submission form
posts to the API blueprint, not here).
"""
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.models.session import AttendanceSession
from app.models.attendance import Attendance
from app.utils.decorators import role_required

student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.route("/dashboard")
@login_required
@role_required("student")
def dashboard():
    now = datetime.utcnow()
    enrolled_course_ids = [c.id for c in current_user.enrolled_courses]

    open_sessions = (
        AttendanceSession.query
        .filter(
            AttendanceSession.course_id.in_(enrolled_course_ids),
            AttendanceSession.opens_at <= now,
            AttendanceSession.closes_at >= now,
        )
        .all()
    )

    already_marked_ids = {
        record.session_id for record in
        Attendance.query.filter_by(student_id=current_user.id).all()
    }

    past_records = (
        Attendance.query
        .filter_by(student_id=current_user.id)
        .order_by(Attendance.submitted_at.desc())
        .limit(20)
        .all()
    )

    return render_template(
        "student/dashboard.html",
        open_sessions=open_sessions,
        already_marked_ids=already_marked_ids,
        past_records=past_records,
    )


@student_bp.route("/sessions/<int:session_id>/mark")
@login_required
@role_required("student")
def mark_attendance(session_id):
    session = AttendanceSession.query.get_or_404(session_id)

    if session.course not in current_user.enrolled_courses:
        flash("You are not enrolled in this course.", "danger")
        return redirect(url_for("student.dashboard"))

    if not session.is_open():
        flash("This attendance session is not currently open.", "warning")
        return redirect(url_for("student.dashboard"))

    existing = Attendance.query.filter_by(
        session_id=session.id, student_id=current_user.id
    ).first()
    if existing:
        flash("You have already marked attendance for this session.", "info")
        return redirect(url_for("student.dashboard"))

    return render_template("student/mark_attendance.html", session=session)
