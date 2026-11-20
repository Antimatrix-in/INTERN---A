from datetime import datetime, timezone
from .database import db

class ProctoringEvent(db.Model):
    __tablename__ = 'proctoring_events'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('attempts.id', ondelete='CASCADE'), nullable=False, index=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True) # TAB_SWITCH, FULLSCREEN_EXIT, FOCUS_LOST, RESUME_ATTEMPT, SYSTEM_INFO
    details = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    attempt = db.relationship('Attempt', back_populates='proctoring_events')

    def __repr__(self):
        return f"<ProctoringEvent {self.event_type} (Attempt={self.attempt_id})>"
