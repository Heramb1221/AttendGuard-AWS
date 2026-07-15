"""Authentication routes: registration and login/logout for both roles."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models.user import User
from app.utils.validators import is_valid_email, is_valid_roll_number, sanitize_text
from app.utils.logger import get_logger

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
logger = get_logger("routes.auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        name = sanitize_text(request.form.get("name"), 120)
        email = sanitize_text(request.form.get("email"), 150).lower()
        password = request.form.get("password") or ""
        role = request.form.get("role")
        roll_number = sanitize_text(request.form.get("roll_number"), 50) or None

        errors = []
        if not name:
            errors.append("Name is required.")
        if not is_valid_email(email):
            errors.append("A valid email is required.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        if role not in ("faculty", "student"):
            errors.append("Please select a valid role.")
        if role == "student":
            if not roll_number or not is_valid_roll_number(roll_number):
                errors.append("A valid roll number is required for students.")
        if User.query.filter_by(email=email).first():
            errors.append("An account with that email already exists.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("auth/register.html", form_data=request.form)

        user = User(name=name, email=email, role=role,
                    roll_number=roll_number if role == "student" else None)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        logger.info("New %s registered: %s", role, email)
        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form_data={})


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = sanitize_text(request.form.get("email"), 150).lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")

        login_user(user)
        logger.info("User logged in: %s", email)

        if user.role == "faculty":
            return redirect(url_for("faculty.dashboard"))
        return redirect(url_for("student.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logger.info("User logged out: %s", current_user.email)
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
