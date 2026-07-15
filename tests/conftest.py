"""Shared pytest fixtures for AttendGuard tests."""
import os
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from app import create_app
from app.extensions import db as _db


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    return _db
