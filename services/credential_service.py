import os
import secrets
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_
from models import db, User, Credential, Assessment, EmailTemplate, ScheduledEmailJob
from .email_template_service import render_template_placeholders
from .candidate_lookup_service import lookup_candidate

def find_or_sync_candidate_identity(candidate_info):
    """
    Syncs candidate identity snapshot from external authoritative database into assessment database.
    Does not modify external database.
    Returns local User model instance.
    """
    if not candidate_info:
        return None
    cid = candidate_info.get('candidate_id', '').strip()
    cname = candidate_info.get('candidate_name', '').strip()
    cemail = candidate_info.get('candidate_email', '').strip().lower()
    source_sys = candidate_info.get('source_system', 'antimatrix_db')

    # Look for existing user in assessment DB by user_id or email
    user = User.query.filter(
        (User.user_id == cid) |
        (db.func.lower(User.user_id) == cid.lower()) |
        (db.func.lower(User.email) == cemail)
    ).first()

    if not user:
        user = User(
            user_id=cid,
            username=cid.lower(),
            email=cemail,
            full_name=cname,
            role='CANDIDATE',
            source_system=source_sys,
            is_active=True
        )
        user.set_password(generate_secure_password())
        db.session.add(user)
        db.session.flush()
    else:
        # Update name and email to match authoritative source
        user.full_name = cname
        user.email = cemail
        user.user_id = cid
        user.role = 'CANDIDATE'
        user.source_system = source_sys
        user.is_active = True
        db.session.flush()

    return user

def generate_candidate_user_id():
    """Generates a unique, professional candidate user ID e.g. AM-2026-X8K9M2."""
    year = datetime.now().year
    while True:
        suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        candidate_id = f"AM-{year}-{suffix}"
        if not User.query.filter_by(user_id=candidate_id).first():
            return candidate_id

def generate_secure_password(length=12):
    """
    Generates a high-entropy temporary password containing uppercase,
    lowercase, digits, and special characters.
    """
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = ''.join(secrets.choice(chars) for _ in range(length))
        # Ensure at least one upper, lower, digit, and symbol
        if (any(c.islower() for c in pwd) and
            any(c.isupper() for c in pwd) and
            any(c.isdigit() for c in pwd) and
            any(c in "!@#$%^&*" for c in pwd)):
            return pwd

def generate_credential_key():
    """Generates a secure public credential key e.g. CRD-XXXXXXXX."""
    while True:
        key = "CRD-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))
        if not Credential.query.filter_by(credential_key=key).first():
            return key

def find_candidate_by_id(candidate_id):
    """
    Find candidate by Candidate ID:
    1. Queries the authoritative Anti-Matrix source database (strict read-only).
       If found, syncs candidate identity reference into assessment database.
    2. Fallback: checks local assessment database User records (e.g. if source DB is temporarily unreachable).
    Returns User object or None.
    """
    if not candidate_id:
        return None
    candidate_id = str(candidate_id).strip()

    # Query authoritative source database
    lookup_res = lookup_candidate(candidate_id)
    if lookup_res.get("success") and lookup_res.get("candidate"):
        return find_or_sync_candidate_identity(lookup_res["candidate"])

    # Fallback to local assessment DB records (e.g. offline fallback / existing snapshot)
    return User.query.filter(
        (User.user_id == candidate_id) |
        (db.func.lower(User.user_id) == candidate_id.lower()) |
        (db.func.lower(User.username) == candidate_id.lower()) |
        (db.func.lower(User.email) == candidate_id.lower())
    ).filter_by(role='CANDIDATE').first()

