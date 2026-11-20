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

    @property
    def coding_score(self):
        return 0.0

    @property
    def aptitude_score(self):
        if not self.attempt or not self.attempt.answers:
            return 0.0
        pts = 0.0
        for ans in self.attempt.answers:
            if ans.is_answered and ans.question and ans.question.section == 'APTITUDE':
                if ans.selected_option and ans.selected_option.strip().upper() == ans.question.correct_option.strip().upper():
                    pts += ans.question.points
        return pts

    @property
    def mcq_score(self):
        if not self.attempt or not self.attempt.answers:
            return self.score
        pts = 0.0
        for ans in self.attempt.answers:
            if ans.is_answered and ans.question and (ans.question.section == 'MCQ' or not ans.question.section):
                if ans.selected_option and ans.selected_option.strip().upper() == ans.question.correct_option.strip().upper():
                    pts += ans.question.points
        return pts

    def __repr__(self):
        return f"<Result Attempt={self.attempt_id}, Score={self.score}/{self.max_score} ({self.percentage}%), Passed={self.passed}>"
