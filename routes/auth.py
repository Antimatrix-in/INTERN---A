from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    """Root redirect according to role or login."""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_candidate:
            return redirect(url_for('candidate.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Professional login page for ANTI-MATRIX platform.
    Handles both Admin and Candidate logins with role-based routing.
    """
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('candidate.dashboard'))

    if request.method == 'POST':
        login_identifier = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember_me'))

        if not login_identifier:
            flash("Username or Candidate User ID is required.", "danger")
            return render_template('auth/login.html')

        if not password:
            flash("Password is required.", "danger")
            return render_template('auth/login.html', username=login_identifier)

        # Allow login via username, email, or candidate user_id
        user = User.query.filter(
            (User.username == login_identifier) |
            (User.username == login_identifier.lower()) |
            (User.email == login_identifier.lower()) |
            (User.user_id == login_identifier.upper())
        ).first()

        if not user or not user.check_password(password):
            flash("Invalid credentials. Please verify your User ID/username and password.", "danger")
            return render_template('auth/login.html', username=login_identifier)

        if not user.is_active:
            flash("Your account has been deactivated. Please contact the administrator.", "danger")
            return render_template('auth/login.html')

        # Update last login timestamp
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()

        # Log in the user
        login_user(user, remember=remember)

        # Role-based redirection
        next_page = request.args.get('next')

        if user.is_admin:
            flash(f"Welcome back, {user.full_name}!", "success")
            if next_page and next_page.startswith('/admin'):
                return redirect(next_page)
            return redirect(url_for('admin.dashboard'))

        elif user.is_candidate:
            flash(f"Welcome, {user.full_name}. You are logged into the Candidate Assessment Portal.", "info")
            if next_page and next_page.startswith('/candidate'):
                return redirect(next_page)
            return redirect(url_for('candidate.dashboard'))

        else:
            flash("Unknown user role. Please contact support.", "danger")
            logout_user()
            return redirect(url_for('auth.login'))

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Secure logout."""
    logout_user()
    flash("You have been successfully logged out of ANTI-MATRIX.", "info")
    return redirect(url_for('auth.login'))
