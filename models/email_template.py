from datetime import datetime, timezone
from .database import db

class EmailTemplate(db.Model):
    __tablename__ = 'email_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='RECRUITMENT')
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    event_mappings = db.relationship('EmailEventMapping', back_populates='template')
    scheduled_jobs = db.relationship('ScheduledEmailJob', back_populates='template')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'subject': self.subject,
            'body': self.body,
            'category': self.category,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<EmailTemplate {self.id}: {self.name}>"


class EmailEventMapping(db.Model):
    __tablename__ = 'email_event_mappings'

    id = db.Column(db.Integer, primary_key=True)
    event_key = db.Column(db.String(50), unique=True, nullable=False, index=True)
    event_name = db.Column(db.String(100), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('email_templates.id', ondelete='SET NULL'), nullable=True, index=True)
    delay_minutes = db.Column(db.Integer, nullable=False, default=0)
    is_automated = db.Column(db.Boolean, nullable=False, default=True)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    template = db.relationship('EmailTemplate', back_populates='event_mappings')

    def to_dict(self):
        return {
            'id': self.id,
            'event_key': self.event_key,
            'event_name': self.event_name,
            'template_id': self.template_id,
            'template_name': self.template.name if self.template else None,
            'delay_minutes': self.delay_minutes,
            'is_automated': self.is_automated,
            'description': self.description
        }

    def __repr__(self):
        return f"<EmailEventMapping {self.event_key} -> Template #{self.template_id} ({self.delay_minutes}m delay)>"


class ScheduledEmailJob(db.Model):
    __tablename__ = 'scheduled_email_jobs'

    id = db.Column(db.Integer, primary_key=True)
    recipient_email = db.Column(db.String(120), nullable=False, index=True)
    recipient_name = db.Column(db.String(120), nullable=True)
    template_id = db.Column(db.Integer, db.ForeignKey('email_templates.id', ondelete='SET NULL'), nullable=True, index=True)
    event_key = db.Column(db.String(50), nullable=False, index=True)
    context_data = db.Column(db.JSON, nullable=True)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='PENDING', index=True) # PENDING, SENT, FAILED, CANCELLED
    idempotency_key = db.Column(db.String(120), unique=True, nullable=True, index=True) # Duplicate protection
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    template = db.relationship('EmailTemplate', back_populates='scheduled_jobs')

    def to_dict(self):
        return {
            'id': self.id,
            'recipient_email': self.recipient_email,
            'recipient_name': self.recipient_name,
            'template_id': self.template_id,
            'event_key': self.event_key,
            'subject': self.subject,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'status': self.status,
            'idempotency_key': self.idempotency_key,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<ScheduledEmailJob {self.id}: {self.event_key} -> {self.recipient_email} [{self.status}]>"
