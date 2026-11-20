import re
from datetime import datetime, timezone, timedelta
from models import db, EmailTemplate, EmailEventMapping, ScheduledEmailJob

DEFAULT_TEMPLATES = [
    {
        "name": "Application Acknowledgment",
        "subject": "Application Received — {{job_title}} at {{company_name}}",
        "category": "RECRUITMENT",
        "body": """Dear {{candidate_name}},

Thank you for applying for the {{job_title}} position at {{company_name}}.

We have received your application successfully. Your application reference ID is: {{application_id}}.
Our hiring team will carefully review your credentials and qualifications. You will receive an update regarding the next steps in our recruitment process.

Best regards,
Talent Acquisition Team
{{company_name}}"""
    },
    {
        "name": "Assessment Invitation",
        "subject": "Online Assessment Invitation — {{company_name}}",
        "category": "ASSESSMENT",
        "body": """Dear {{candidate_name}},

We are pleased to invite you to complete the online assessment for the {{job_title}} role at {{company_name}}.

Application ID: {{application_id}}
Please log in to your candidate assessment portal to access your assigned technical examination.
Ensure you complete your assessment before the strict credential validity period expires.

Best regards,
Recruitment & Assessment Team
{{company_name}}"""
    },
    {
        "name": "Shortlisted Notification",
        "subject": "Update on your application for {{job_title}} — {{company_name}}",
        "category": "RECRUITMENT",
        "body": """Dear {{candidate_name}},

Congratulations! We are pleased to inform you that your profile has been shortlisted for the {{job_title}} role at {{company_name}}.

Application ID: {{application_id}}
Our talent acquisition team was impressed with your qualifications and will reach out shortly with details regarding the next evaluation round.

Best regards,
Talent Acquisition Team
{{company_name}}"""
    },
    {
        "name": "Rejection Notification",
        "subject": "Application Status — {{job_title}} at {{company_name}}",
        "category": "RECRUITMENT",
        "body": """Dear {{candidate_name}},

Thank you for taking the time to apply for the {{job_title}} position at {{company_name}} and for your interest in our team.

After careful review of your application (Reference ID: {{application_id}}), we regret to inform you that we will not be moving forward with your candidacy for this role at this time.

We appreciate the effort you invested and encourage you to apply for future opportunities matching your profile.

Sincerely,
Talent Acquisition Team
{{company_name}}"""
    },
    {
        "name": "Interview Invitation",
        "subject": "Interview Invitation — {{job_title}} at {{company_name}}",
        "category": "RECRUITMENT",
        "body": """Dear {{candidate_name}},

Following your performance, we would like to invite you for an interview for the {{job_title}} position at {{company_name}}.

Application Reference: {{application_id}}
Please reply to this email with your availability over the upcoming 3 business days to coordinate the interview slot.

Best regards,
Talent Acquisition Team
{{company_name}}"""
    }
]

DEFAULT_EVENT_MAPPINGS = [
    {
        "event_key": "APPLICATION_SUBMITTED",
        "event_name": "Candidate Application Submitted",
        "template_name": "Application Acknowledgment",
        "delay_minutes": 5, # 5-minute delayed acknowledgment per specification
        "is_automated": True,
        "description": "Sent to candidate 5 minutes after submitting an application"
    },
    {
        "event_key": "CANDIDATE_SHORTLISTED",
        "event_name": "Candidate Shortlisted",
        "template_name": "Shortlisted Notification",
        "delay_minutes": 0,
        "is_automated": True,
        "description": "Sent when an admin marks candidate status as shortlisted"
    },
    {
        "event_key": "CANDIDATE_REJECTED",
        "event_name": "Candidate Rejected",
        "template_name": "Rejection Notification",
        "delay_minutes": 0,
        "is_automated": True,
        "description": "Sent when an application is rejected"
    },
    {
        "event_key": "ASSESSMENT_INVITATION",
        "event_name": "Assessment Invitation",
        "template_name": "Assessment Invitation",
        "delay_minutes": 0,
        "is_automated": False, # Crucial: "Do not activate assessment email automation yet."
        "description": "Invitation with assessment credentials (automation currently paused)"
    },
    {
        "event_key": "INTERVIEW_INVITATION",
        "event_name": "Interview Invitation",
        "template_name": "Interview Invitation",
        "delay_minutes": 0,
        "is_automated": True,
        "description": "Sent when inviting candidate for an interview"
    }
]

def render_template_placeholders(text, context=None):
    """
    Renders {{placeholder}} tokens using safe regex replacement.
    Default context values are provided if missing.
    """
    if not text:
        return ""
    
    ctx = {
        'candidate_name': 'Candidate',
        'application_id': 'AM-APP-0001',
        'job_title': 'Software Engineering Intern',
        'company_name': 'Anti-Matrix',
    }
    if context:
        ctx.update(context)

    rendered = text
    for key, val in ctx.items():
        pattern = re.compile(r'\{\{\s*' + re.escape(key) + r'\s*\}\}', re.IGNORECASE)
        rendered = pattern.sub(str(val), rendered)
        
    return rendered

