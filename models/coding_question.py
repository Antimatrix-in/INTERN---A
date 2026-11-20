from datetime import datetime, timezone
from .database import db

class CodingQuestion(db.Model):
    __tablename__ = 'coding_questions'

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    problem_statement = db.Column(db.Text, nullable=False)
    input_description = db.Column(db.Text, nullable=True)
    output_description = db.Column(db.Text, nullable=True)
    constraints = db.Column(db.Text, nullable=True)
    sample_input = db.Column(db.Text, nullable=True)
    sample_output = db.Column(db.Text, nullable=True)
    languages_supported = db.Column(db.JSON, nullable=False, default=list) # e.g. ["Python", "Java", "C++", "JavaScript"]
    test_cases = db.Column(db.JSON, nullable=False, default=list) # e.g. [{"input": "...", "expected_output": "...", "is_hidden": false}]
    points = db.Column(db.Float, nullable=False, default=15.0) # Configuration: 15 marks per question
    difficulty = db.Column(db.String(20), nullable=False, default='MEDIUM') # EASY, MEDIUM, HARD
    category = db.Column(db.String(64), nullable=False, default='Algorithms') # Topic / Category
    section = db.Column(db.String(20), nullable=False, default='CODING', index=True) # CODING
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    assessment = db.relationship('Assessment', back_populates='coding_questions')

    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'assessment_title': self.assessment.title if self.assessment else 'General Pool',
            'title': self.title,
            'problem_statement': self.problem_statement,
            'input_description': self.input_description,
            'output_description': self.output_description,
            'constraints': self.constraints,
            'sample_input': self.sample_input,
            'sample_output': self.sample_output,
            'languages_supported': self.languages_supported or [],
            'test_cases': self.test_cases or [],
            'points': self.points,
            'difficulty': self.difficulty,
            'category': self.category,
            'section': self.section,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<CodingQuestion {self.id}: {self.title}>"
