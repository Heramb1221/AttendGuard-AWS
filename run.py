"""
Local development entry point.

Usage:
    python run.py

This runs Flask's built-in development server. It is NOT used in production;
production uses gunicorn via wsgi.py (see deployment/scripts/application_start.sh).
"""
import os
from app import create_app

app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_ENV", "development") == "development"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
