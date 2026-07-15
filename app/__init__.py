"""
Application factory for AttendGuard.

Using the factory pattern keeps configuration testable (see tests/conftest.py,
which builds the app with TestingConfig) and avoids import-time side effects.
"""
import logging
import os

from flask import Flask, render_template

from app.config import CONFIG_MAP
from app.extensions import db, login_manager, migrate


def create_app(env_name: str = "production") -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    config_class = CONFIG_MAP.get(env_name, CONFIG_MAP["production"])
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)

    _configure_logging(app)
    _register_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_cli_commands(app)

    return app


def _configure_logging(app: Flask) -> None:
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app.logger.setLevel(log_level)


def _register_extensions(app: Flask) -> None:
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))


def _register_blueprints(app: Flask) -> None:
    from app.routes.auth import auth_bp
    from app.routes.faculty import faculty_bp
    from app.routes.student import student_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.route("/")
    def index():
        from flask import redirect, url_for
        from flask_login import current_user

        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.role == "faculty":
            return redirect(url_for("faculty.dashboard"))
        return redirect(url_for("student.dashboard"))


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception("Unhandled server error: %s", error)
        return render_template("errors/500.html"), 500


def _register_cli_commands(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db():
        """Create all database tables. Usage: flask init-db"""
        db.create_all()
        print("Database tables created.")

    @app.cli.command("seed-db")
    def seed_db():
        """Insert demo faculty/student/course data. Usage: flask seed-db"""
        from app.models.user import User
        from app.models.course import Course

        if User.query.filter_by(email="faculty@example.edu").first():
            print("Seed data already present, skipping.")
            return

        faculty = User(
            name="Dr. Ananya Kulkarni",
            email="faculty@example.edu",
            role="faculty",
        )
        faculty.set_password("ChangeMe123!")

        student = User(
            name="Rohan Deshmukh",
            email="student@example.edu",
            role="student",
            roll_number="RCPIT2023CO045",
        )
        student.set_password("ChangeMe123!")

        course = Course(
            name="Cloud Computing Fundamentals",
            code="CS401",
            faculty=faculty,
        )

        db.session.add_all([faculty, student, course])
        db.session.commit()
        print("Seed data inserted: faculty@example.edu / student@example.edu "
              "(password: ChangeMe123!)")