def create_candidate_credential(full_name=None, email=None, assessment_id=None, custom_password=None, candidate_id=None):
    """
    Creates or assigns a Credential valid for exactly 48 hours.
    Supports:
      1. New workflow: candidate_id (existing candidate lookup from DB)
      2. Legacy workflow: full_name and email
    Enforces:
      - Assessment must exist and be active.
      - Candidate must exist when candidate_id is specified.
      - If candidate already has an active credential for the same assessment, duplicate issuance is blocked.
      - Strict 48-hour expiration.
    Returns: (credential, user, raw_password, error_message)
    """
    # Validate assessment exists and is active
    if not assessment_id:
        return None, None, None, "Assigned Assessment is required."

    assessment = db.session.get(Assessment, int(assessment_id))
    if not assessment:
        return None, None, None, "Selected assessment does not exist."
    if not assessment.is_active:
        return None, None, None, "Selected assessment is currently inactive."

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=48) # Strictly 48 hours
    credential_key = generate_credential_key()
    raw_password = custom_password or generate_secure_password()

    try:
        # Case 1: Candidate ID Lookup Workflow
        if candidate_id:
            candidate = find_candidate_by_id(candidate_id)
            if not candidate:
                return None, None, None, "Candidate not found. Please check the Candidate ID."

            # Check if candidate already has an active credential for the same assessment
            if candidate.credential and candidate.credential.effective_status == 'ACTIVE':
                if candidate.credential.assessment_id == assessment.id:
                    return None, None, None, "Candidate already has an active credential for this assessment."
                else:
                    return None, None, None, f"Candidate already has an active credential for another assessment ({candidate.credential.assessment.title})."

            candidate.set_password(raw_password)
            candidate.is_active = True

            # If candidate had an expired/used credential, remove it to preserve 1-credential constraint
            if candidate.credential:
                db.session.delete(candidate.credential)
                db.session.flush()

            credential = Credential(
                credential_key=credential_key,
                user_id=candidate.id,
                assessment_id=assessment.id,
                status='ACTIVE',
                created_at=now,
                expires_at=expires_at,
                email_status='PENDING'
            )
            db.session.add(credential)
            db.session.commit()
            return credential, candidate, raw_password, None

        # Case 2: Full Name & Email Workflow (Legacy / Registration fallback)
        if not full_name or not email:
            return None, None, None, "Candidate Name and Email or Candidate ID are required."

        existing_user = User.query.filter_by(email=email.strip().lower()).first()
        if existing_user:
            if existing_user.credential and existing_user.credential.effective_status == 'ACTIVE':
                if existing_user.credential.assessment_id == assessment.id:
                    return None, None, None, "Candidate already has an active credential for this assessment."
                return None, None, None, f"Candidate with email {email} already has an active credential."

        user_id = generate_candidate_user_id()
        username = user_id.lower()

        if not existing_user:
            candidate = User(
                user_id=user_id,
                username=username,
                email=email.strip().lower(),
                full_name=full_name.strip(),
                role='CANDIDATE',
                is_active=True
            )
            candidate.set_password(raw_password)
            db.session.add(candidate)
            db.session.flush()
        else:
            candidate = existing_user
            candidate.full_name = full_name.strip()
            candidate.set_password(raw_password)
            candidate.is_active = True
            if candidate.credential:
                db.session.delete(candidate.credential)
                db.session.flush()

        credential = Credential(
            credential_key=credential_key,
            user_id=candidate.id,
            assessment_id=assessment.id,
            status='ACTIVE',
            created_at=now,
            expires_at=expires_at,
            email_status='PENDING'
        )
        db.session.add(credential)
        db.session.commit()
        return credential, candidate, raw_password, None

    except Exception as e:
        db.session.rollback()
        return None, None, None, f"Database error creating credential: {str(e)}"

def regenerate_candidate_credential(credential_id):
    """
    Explicit admin action: resets candidate password and restarts the 48-hour validity.
    Returns: (credential, raw_password, error_message)
    """
    credential = db.session.get(Credential, credential_id)
    if not credential:
        return None, None, "Credential not found."

    if credential.attempt and credential.attempt.status == 'COMPLETED':
        return None, None, "Cannot regenerate credential for an assessment attempt that has already been completed."

    candidate = credential.candidate
    raw_password = generate_secure_password()
    candidate.set_password(raw_password)

    now = datetime.now(timezone.utc)
    credential.created_at = now
    credential.expires_at = now + timedelta(hours=48)
    credential.status = 'ACTIVE'
    credential.email_status = 'PENDING'
    credential.email_sent_at = None

    try:
        db.session.commit()
        return credential, raw_password, None
    except Exception as e:
        db.session.rollback()
        return None, None, f"Failed to regenerate credential: {str(e)}"

def toggle_credential_status(credential_id):
    """Admin toggle between ACTIVE and DISABLED."""
    credential = db.session.get(Credential, credential_id)
    if not credential:
        return None, "Credential not found."

    if credential.status == 'DISABLED':
        if credential.is_expired:
            credential.status = 'EXPIRED'
        else:
            credential.status = 'ACTIVE'
    else:
        credential.status = 'DISABLED'

    db.session.commit()
    return credential, None

def get_all_credentials(search=None, status_filter=None, assessment_id=None):
    """Fetches credentials with dynamic expiration status update and filtering."""
    query = Credential.query.join(User).join(Assessment)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(search_term),
                User.email.ilike(search_term),
                User.user_id.ilike(search_term),
                Credential.credential_key.ilike(search_term),
                Assessment.title.ilike(search_term)
            )
        )

    if assessment_id:
        query = query.filter(Credential.assessment_id == assessment_id)

    credentials = query.order_by(Credential.created_at.desc()).all()

    # Synchronize expired credentials
    has_changes = False
    for cred in credentials:
        if cred.status == 'ACTIVE' and cred.is_expired and not cred.attempt:
            cred.status = 'EXPIRED'
            has_changes = True

    if has_changes:
        db.session.commit()

    if status_filter:
        credentials = [c for c in credentials if c.effective_status == status_filter]

    return credentials

