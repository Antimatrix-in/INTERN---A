from functools import wraps
import os
import secrets
import string
from flask import abort, redirect, url_for, flash, request
from flask_login import current_user
from models import db, User

def admin_required(f):
    """Decorator to enforce admin-only access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_admin:
            flash("Access denied: Administrator privileges required.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def candidate_required(f):
    """Decorator to enforce candidate-only access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_candidate:
            flash("Access denied: Candidate portal is for assessment candidates only.", "warning")
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def create_initial_admin(username=None, email=None, password=None, full_name=None):
    """
    Creates the initial admin account securely using environment variables or passed parameters.
    Never hardcodes production credentials.
    """
    admin_username = username or os.environ.get('ADMIN_USERNAME', 'admin')
    admin_email = email or os.environ.get('ADMIN_EMAIL', 'admin@antimatrix.local')
    admin_password = password or os.environ.get('ADMIN_PASSWORD')
    admin_fullname = full_name or os.environ.get('ADMIN_FULL_NAME', 'Anti-Matrix Administrator')

    if not admin_password:
        # Generate a secure random password if none was supplied
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        admin_password = ''.join(secrets.choice(alphabet) for _ in range(16))
        print(f"Generated secure temporary admin password: {admin_password}")

    # Check if admin already exists
    existing = User.query.filter((User.username == admin_username) | (User.email == admin_email)).first()
    if existing:
        return existing, False, None

    admin_user = User(
        user_id="AM-ADMIN-001",
        username=admin_username,
        email=admin_email,
        full_name=admin_fullname,
        role='ADMIN',
        is_active=True
    )
    admin_user.set_password(admin_password)

    db.session.add(admin_user)
    db.session.commit()
    return admin_user, True, admin_password
