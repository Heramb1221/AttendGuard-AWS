# AttendGuard — Geofenced Attendance System with Real-Time Fraud Detection

## Project Description

AttendGuard is a web-based attendance management system built for university
classrooms. Unlike a conventional attendance app, it treats attendance
marking as a trust problem: every submission is validated against a
GPS geofence and scored by an anomaly detection engine that looks for the
signatures of proxy attendance (one student marking present for an absent
classmate).

## Problem Statement

Manual roll-call attendance is time-consuming, and simple digital
attendance apps that just record "student X tapped present" are trivially
gamed: a student can hand their phone to a friend, or a friend can log into
a QR-code attendance link and submit the location without being physically
present. Existing "smart attendance" tutorials rarely address this because
they trust the client-submitted data at face value.

## Why I Built This

As a Computer Engineering student, I wanted a capstone project that goes
beyond CRUD: something with a genuine algorithmic core (the anomaly
scoring engine) wrapped in a production-style cloud deployment pipeline,
demonstrating both software engineering and DevOps/AWS skills expected in
an SWE/Full-Stack role.

## Objectives

- Build a Flask web application with role-based access (faculty/student).
- Enforce location-based attendance validity using geofencing.
- Detect and flag patterns indicative of attendance fraud.
- Automate deployment end-to-end using AWS CodePipeline, CodeBuild, and
  CodeDeploy, so that every `git push` ships a tested build with zero
  manual server work.
- Stay within AWS Free Tier.

## Features

- **Role-based accounts**: faculty create courses/sessions, students mark
  attendance.
- **Geofenced sessions**: faculty define a classroom's GPS coordinates and
  an allowed radius; students outside that radius are rejected outright.
- **Anomaly detection engine** with three independent rules:
  - Duplicate device fingerprint used across different student accounts.
  - Near-identical GPS coordinates submitted by different students.
  - Impossible travel speed between a student's two most recent sessions.
- **Trust score (0-100)** attached to every attendance record, with
  automatic flagging below a configurable threshold.
- **Faculty review workflow** to approve/reject flagged records.
- **CSV report export** uploaded to S3 with a pre-signed, time-limited
  download link.
- **Fully automated CI/CD**: CodePipeline → CodeBuild (tests) → CodeDeploy
  (EC2) on every push to `main`.

## Architecture

```
GitHub --push--> CodePipeline --Source--> CodeBuild --Build/Test--> S3 (artifacts)
                                                                        │
                                                                        ▼
                                                              CodeDeploy --Deploy--> EC2 (Ubuntu, t3.micro)
                                                                                        │
                                                                    ┌───────────────────┼───────────────────┐
                                                                    ▼                   ▼                   ▼
                                                          RDS PostgreSQL      S3 (attendance reports)   CloudWatch (logs)
                                                          (db.t3.micro)
```

Nginx runs on the EC2 instance as a reverse proxy in front of gunicorn,
which serves the Flask application.

## AWS Services Used

| Service | Purpose |
|---|---|
| **CodePipeline** | Orchestrates the Source → Build → Deploy workflow |
| **S3** | (1) CodePipeline artifact storage, (2) exported attendance CSV reports |
| **CodeBuild** | Installs dependencies, runs the pytest suite, packages the build |
| **CodeDeploy** | Deploys the tested build to the EC2 instance via lifecycle hooks |
| **EC2** | Hosts the Flask app (Ubuntu 22.04, t3.micro, Free Tier) |
| **RDS (PostgreSQL)** | Persistent relational storage (db.t3.micro, Free Tier) |
| **IAM** | Scoped roles for EC2, CodeBuild, and CodePipeline |
| **CloudWatch** | Centralized application + system logs |

All optional services above were chosen because they directly support the
CI/CD requirement; no service was added just because it appeared on an
available-services list.

## Folder Structure

```
attendguard/
├── app/
│   ├── __init__.py            # Application factory
│   ├── config.py              # Environment-driven configuration
│   ├── extensions.py          # db, login_manager, migrate instances
│   ├── models/                # SQLAlchemy models
│   ├── routes/                # Flask blueprints (auth, faculty, student, api)
│   ├── services/               # Geofence, anomaly detection, S3, reports
│   ├── utils/                  # Validators, decorators, logging
│   ├── templates/              # Jinja2 + Bootstrap templates
│   └── static/                 # CSS and JS (geolocation, fingerprint)
├── sql/                        # Reference schema.sql / seed.sql
├── tests/                      # pytest unit tests
├── deployment/
│   ├── buildspec.yml           # CodeBuild spec
│   ├── appspec.yml             # CodeDeploy spec
│   ├── scripts/                # CodeDeploy lifecycle hooks
│   ├── nginx/                  # Nginx site config
│   ├── systemd/                # gunicorn systemd unit
│   ├── iam_policies/           # Reference IAM policy JSON documents
│   └── ec2_user_data.sh        # EC2 first-boot bootstrap script
├── scripts/
│   ├── aws_setup.sh            # Step-by-step AWS CLI provisioning reference
│   └── init_db.py              # Manual DB schema initialization
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── run.py                      # Local dev entry point
├── wsgi.py                     # Production (gunicorn) entry point
├── README.md
└── instructions.md
```

## Technology Stack

