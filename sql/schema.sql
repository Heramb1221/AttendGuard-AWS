-- ============================================================
-- AttendGuard database schema (PostgreSQL / Amazon RDS)
--
-- This file is provided for reference and for manual review before
-- deployment. In normal operation the schema is created automatically by
-- SQLAlchemy via `flask init-db` (see app/__init__.py CLI commands), which
-- reads the models in app/models/*.py. This .sql file must stay in sync
-- with those models and can be used to provision the schema directly with
-- psql if you prefer not to run the Flask CLI.
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(120) NOT NULL,
    email           VARCHAR(150) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('faculty', 'student')),
    roll_number     VARCHAR(50) UNIQUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS courses (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    code        VARCHAR(30) UNIQUE NOT NULL,
    faculty_id  INTEGER NOT NULL REFERENCES users(id),
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS enrollments (
    student_id  INTEGER NOT NULL REFERENCES users(id),
    course_id   INTEGER NOT NULL REFERENCES courses(id),
    PRIMARY KEY (student_id, course_id)
);

CREATE TABLE IF NOT EXISTS attendance_sessions (
    id                SERIAL PRIMARY KEY,
    course_id         INTEGER NOT NULL REFERENCES courses(id),
    title             VARCHAR(150) NOT NULL,
    center_latitude   DOUBLE PRECISION NOT NULL,
    center_longitude  DOUBLE PRECISION NOT NULL,
    radius_meters     DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    opens_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    closes_at         TIMESTAMP NOT NULL,
    created_at        TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS attendance (
    id                       SERIAL PRIMARY KEY,
    session_id               INTEGER NOT NULL REFERENCES attendance_sessions(id),
    student_id               INTEGER NOT NULL REFERENCES users(id),
    latitude                 DOUBLE PRECISION NOT NULL,
    longitude                DOUBLE PRECISION NOT NULL,
    distance_from_center_m   DOUBLE PRECISION NOT NULL,
    device_fingerprint       VARCHAR(128) NOT NULL,
    ip_address               VARCHAR(64),
    submitted_at             TIMESTAMP NOT NULL DEFAULT NOW(),
    within_geofence          BOOLEAN NOT NULL DEFAULT FALSE,
    trust_score              DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    flagged                  BOOLEAN NOT NULL DEFAULT FALSE,
    flag_reasons             TEXT,
    reviewed                 BOOLEAN NOT NULL DEFAULT FALSE,
    review_decision          VARCHAR(20),
    CONSTRAINT uq_session_student UNIQUE (session_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_attendance_device_fp ON attendance(device_fingerprint);
CREATE INDEX IF NOT EXISTS idx_attendance_submitted_at ON attendance(submitted_at);
