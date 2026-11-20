from datetime import datetime, timezone
from .database import db

class Attempt(db.Model):
    __tablename__ = 'attempts'

    id = db.Column(db.Integer, primary_key=True)
    # Strict DB-level guarantee: One attempt per credential
    credential_id = db.Column(db.Integer, db.ForeignKey('credentials.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='IN_PROGRESS', index=True) # IN_PROGRESS, COMPLETED, TIMED_OUT, ABANDONED
    started_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True) # Server-side examination timer limit
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)

    # Relationships
    credential = db.relationship('Credential', back_populates='attempt')
    candidate = db.relationship('User', back_populates='attempts')
    assessment = db.relationship('Assessment', back_populates='attempts')
    answers = db.relationship('AttemptAnswer', back_populates='attempt', cascade='all, delete-orphan')
    result = db.relationship('Result', back_populates='attempt', uselist=False, cascade='all, delete-orphan')
    proctoring_events = db.relationship('ProctoringEvent', back_populates='attempt', cascade='all, delete-orphan')

    @property
    def is_timed_out(self):
        """Check if server-side exam countdown has expired."""
        now = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp is None:
            return False
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now >= exp

    @property
    def seconds_remaining(self):
        """Server-side remaining time in seconds."""
        if self.status != 'IN_PROGRESS':
            return 0
        now = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp is None:
            return 0
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        diff = (exp - now).total_seconds()
        return max(0, int(diff))

    @property
    def can_resume(self):
        """Check if attempt can be safely resumed by candidate."""
        return self.status == 'IN_PROGRESS' and not self.is_timed_out

    def __repr__(self):
        return f"<Attempt {self.id}: Candidate={self.candidate_id}, Status={self.status}>"


class AttemptAnswer(db.Model):
    __tablename__ = 'attempt_answers'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('attempts.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    selected_option = db.Column(db.String(10), nullable=True) # "A", "B", "C", "D"
    is_answered = db.Column(db.Boolean, default=False, nullable=False)
    is_flagged = db.Column(db.Boolean, default=False, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    attempt = db.relationship('Attempt', back_populates='answers')
    question = db.relationship('Question', back_populates='attempt_answers')

    __table_args__ = (
        db.UniqueConstraint('attempt_id', 'question_id', name='uq_attempt_question'),
    )

    def __repr__(self):
        return f"<AttemptAnswer Attempt={self.attempt_id}, Question={self.question_id}, Option={self.selected_option}>"
