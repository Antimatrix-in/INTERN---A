from datetime import datetime, timezone
from .database import db

class Assessment(db.Model):
    __tablename__ = 'assessments'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    pass_percentage = db.Column(db.Float, nullable=False, default=60.0)
    mcq_count = db.Column(db.Integer, nullable=False, default=20)
    coding_count = db.Column(db.Integer, nullable=False, default=2) # 1 to 5 per requirements
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    questions = db.relationship('Question', back_populates='assessment', cascade='all, delete-orphan', lazy='dynamic')
    coding_questions = db.relationship('CodingQuestion', back_populates='assessment', cascade='all, delete-orphan', lazy='dynamic')
    credentials = db.relationship('Credential', back_populates='assessment', cascade='all, delete-orphan')
    attempts = db.relationship('Attempt', back_populates='assessment')
    results = db.relationship('Result', back_populates='assessment')

    @property
    def total_questions_configured(self):
        return (self.mcq_count or 0) + (self.coding_count or 0)

    @property
    def active_questions_count(self):
        return self.questions.filter_by(is_active=True).count()

    def __repr__(self):
        return f"<Assessment {self.code}: {self.title}>"