def seed_default_templates_and_mappings():
    """Seeds the 5 standard email templates and recruitment event mappings if missing."""
    template_map = {}
    
    # 1. Seed Templates
    for t_data in DEFAULT_TEMPLATES:
        existing = EmailTemplate.query.filter(db.func.lower(EmailTemplate.name) == t_data['name'].lower()).first()
        if not existing:
            new_t = EmailTemplate(
                name=t_data['name'],
                subject=t_data['subject'],
                body=t_data['body'],
                category=t_data['category'],
                is_active=True
            )
            db.session.add(new_t)
            db.session.flush()
            template_map[t_data['name']] = new_t.id
        else:
            template_map[t_data['name']] = existing.id

    # 2. Seed Event Mappings with stable template IDs
    for m_data in DEFAULT_EVENT_MAPPINGS:
        existing_m = EmailEventMapping.query.filter_by(event_key=m_data['event_key']).first()
        mapped_t_id = template_map.get(m_data['template_name'])
        
        if not existing_m:
            new_m = EmailEventMapping(
                event_key=m_data['event_key'],
                event_name=m_data['event_name'],
                template_id=mapped_t_id,
                delay_minutes=m_data['delay_minutes'],
                is_automated=m_data['is_automated'],
                description=m_data.get('description', '')
            )
            db.session.add(new_m)
        else:
            # If template_id was missing or unmapped, associate with default template ID
            if not existing_m.template_id and mapped_t_id:
                existing_m.template_id = mapped_t_id

    db.session.commit()

def get_all_templates(search=None, category=None, status=None):
    """Fetch all email templates with optional filters."""
    query = EmailTemplate.query
    if search:
        s = f"%{search.strip()}%"
        query = query.filter((EmailTemplate.name.ilike(s)) | (EmailTemplate.subject.ilike(s)))
    if category:
        query = query.filter_by(category=category)
    if status is not None and status != '':
        is_act = (status.lower() in ['true', '1', 'active'])
        query = query.filter_by(is_active=is_act)
        
    return query.order_by(EmailTemplate.created_at.desc()).all()

def get_template_by_id(template_id):
    """Retrieve template by ID."""
    return db.session.get(EmailTemplate, template_id)

def create_email_template(name, subject, body, category='RECRUITMENT', is_active=True):
    """
    Creates an email template ensuring unique name.
    Returns (template, error).
    """
    name = (name or '').strip()
    subject = (subject or '').strip()
    body = (body or '').strip()

    if not name or len(name) < 3:
        return None, "Template name is required and must be at least 3 characters."
    if not subject:
        return None, "Email subject line is required."
    if not body:
        return None, "Email body text is required."

    existing = EmailTemplate.query.filter(db.func.lower(EmailTemplate.name) == name.lower()).first()
    if existing:
        return None, f"An email template with the name '{name}' already exists."

    t = EmailTemplate(
        name=name,
        subject=subject,
        body=body,
        category=category or 'RECRUITMENT',
        is_active=is_active
    )
    db.session.add(t)
    db.session.commit()
    return t, None

def update_email_template(template_id, name, subject, body, category=None, is_active=None):
    """
    Updates an existing email template.
    Does NOT break mappings (mappings reference template.id).
    """
    t = db.session.get(EmailTemplate, template_id)
    if not t:
        return None, "Email template not found."

    name = (name or '').strip()
    subject = (subject or '').strip()
    body = (body or '').strip()

    if not name or len(name) < 3:
        return None, "Template name is required and must be at least 3 characters."
    if not subject:
        return None, "Email subject line is required."
    if not body:
        return None, "Email body text is required."

    # Check unique name across other templates
    existing = EmailTemplate.query.filter(
        db.func.lower(EmailTemplate.name) == name.lower(),
        EmailTemplate.id != template_id
    ).first()
    if existing:
        return None, f"Another email template with the name '{name}' already exists."

    t.name = name
    t.subject = subject
    t.body = body
    if category is not None:
        t.category = category
    if is_active is not None:
        t.is_active = is_active

    db.session.commit()
    return t, None

def duplicate_email_template(template_id):
    """
    Duplicates an email template, creating a copy with a unique name.
    """
    original = db.session.get(EmailTemplate, template_id)
    if not original:
        return None, "Template not found."

    base_name = f"{original.name} (Copy)"
    candidate_name = base_name
    counter = 2
    while EmailTemplate.query.filter(db.func.lower(EmailTemplate.name) == candidate_name.lower()).first():
        candidate_name = f"{original.name} (Copy {counter})"
        counter += 1

    duplicate = EmailTemplate(
        name=candidate_name,
        subject=original.subject,
        body=original.body,
        category=original.category,
        is_active=original.is_active
    )
    db.session.add(duplicate)
    db.session.commit()
    return duplicate, None

