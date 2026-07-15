"""
One-off script to initialize the database schema against a real RDS
instance (as an alternative to `flask init-db`). Reads connection details
from environment variables (.env), same as the main app.

Usage:
    python scripts/init_db.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db


def main():
    app = create_app(os.getenv("FLASK_ENV", "production"))
    with app.app_context():
        db.create_all()
        print("Database tables created successfully at:")
        print(f"  {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]}")


if __name__ == "__main__":
    main()
