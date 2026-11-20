from datetime import datetime, timezone
from .database import db

class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=True, index=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False, default='MCQ') # MCQ
    section = db.Column(db.String(20), nullable=False, default='MCQ', server_default='MCQ', index=True) # 'MCQ' or 'APTITUDE'
    options = db.Column(db.JSON, nullable=False) # e.g. [{"id": "A", "text": "Option A"}, ...]
    correct_option = db.Column(db.String(10), nullable=False) # "A", "B", "C", "D"
    explanation = db.Column(db.Text, nullable=True)
    points = db.Column(db.Float, nullable=False, default=1.0) # MCQ: 1.0, Aptitude: 2.0
    difficulty = db.Column(db.String(20), nullable=False, default='MEDIUM') # EASY, MEDIUM, HARD
    category = db.Column(db.String(64), nullable=False, default='General') # Topic for Aptitude, Category for MCQ
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    assessment = db.relationship('Assessment', back_populates='questions')
    attempt_answers = db.relationship('AttemptAnswer', back_populates='question', cascade='all, delete-orphan')

    def to_dict(self, include_correct=False):
        """Serialize question for UI and candidate view."""
        data = {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'assessment_title': self.assessment.title if self.assessment else 'General Pool',
            'question_text': self.question_text,
            'question_type': self.question_type,
            'section': self.section,
            'options': self.options,
            'points': self.points,
            'difficulty': self.difficulty,
            'category': self.category,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_correct:
            data['correct_option'] = self.correct_option
            data['explanation'] = self.explanation
        return data

    def __repr__(self):
        return f"<Question {self.id} [{self.section}]: {self.question_text[:30]}>"
