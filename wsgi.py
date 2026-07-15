"""
WSGI entry point used by gunicorn in production.

Gunicorn is invoked as:
    gunicorn -w 3 -b 127.0.0.1:8000 wsgi:app

See deployment/scripts/application_start.sh for the exact production command
and deployment/systemd/attendguard.service for how it's supervised.
"""
import os
from app import create_app

app = create_app(os.getenv("FLASK_ENV", "production"))
