"""Role-based access control decorators built on top of Flask-Login."""
from functools import wraps

from flask import abort
from flask_login import current_user


def role_required(*roles):
    """Restrict a view to users whose `role` is in `roles`.

    Usage:
        @role_required("faculty")
        def dashboard(): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator
