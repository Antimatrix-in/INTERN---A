from datetime import datetime, timezone, timedelta
from models import db, Credential, Assessment, Attempt, AttemptAnswer, Result, Question, ProctoringEvent

def start_or_resume_examination(candidate_user, ip_address=None, user_agent=None):
    """
    Enforces strict examination rules:
    - 48-hour credential validity for starting
    - Strict one attempt per credential
    - Resumption of interrupted attempts
    - Server-side timing
    Returns: (attempt, is_resumed, error_message)
    """
    credential = candidate_user.credential
    if not credential:
        return None, False, "No active credential assigned to your candidate profile."

    assessment = credential.assessment
    if not assessment:
        return None, False, "Assigned assessment could not be found."

    if not assessment.is_active:
        return None, False, "The assigned assessment is currently inactive."

    now = datetime.now(timezone.utc)

    # 1. Check if attempt already exists
    existing_attempt = credential.attempt
    if existing_attempt:
        if existing_attempt.status in ['COMPLETED', 'TIMED_OUT']:
            return None, False, "Examination attempt has already been submitted. Re-attempts are strictly prohibited."

        # Check if server-side examination timer has elapsed
        if existing_attempt.is_timed_out:
            # Auto-submit the expired attempt
            submit_examination(existing_attempt.id, auto_timeout=True)
            return None, False, "Examination time limit has expired. Your attempt has been automatically submitted."

        # Attempt is active and has time remaining -> Resume attempt!
        # Log resumption proctoring event
        resume_event = ProctoringEvent(
            attempt_id=existing_attempt.id,
            candidate_id=candidate_user.id,
            event_type='RESUME_ATTEMPT',
            details={'ip': ip_address, 'resumed_at': now.isoformat()}
        )
        db.session.add(resume_event)
        db.session.commit()
        return existing_attempt, True, None

    # 2. Starting a FRESH attempt -> enforce strict 48-hour credential validity
    if credential.status == 'DISABLED':
        return None, False, "Your credential has been disabled by the administrator."

    if credential.is_expired:
        credential.status = 'EXPIRED'
        db.session.commit()
        return None, False, "This credential has expired (48-hour validity window elapsed). You cannot start a new examination."

    # 3. Create fresh attempt inside a transaction
    try:
        exam_duration = assessment.duration_minutes or 60
        exam_expires_at = now + timedelta(minutes=exam_duration)

        attempt = Attempt(
            credential_id=credential.id,
            candidate_id=candidate_user.id,
            assessment_id=assessment.id,
            status='IN_PROGRESS',
            started_at=now,
            expires_at=exam_expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(attempt)
        db.session.flush() # Obtain attempt.id

        # Update credential status to reflect it has been claimed/used
        credential.used_at = now

        # Initialize answer slots for all active questions in this assessment
        questions = Question.query.filter_by(assessment_id=assessment.id, is_active=True).order_by(Question.id.asc()).all()
        for q in questions:
            ans = AttemptAnswer(
                attempt_id=attempt.id,
                question_id=q.id,
                selected_option=None,
                is_answered=False,
                is_flagged=False
            )
            db.session.add(ans)

        # Log system start proctoring event
        start_event = ProctoringEvent(
            attempt_id=attempt.id,
            candidate_id=candidate_user.id,
            event_type='SYSTEM_INFO',
            details={'ip': ip_address, 'user_agent': user_agent, 'started_at': now.isoformat()}
        )
        db.session.add(start_event)

        db.session.commit()
        return attempt, False, None

    except Exception as e:
        db.session.rollback()
        return None, False, f"Failed to initialize examination session: {str(e)}"

def autosave_attempt_answer(attempt_id, candidate_id, question_id, selected_option, is_flagged=None):
    """
    Autosaves candidate's response for a question.
    Validates server time before saving.
    """
    attempt = db.session.get(Attempt, attempt_id)
    if not attempt or attempt.candidate_id != candidate_id:
        return False, "Invalid attempt session."

    if attempt.status != 'IN_PROGRESS':
        return False, "Attempt has already been completed."

    if attempt.is_timed_out:
        submit_examination(attempt_id, auto_timeout=True)
        return False, "Exam time limit has elapsed. Attempt automatically submitted."

    answer = AttemptAnswer.query.filter_by(attempt_id=attempt_id, question_id=question_id).first()
    if not answer:
        # Create answer record if not present
        answer = AttemptAnswer(
            attempt_id=attempt_id,
            question_id=question_id,
            selected_option=selected_option if selected_option else None,
            is_answered=bool(selected_option),
            is_flagged=bool(is_flagged) if is_flagged is not None else False
        )
        db.session.add(answer)
    else:
        if selected_option is not None:
            answer.selected_option = selected_option if selected_option != "" else None
            answer.is_answered = bool(answer.selected_option)
        if is_flagged is not None:
            answer.is_flagged = bool(is_flagged)
        answer.updated_at = datetime.now(timezone.utc)

    db.session.commit()
    return True, None

def submit_examination(attempt_id, auto_timeout=False):
    """
    Submits examination, evaluates answers, calculates score, and generates Result record.
    Prevents any duplicate evaluation.
    """
    attempt = db.session.get(Attempt, attempt_id)
    if not attempt:
        return None, "Attempt not found."

    if attempt.status in ['COMPLETED', 'TIMED_OUT'] and attempt.result:
        return attempt.result, None

    now = datetime.now(timezone.utc)
    assessment = attempt.assessment

    # Fetch all answers and corresponding questions
    answers = AttemptAnswer.query.filter_by(attempt_id=attempt.id).all()
    questions = {q.id: q for q in Question.query.filter_by(assessment_id=assessment.id, is_active=True).all()}

    total_questions = len(questions)
    answered_questions = 0
    correct_answers = 0
    total_score = 0.0
    max_score = sum(q.points for q in questions.values()) if questions else 0.0

    for ans in answers:
        q = questions.get(ans.question_id)
        if not q:
            continue
        if ans.is_answered and ans.selected_option:
            answered_questions += 1
            if ans.selected_option.strip().upper() == q.correct_option.strip().upper():
                correct_answers += 1
                total_score += q.points

    percentage = round((total_score / max_score * 100), 2) if max_score > 0 else 0.0
    passed = percentage >= (assessment.pass_percentage or 60.0)

    try:
        attempt.status = 'TIMED_OUT' if auto_timeout else 'COMPLETED'
        attempt.submitted_at = now

        # Update credential status to USED
        if attempt.credential:
            attempt.credential.status = 'USED'

        result = Result(
            attempt_id=attempt.id,
            candidate_id=attempt.candidate_id,
            assessment_id=assessment.id,
            total_questions=total_questions,
            answered_questions=answered_questions,
            correct_answers=correct_answers,
            score=total_score,
            max_score=max_score,
            percentage=percentage,
            passed=passed,
            created_at=now
        )
        db.session.add(result)
        db.session.commit()
        return result, None

    except Exception as e:
        db.session.rollback()
        return None, f"Error submitting assessment: {str(e)}"
