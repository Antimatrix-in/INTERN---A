from datetime import datetime, timezone
from .database import db

class Result(db.Model):
    __tablename__ = 'results'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('attempts.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False, index=True)
    total_questions = db.Column(db.Integer, nullable=False, default=0)
    answered_questions = db.Column(db.Integer, nullable=False, default=0)
    correct_answers = db.Column(db.Integer, nullable=False, default=0)
    score = db.Column(db.Float, nullable=False, default=0.0)
    max_score = db.Column(db.Float, nullable=False, default=0.0)
    percentage = db.Column(db.Float, nullable=False, default=0.0)
    passed = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    attempt = db.relationship('Attempt', back_populates='result')
    candidate = db.relationship('User', back_populates='results')
    assessment = db.relationship('Assessment', back_populates='results')

    def __repr__(self):
        return f"<Result Attempt={self.attempt_id}, Score={self.score}/{self.max_score} ({self.percentage}%), Passed={self.passed}>"
