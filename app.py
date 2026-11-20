import os
import click
from datetime import datetime, timezone
from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_migrate import Migrate

from config import config_by_name
from models import db, User, Assessment, Question, Credential, Attempt, AttemptAnswer, Result, ProctoringEvent
from routes import auth_bp, admin_bp, candidate_bp
from services import create_initial_admin

login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

def create_app(config_name=None):
    """Application factory for ANTI-MATRIX Assessment Platform."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Please sign in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(candidate_bp)

    # Global Template Context Processor
    @app.context_processor
    def inject_global_vars():
        return {
            'now_year': datetime.now(timezone.utc).year,
            'platform_name': 'ANTI-MATRIX',
            'platform_version': '1.0.0 (Phase 1)'
        }

    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash("Your session or security token has expired. Please try again.", "danger")
        return redirect(url_for('auth.login'))

    # CLI Commands
    @app.cli.command("create-admin")
    @click.option("--username", default=None, help="Admin username")
    @click.option("--email", default=None, help="Admin email")
    @click.option("--password", default=None, help="Admin password")
    @click.option("--fullname", default=None, help="Admin full name")
    def create_admin_command(username, email, password, fullname):
        """Creates the initial admin account securely via CLI or environment."""
        with app.app_context():
            user, created, raw_pwd = create_initial_admin(
                username=username,
                email=email,
                password=password,
                full_name=fullname
            )
            if created:
                click.secho(f"Admin account created successfully!", fg="green", bold=True)
                click.echo(f"  User ID : {user.user_id}")
                click.echo(f"  Username: {user.username}")
                click.echo(f"  Email   : {user.email}")
                click.echo(f"  Password: {raw_pwd}")
            else:
                click.secho(f"Admin user '{user.username}' already exists.", fg="yellow")

    @app.cli.command("init-db")
    def init_db_command():
        """Creates database tables and default admin if missing."""
        with app.app_context():
            db.create_all()
            click.secho("Database tables verified / created.", fg="green")
            user, created, raw_pwd = create_initial_admin()
            if created:
                click.secho("Initial administrator account seeded from environment variables.", fg="cyan")

    return app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_initial_admin()
    app.run(host='0.0.0.0', port=5000, debug=True)
