from datetime import datetime, timezone, timedelta
from .database import db

class Credential(db.Model):
    __tablename__ = 'credentials'

    id = db.Column(db.Integer, primary_key=True)
    credential_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='ACTIVE', index=True) # ACTIVE, USED, EXPIRED, DISABLED
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    candidate = db.relationship('User', back_populates='credential')
    assessment = db.relationship('Assessment', back_populates='credentials')
    attempt = db.relationship('Attempt', back_populates='credential', uselist=False, cascade='all, delete-orphan')

    @property
    def is_expired(self):
        """Check if credential has passed its strict 48-hour lifetime."""
        now = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp is None:
            return False
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now >= exp

    @property
    def effective_status(self):
        """Dynamic status calculation taking time into account."""
        if self.status == 'DISABLED':
            return 'DISABLED'
        if self.attempt:
            return 'USED'
        if self.is_expired:
            return 'EXPIRED'
        return self.status

    @property
    def is_valid_for_new_attempt(self):
        """Returns True if the credential can be used to start a new attempt."""
        return (self.effective_status == 'ACTIVE' and not self.attempt and not self.is_expired)

    @property
    def seconds_remaining(self):
        """Seconds remaining before credential expires."""
        now = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp is None:
            return 0
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        diff = (exp - now).total_seconds()
        return max(0, int(diff))

    @property
    def time_remaining_display(self):
        """Human-readable countdown string."""
        secs = self.seconds_remaining
        if secs <= 0:
            return "Expired"
        hours = secs // 3600
        mins = (secs % 3600) // 60
        return f"{hours}h {mins}m"

    def sync_status(self):
        """Persist status updates when expired."""
        if self.status == 'ACTIVE' and self.is_expired and not self.attempt:
            self.status = 'EXPIRED'
            db.session.add(self)

    def __repr__(self):
        return f"<Credential {self.credential_key}: User={self.user_id}, Status={self.status}>"
