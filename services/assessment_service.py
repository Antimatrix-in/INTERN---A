from models import db, Assessment

def create_assessment(title, code, description, duration_minutes, pass_percentage, mcq_count, coding_count, is_active=True, created_by_id=None):
    """
    Creates an assessment with validated fields.
    coding_count must be between 1 and 5.
    """
    errors = []
    if not title or len(title.strip()) < 3:
        errors.append("Title must be at least 3 characters long.")
    if not code or len(code.strip()) < 2:
        errors.append("Assessment code must be at least 2 characters long.")
    else:
        existing = Assessment.query.filter_by(code=code.strip().upper()).first()
        if existing:
            errors.append(f"Assessment code '{code.strip().upper()}' already exists.")

    try:
        duration_minutes = int(duration_minutes)
        if duration_minutes <= 0 or duration_minutes > 360:
            errors.append("Duration must be between 1 and 360 minutes.")
    except (ValueError, TypeError):
        errors.append("Duration must be a valid integer.")

    try:
        pass_percentage = float(pass_percentage)
        if pass_percentage < 0 or pass_percentage > 100:
            errors.append("Pass percentage must be between 0 and 100.")
    except (ValueError, TypeError):
        errors.append("Pass percentage must be a valid number.")

    try:
        mcq_count = int(mcq_count)
        if mcq_count < 0:
            errors.append("MCQ count cannot be negative.")
    except (ValueError, TypeError):
        errors.append("MCQ count must be a valid integer.")

    try:
        coding_count = int(coding_count)
        # Configure coding problem count from 1 to 5 per requirements
        if coding_count < 1 or coding_count > 5:
            errors.append("Coding problem count must be between 1 and 5.")
    except (ValueError, TypeError):
        errors.append("Coding problem count must be a valid integer between 1 and 5.")

    if errors:
        return None, errors

    assessment = Assessment(
        code=code.strip().upper(),
        title=title.strip(),
        description=description.strip() if description else "",
        duration_minutes=duration_minutes,
        pass_percentage=pass_percentage,
        mcq_count=mcq_count,
        coding_count=coding_count,
        is_active=bool(is_active),
        created_by_id=created_by_id
    )

    db.session.add(assessment)
    db.session.commit()
    return assessment, None

def update_assessment(assessment_id, title, code, description, duration_minutes, pass_percentage, mcq_count, coding_count, is_active):
    """Updates an existing assessment with validation."""
    assessment = db.session.get(Assessment, assessment_id)
    if not assessment:
        return None, ["Assessment not found."]

    errors = []
    if not title or len(title.strip()) < 3:
        errors.append("Title must be at least 3 characters long.")
    if not code or len(code.strip()) < 2:
        errors.append("Assessment code must be at least 2 characters long.")
    else:
        existing = Assessment.query.filter(Assessment.code == code.strip().upper(), Assessment.id != assessment_id).first()
        if existing:
            errors.append(f"Assessment code '{code.strip().upper()}' is used by another assessment.")

    try:
        duration_minutes = int(duration_minutes)
        if duration_minutes <= 0 or duration_minutes > 360:
            errors.append("Duration must be between 1 and 360 minutes.")
    except (ValueError, TypeError):
        errors.append("Duration must be a valid integer.")

    try:
        pass_percentage = float(pass_percentage)
        if pass_percentage < 0 or pass_percentage > 100:
            errors.append("Pass percentage must be between 0 and 100.")
    except (ValueError, TypeError):
        errors.append("Pass percentage must be a valid number.")

    try:
        mcq_count = int(mcq_count)
        if mcq_count < 0:
            errors.append("MCQ count cannot be negative.")
    except (ValueError, TypeError):
        errors.append("MCQ count must be a valid integer.")

    try:
        coding_count = int(coding_count)
        if coding_count < 1 or coding_count > 5:
            errors.append("Coding problem count must be between 1 and 5.")
    except (ValueError, TypeError):
        errors.append("Coding problem count must be a valid integer between 1 and 5.")

    if errors:
        return None, errors

    assessment.title = title.strip()
    assessment.code = code.strip().upper()
    assessment.description = description.strip() if description else ""
    assessment.duration_minutes = duration_minutes
    assessment.pass_percentage = pass_percentage
    assessment.mcq_count = mcq_count
    assessment.coding_count = coding_count
    assessment.is_active = bool(is_active)

    db.session.commit()
    return assessment, None

def toggle_assessment_status(assessment_id):
    """Toggle assessment active state."""
    assessment = db.session.get(Assessment, assessment_id)
    if not assessment:
        return None, "Assessment not found."
    assessment.is_active = not assessment.is_active
    db.session.commit()
    return assessment, None