def send_credential_email(credential_id, raw_password=None, resend=False, login_url=None):
    """
    Dispatches credential details to the candidate's registered email.
    Substitutes all variables:
      {{candidate_name}}
      {{candidate_id}}
      {{candidate_email}}
      {{assessment_name}}
      {{login_url}}
      {{username}}
      {{password}}
      {{expiry_time}}
    Prevents accidental duplicate sending unless resend is True.
    Records email delivery status: 'PENDING', 'SENT', 'FAILED'.
    Returns (success_bool, message).
    """
    credential = db.session.get(Credential, credential_id)
    if not credential:
        return False, "Credential record not found."

    # Prevent accidental duplicate email sending
    if credential.email_status == 'SENT' and not resend:
        return False, "Credentials have already been sent to this candidate. Use the Resend option if needed."

    candidate = credential.candidate
    assessment = credential.assessment

    if not candidate or not candidate.email:
        return False, "Candidate has no registered email address."

    # Template retrieval (falls back gracefully)
    template = EmailTemplate.query.filter(
        (EmailTemplate.name == 'Assessment Invitation') |
        (EmailTemplate.name == 'Candidate Assessment Credential')
    ).first()

    default_subject = "Assessment Credentials — {{assessment_name}} — Anti-Matrix"
    default_body = """Dear {{candidate_name}},

You have been provisioned access for the {{assessment_name}} on the Anti-Matrix Online Assessment Platform.

Your Assessment Login Details:
Candidate ID: {{candidate_id}}
Username: {{username}}
Password: {{password}}
Portal Login URL: {{login_url}}

Validity Period:
Your credentials expire on {{expiry_time}} (Strictly 48 Hours from issuance).

Important Instructions:
- Exactly 1 attempt is permitted per credential.
- Once the assessment begins, the timer cannot be paused.
- In case of network interruption, log back in with these credentials to resume your attempt.

Best regards,
Anti-Matrix Assessment Team"""

    subject_template = template.subject if template else default_subject
    body_template = template.body if template else default_body

    # Format expiry
    exp_str = credential.expires_at.strftime('%Y-%m-%d %H:%M UTC') if credential.expires_at else '48 Hours from issuance'

    context = {
        'candidate_name': candidate.full_name,
        'candidate_id': candidate.user_id,
        'candidate_email': candidate.email,
        'assessment_name': assessment.title,
        'login_url': login_url or 'http://localhost:5000/auth/login',
        'username': candidate.user_id,
        'password': raw_password or '[Active Password Generated]',
        'expiry_time': exp_str
    }

    rendered_subject = render_template_placeholders(subject_template, context)
    rendered_body = render_template_placeholders(body_template, context)

    # SMTP Configuration from Environment
    smtp_server = os.environ.get('SMTP_SERVER') or os.environ.get('MAIL_SERVER')
    smtp_port = int(os.environ.get('SMTP_PORT') or os.environ.get('MAIL_PORT') or 587)
    smtp_user = os.environ.get('SMTP_USERNAME') or os.environ.get('MAIL_USERNAME')
    smtp_pass = os.environ.get('SMTP_PASSWORD') or os.environ.get('MAIL_PASSWORD')
    smtp_use_tls = os.environ.get('SMTP_USE_TLS', 'true').lower() in ['true', '1', 'yes']
    mail_from = os.environ.get('SMTP_FROM_EMAIL') or os.environ.get('MAIL_DEFAULT_SENDER') or 'recruitment@antimatrix.local'

    delivery_success = False
    delivery_error = None

    if smtp_server:
        try:
            msg = MIMEMultipart()
            msg['From'] = mail_from
            msg['To'] = candidate.email
            msg['Subject'] = rendered_subject
            msg.attach(MIMEText(rendered_body, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            if smtp_use_tls:
                server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(mail_from, [candidate.email], msg.as_string())
            server.quit()
            delivery_success = True
        except Exception as e:
            delivery_success = False
            delivery_error = str(e)
    else:
        # Development / Testing simulation: email dispatch succeeds safely
        delivery_success = True

    now_utc = datetime.now(timezone.utc)
    if delivery_success:
        credential.email_status = 'SENT'
        credential.email_sent_at = now_utc
        credential.email_error = None

        # Audit log in ScheduledEmailJob
        job = ScheduledEmailJob(
            recipient_email=candidate.email,
            recipient_name=candidate.full_name,
            template_id=template.id if template else None,
            event_key='ASSESSMENT_INVITATION',
            context_data=context,
            subject=rendered_subject,
            body=rendered_body,
            scheduled_at=now_utc,
            sent_at=now_utc,
            status='SENT',
            idempotency_key=f"cred_send_{credential.id}_{int(now_utc.timestamp() * 1000)}_{secrets.token_hex(4)}"
        )
        db.session.add(job)
        db.session.commit()
        return True, f"Credentials successfully delivered to {candidate.email}."
    else:
        credential.email_status = 'FAILED'
        credential.email_error = delivery_error
        db.session.commit()
        return False, f"Email delivery failed: {delivery_error}"