- **Backend**: Python 3.12, Flask 3, Flask-SQLAlchemy, Flask-Login, boto3
- **Frontend**: Server-rendered Jinja2 templates + Bootstrap 5
- **Database**: Amazon RDS (PostgreSQL)
- **Infrastructure**: AWS CodePipeline, CodeBuild, CodeDeploy, EC2, S3, IAM, CloudWatch
- **Testing**: pytest

## Installation (Local Development)

```bash
git clone <your-repo-url>
cd attendguard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# Edit .env: set SECRET_KEY at minimum. Leave DB_* blank to use local SQLite.
flask init-db
flask seed-db
python run.py
```

Visit `http://127.0.0.1:5000`. Demo accounts created by `flask seed-db`:
`faculty@example.edu` / `student@example.edu`, password `ChangeMe123!`.

## Configuration

All configuration lives in environment variables — see `.env.example` for
the full list (database credentials, AWS region, S3 bucket, geofence/
anomaly tuning). No secrets are hardcoded anywhere in the codebase.

## Deployment

Full step-by-step instructions are in **instructions.md**. Summary:

1. Provision RDS, S3 buckets, IAM roles, and an EC2 instance (`scripts/aws_setup.sh`).
2. Connect GitHub to CodeStar Connections.
3. Create a CodeBuild project referencing `deployment/buildspec.yml`.
4. Create a CodeDeploy application/deployment group targeting the EC2 instance.
5. Create a CodePipeline wiring Source → Build → Deploy together.
6. Push to `main` — the pipeline builds, tests, and deploys automatically.

## API Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/auth/register` | Create a faculty or student account | Public |
| POST | `/auth/login` | Log in | Public |
| GET | `/auth/logout` | Log out | Required |
| GET | `/faculty/dashboard` | List faculty's courses | Faculty |
| POST | `/faculty/courses/<id>/sessions/new` | Open a new attendance session | Faculty |
| GET | `/faculty/sessions/<id>` | View session attendance + trust scores | Faculty |
| POST | `/faculty/attendance/<id>/review` | Approve/reject a flagged record | Faculty |
| POST | `/faculty/sessions/<id>/export` | Export CSV report to S3 | Faculty |
| GET | `/student/dashboard` | List open sessions + attendance history | Student |
| GET | `/student/sessions/<id>/mark` | Attendance-marking page | Student |
| POST | `/api/attendance/submit` | Submit GPS + fingerprint for scoring (JSON) | Student |

---

## Application Screenshots

| Feature | Preview |
|----------|---------|
| Login Page | <img width="1917" height="862" alt="image" src="https://github.com/user-attachments/assets/ce0bc7ac-31f7-4803-9894-35fe20285797" /> |
| Faculty Dashboard | <img width="1917" height="862" alt="image" src="https://github.com/user-attachments/assets/c62f8c88-e214-4bdb-bace-951c819b0318" /> |
| Student Dashboard | <img width="1917" height="867" alt="image" src="https://github.com/user-attachments/assets/ddd114ae-b507-47a6-9f2c-4fe5a0944948" /> |
| Create Attendance Session | <img width="1897" height="862" alt="image" src="https://github.com/user-attachments/assets/1322a20c-e7b3-4b4a-9eae-efb59af979b8" /> |
| Attendance Marking | <img width="1917" height="870" alt="image" src="https://github.com/user-attachments/assets/cb4f263d-29b3-4500-907d-59515207e215" /> |
| Trust Score Analysis | <img width="1917" height="862" alt="image" src="https://github.com/user-attachments/assets/314049b0-197e-4671-bcec-527a98ffcf84" /> |
| Flagged Attendance Review | <img width="1917" height="850" alt="image" src="https://github.com/user-attachments/assets/cc793f60-0966-405c-8b86-e5d93eb7a463" /> |

---

## Challenges Faced

- Balancing false positives vs. false negatives in the anomaly engine —
  overly aggressive thresholds would flag legitimate students sitting near
  each other; the final design uses a small GPS-match epsilon (2m) and a
  short time window to reduce false positives.
- Structuring CodeDeploy lifecycle hooks so that a *first-ever* deployment
  (no existing service to stop) doesn't fail the pipeline.
- Keeping the entire architecture within AWS Free Tier limits while still
  demonstrating a realistic CI/CD pipeline.

## Future Improvements

- Wi-Fi BSSID validation as a second geofencing signal alongside GPS.
- Move from single EC2 instance to an Auto Scaling Group behind an ALB.
- Add Amazon SNS notifications to faculty when a session accumulates
  multiple flagged records in real time.
- Replace the lightweight JS fingerprint with a more robust, privacy-
  respecting device attestation mechanism.

## What I Learned

Building AttendGuard reinforced how to design a CI/CD pipeline around
CodePipeline/CodeBuild/CodeDeploy for a stateful application (as opposed to
a stateless Lambda), how to reason about trust and fraud signals in a
real-world system, and how to structure a Flask application for production
(application factory, blueprints, environment-driven config).

## Contact

**Heramb Chaudhari**

[![GitHub](https://img.shields.io/badge/GitHub-Heramb1221-black?style=for-the-badge&logo=github)](https://github.com/Heramb1221)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Heramb%20Chaudhari-blue?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/in/heramb-chaudhari)

[![Email](https://img.shields.io/badge/Email-hchaudhari1221%40gmail.com-red?style=for-the-badge&logo=gmail)](mailto:hchaudhari1221@gmail.com)
