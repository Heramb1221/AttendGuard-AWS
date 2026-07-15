"""
Generates CSV attendance reports for a session or course and hands them off
to S3ReportService for storage + pre-signed URL retrieval.
"""
import csv
import io
import os
import tempfile
from datetime import datetime

from flask import current_app

from app.services.s3_service import S3ReportService
from app.utils.logger import get_logger

logger = get_logger("report_service")


def _build_csv(rows, header):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def generate_session_report(session) -> str:
    """
    Build a CSV report for a single AttendanceSession, upload it to S3, and
    return a pre-signed download URL.
    """
    header = [
        "Student Name", "Roll Number", "Status", "Trust Score",
        "Distance (m)", "Submitted At (UTC)", "Flag Reasons",
    ]
    rows = []
    for record in session.attendance_records:
        rows.append([
            record.student.name,
            record.student.roll_number or "-",
            record.status_label(),
            f"{record.trust_score:.1f}",
            f"{record.distance_from_center_m:.1f}",
            record.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
            record.flag_reasons or "-",
        ])

    csv_content = _build_csv(rows, header)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    filename = f"session_{session.id}_{timestamp}.csv"
    s3_key = f"reports/course_{session.course_id}/{filename}"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        service = S3ReportService(
            bucket_name=current_app.config["S3_REPORTS_BUCKET"],
            region_name=current_app.config["AWS_REGION"],
        )
        service.upload_report(tmp_path, s3_key)
        url = service.generate_download_url(s3_key)
        return url
    finally:
        os.remove(tmp_path)