def toggle_email_template_status(template_id):
    """Toggles template between active and inactive."""
    t = db.session.get(EmailTemplate, template_id)
    if not t:
        return None, "Template not found."

    t.is_active = not t.is_active
    db.session.commit()
    return t, None

def delete_email_template(template_id):
    """Deletes an email template, unlinking it from mappings safely."""
    t = db.session.get(EmailTemplate, template_id)
    if not t:
        return False, "Template not found."

    # Unlink any mappings referencing this template
    for mapping in t.event_mappings:
        mapping.template_id = None

    db.session.delete(t)
    db.session.commit()
    return True, None

def get_all_event_mappings():
    """Returns all event mappings ordered by event key."""
    return EmailEventMapping.query.order_by(EmailEventMapping.id.asc()).all()

def update_event_mapping(event_key, template_id=None, delay_minutes=0, is_automated=True):
    """
    Updates an event mapping using stable template ID.
    Returns (mapping, error).
    """
    mapping = EmailEventMapping.query.filter_by(event_key=event_key).first()
    if not mapping:
        return None, f"Event mapping '{event_key}' not found."

    if template_id:
        target_template = db.session.get(EmailTemplate, int(template_id))
        if not target_template:
            return None, "Selected email template does not exist."
        mapping.template_id = target_template.id
    else:
        mapping.template_id = None

    try:
        mapping.delay_minutes = max(0, int(delay_minutes))
    except (ValueError, TypeError):
        mapping.delay_minutes = 0

    mapping.is_automated = bool(is_automated)
    db.session.commit()
    return mapping, None

def schedule_email_event(event_key, recipient_email, recipient_name=None, context_data=None, idempotency_key=None):
    """
    Schedules an email job based on an event mapping.
    Enforces delay_minutes, automation status, and duplicate protection via idempotency_key.
    Returns (ScheduledEmailJob, error).
    """
    if not recipient_email:
        return None, "Recipient email is required."

    mapping = EmailEventMapping.query.filter_by(event_key=event_key).first()
    if not mapping:
        return None, f"No event mapping configured for event '{event_key}'."

    if not mapping.is_automated:
        return None, f"Automation is disabled for event '{event_key}'."

    if not mapping.template_id:
        return None, f"No template linked to event '{event_key}'."

    template = mapping.template
    if not template or not template.is_active:
        return None, f"Linked template for '{event_key}' is inactive or deleted."

    # Duplicate Protection
    if idempotency_key:
        existing_job = ScheduledEmailJob.query.filter_by(idempotency_key=idempotency_key).first()
        if existing_job:
            return existing_job, "Duplicate email prevented: An email job with this idempotency key is already registered."

    context = context_data or {}
    if recipient_name and 'candidate_name' not in context:
        context['candidate_name'] = recipient_name

    rendered_subject = render_template_placeholders(template.subject, context)
    rendered_body = render_template_placeholders(template.body, context)

    now_utc = datetime.now(timezone.utc)
    scheduled_at = now_utc + timedelta(minutes=mapping.delay_minutes)

    job = ScheduledEmailJob(
        recipient_email=recipient_email.strip().lower(),
        recipient_name=recipient_name,
        template_id=template.id,
        event_key=event_key,
        context_data=context,
        subject=rendered_subject,
        body=rendered_body,
        scheduled_at=scheduled_at,
        status='PENDING',
        idempotency_key=idempotency_key
    )
    db.session.add(job)
    db.session.commit()
    return job, None

def get_email_queue_jobs(limit=50):
    """Returns recent scheduled email jobs."""
    return ScheduledEmailJob.query.order_by(ScheduledEmailJob.scheduled_at.desc()).limit(limit).all()

def process_pending_email_jobs():
    """
    Processes all pending email jobs that have reached their scheduled time.
    Returns count of sent jobs.
    """
    now_utc = datetime.now(timezone.utc)
    pending_jobs = ScheduledEmailJob.query.filter(
        ScheduledEmailJob.status == 'PENDING',
        ScheduledEmailJob.scheduled_at <= now_utc
    ).all()

    processed_count = 0
    for job in pending_jobs:
        # In this platform, mark as SENT
        job.status = 'SENT'
        job.sent_at = datetime.now(timezone.utc)
        processed_count += 1

    db.session.commit()
    return processed_count

def get_email_dashboard_stats():
    """Overview statistics for templates and email queue."""
    total_templates = EmailTemplate.query.count()
    active_templates = EmailTemplate.query.filter_by(is_active=True).count()
    total_mappings = EmailEventMapping.query.count()
    automated_mappings = EmailEventMapping.query.filter_by(is_automated=True).count()
    pending_jobs = ScheduledEmailJob.query.filter_by(status='PENDING').count()
    sent_jobs = ScheduledEmailJob.query.filter_by(status='SENT').count()

    return {
        'total_templates': total_templates,
        'active_templates': active_templates,
        'total_mappings': total_mappings,
        'automated_mappings': automated_mappings,
        'pending_jobs': pending_jobs,
        'sent_jobs': sent_jobs
    }
