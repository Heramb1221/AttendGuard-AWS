"""
Faculty-facing routes: create courses/sessions, view live attendance with
trust scores, review flagged records, and export CSV reports to S3.
"""
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models.course import Course
from app.models.session import AttendanceSession
from app.models.attendance import Attendance
from app.utils.decorators import role_required
from app.utils.validators import (
    is_valid_latitude, is_valid_longitude, is_valid_radius, sanitize_text,
)
from app.services.report_service import generate_session_report
from app.utils.logger import get_logger

faculty_bp = Blueprint("faculty", __name__, url_prefix="/faculty")
logger = get_logger("routes.faculty")


@faculty_bp.route("/dashboard")
@login_required
@role_required("faculty")
def dashboard():
    courses = Course.query.filter_by(faculty_id=current_user.id).all()
    return render_template("faculty/dashboard.html", courses=courses)


@faculty_bp.route("/courses/<int:course_id>/sessions/new", methods=["GET", "POST"])
@login_required
@role_required("faculty")
def create_session(course_id):
    course = Course.query.get_or_404(course_id)
    if course.faculty_id != current_user.id:
        flash("You do not have permission to manage this course.", "danger")
        return redirect(url_for("faculty.dashboard"))

    if request.method == "POST":
        title = sanitize_text(request.form.get("title"), 150)
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        radius = request.form.get("radius_meters") or "100"
        duration_minutes = request.form.get("duration_minutes") or "10"

        errors = []
        if not title:
            errors.append("Session title is required.")
        if not is_valid_latitude(latitude):
            errors.append("A valid classroom latitude is required.")
        if not is_valid_longitude(longitude):
            errors.append("A valid classroom longitude is required.")
        if not is_valid_radius(radius):
            errors.append("Radius must be a positive number of meters (max 5000).")
        try:
            duration_minutes = int(duration_minutes)
            if duration_minutes <= 0 or duration_minutes > 240:
                raise ValueError
        except ValueError:
            errors.append("Duration must be a whole number of minutes (1-240).")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("faculty/create_session.html", course=course)

        opens_at = datetime.utcnow()
        session = AttendanceSession(
            course_id=course.id,
            title=title,
            center_latitude=float(latitude),
            center_longitude=float(longitude),
            radius_meters=float(radius),
            opens_at=opens_at,
            closes_at=opens_at + timedelta(minutes=duration_minutes),
        )
        db.session.add(session)
        db.session.commit()

        logger.info("Session '%s' created for course %s", title, course.code)
        flash("Attendance session created and now open.", "success")
        return redirect(url_for("faculty.session_detail", session_id=session.id))

    return render_template("faculty/create_session.html", course=course)


@faculty_bp.route("/sessions/<int:session_id>")
@login_required
@role_required("faculty")
def session_detail(session_id):
    session = AttendanceSession.query.get_or_404(session_id)
    if session.course.faculty_id != current_user.id:
        flash("You do not have permission to view this session.", "danger")
        return redirect(url_for("faculty.dashboard"))

    records = (
        Attendance.query
        .filter_by(session_id=session.id)
        .order_by(Attendance.submitted_at.desc())
        .all()
    )
    flagged_count = sum(1 for r in records if r.flagged and not r.reviewed)
    return render_template(
        "faculty/session_detail.html",
        session=session, records=records, flagged_count=flagged_count,
    )


@faculty_bp.route("/attendance/<int:attendance_id>/review", methods=["POST"])
@login_required
@role_required("faculty")
def review_attendance(attendance_id):
    record = Attendance.query.get_or_404(attendance_id)
    if record.session.course.faculty_id != current_user.id:
        flash("You do not have permission to review this record.", "danger")
        return redirect(url_for("faculty.dashboard"))

    decision = request.form.get("decision")
    if decision not in ("approved", "rejected"):
        flash("Invalid review decision.", "danger")
        return redirect(url_for("faculty.session_detail", session_id=record.session_id))

    record.reviewed = True
    record.review_decision = decision
    db.session.commit()

    logger.info("Attendance %s reviewed as %s by %s",
                attendance_id, decision, current_user.email)
    flash(f"Record marked as {decision}.", "success")
    return redirect(url_for("faculty.session_detail", session_id=record.session_id))


@faculty_bp.route("/sessions/<int:session_id>/export", methods=["POST"])
@login_required
@role_required("faculty")
def export_report(session_id):
    session = AttendanceSession.query.get_or_404(session_id)
    if session.course.faculty_id != current_user.id:
        flash("You do not have permission to export this session.", "danger")
        return redirect(url_for("faculty.dashboard"))

    try:
        download_url = generate_session_report(session)
        flash("Report generated. Your download link is ready below.", "success")
        return render_template(
            "faculty/session_detail.html",
            session=session,
            records=session.attendance_records,
            flagged_count=sum(1 for r in session.attendance_records
                               if r.flagged and not r.reviewed),
            download_url=download_url,
        )
    except Exception:
        logger.exception("Failed to export report for session %s", session_id)
        flash(
            "Report export failed. Check that S3_REPORTS_BUCKET is configured "
            "and the server's IAM role has s3:PutObject permission.",
            "danger",
        )
        return redirect(url_for("faculty.session_detail", session_id=session_id))
