import secrets
import string
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_
from models import db, User, Credential, Assessment

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

def create_candidate_credential(full_name, email, assessment_id, custom_password=None):
    """
    Creates a new candidate User and assigns a Credential valid for exactly 48 hours.
    Returns: (credential, user, raw_password, error_message)
    """
    # Validate assessment exists and is active
    assessment = db.session.get(Assessment, assessment_id)
    if not assessment:
        return None, None, None, "Selected assessment does not exist."
    if not assessment.is_active:
        return None, None, None, "Selected assessment is currently inactive."

    # Check if candidate email is already registered
    existing_user = User.query.filter_by(email=email.strip().lower()).first()
    if existing_user:
        # Check if they already have an active/pending credential
        if existing_user.credential and existing_user.credential.effective_status == 'ACTIVE':
            return None, None, None, f"Candidate with email {email} already has an active credential."

    # Generate credentials
    user_id = generate_candidate_user_id()
    username = user_id.lower()
    raw_password = custom_password or generate_secure_password()
    credential_key = generate_credential_key()

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=48) # Strictly 48 hours

    try:
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
            db.session.flush() # obtain candidate.id
        else:
            candidate = existing_user
            candidate.full_name = full_name.strip()
            candidate.set_password(raw_password)
            candidate.is_active = True
            # Remove previous credential if it was expired/used
            if candidate.credential:
                db.session.delete(candidate.credential)
                db.session.flush()

        credential = Credential(
            credential_key=credential_key,
            user_id=candidate.id,
            assessment_id=assessment.id,
            status='ACTIVE',
            created_at=now,
            expires_at=expires_at
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

    # If there was an abandoned or in-progress attempt, reset if admin explicitly chooses
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
        # Re-enable only if not past 48h expiry
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
    now = datetime.now(timezone.utc)
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
