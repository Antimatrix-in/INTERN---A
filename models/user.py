from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .database import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='CANDIDATE', index=True) # 'ADMIN' or 'CANDIDATE'
    full_name = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    source_system = db.Column(db.String(50), default='antimatrix_db', nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    credential = db.relationship('Credential', back_populates='candidate', uselist=False, cascade='all, delete-orphan')
    attempts = db.relationship('Attempt', back_populates='candidate', cascade='all, delete-orphan')
    results = db.relationship('Result', back_populates='candidate', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set user password securely."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against stored hash."""
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'ADMIN'

    @property
    def is_candidate(self):
        return self.role == 'CANDIDATE'

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
