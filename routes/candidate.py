from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, Credential, Assessment, Attempt, AttemptAnswer, Question, Result
from services import (
    candidate_required,
    start_or_resume_examination,
    autosave_attempt_answer,
    submit_examination
)

candidate_bp = Blueprint('candidate', __name__, url_prefix='/candidate')

@candidate_bp.before_request
@login_required
@candidate_required
def enforce_candidate():
    """Ensure all candidate routes are strictly guarded."""
    pass

@candidate_bp.route('/dashboard')
def dashboard():
    """
    Candidate Dashboard:
    - Candidate Name & User ID
    - Assigned Assessment details
    - Credential Expiry Countdown (48h)
    - Examination Status (Not Started, In Progress, Completed, Expired)
    - Conditional Start / Resume / Expiry display
    """
    credential = current_user.credential
    assessment = credential.assessment if credential else None
    attempt = credential.attempt if credential else None

    # Check for automatic sync of expired status
    if credential and credential.status == 'ACTIVE' and credential.is_expired and not attempt:
        credential.status = 'EXPIRED'
        db.session.commit()

    return render_template(
        'candidate/dashboard.html',
        candidate=current_user,
        credential=credential,
        assessment=assessment,
        attempt=attempt
    )

@candidate_bp.route('/exam/start', methods=['POST'])
def exam_start():
    """Initiates a new examination attempt or resumes an existing one."""
    ip_address = request.remote_addr
    user_agent = request.user_agent.string if request.user_agent else "Unknown"

    attempt, is_resumed, error = start_or_resume_examination(
        candidate_user=current_user,
        ip_address=ip_address,
        user_agent=user_agent
    )

    if error:
        flash(error, "danger")
        return redirect(url_for('candidate.dashboard'))

    if is_resumed:
        flash("Resuming your active examination session.", "info")
    else:
        flash("Examination session started. The server timer has begun.", "success")

    return redirect(url_for('candidate.exam_session'))

@candidate_bp.route('/exam/session')
def exam_session():
    """Active examination session interface."""
    credential = current_user.credential
    if not credential:
        flash("No assessment assigned.", "danger")
        return redirect(url_for('candidate.dashboard'))

    attempt = credential.attempt
    if not attempt:
        flash("Please start your examination from the dashboard.", "warning")
        return redirect(url_for('candidate.dashboard'))

    if attempt.status in ['COMPLETED', 'TIMED_OUT']:
        flash("Examination has already been completed.", "info")
        return redirect(url_for('candidate.exam_result'))

    # Check server-side timer
    if attempt.is_timed_out:
        submit_examination(attempt.id, auto_timeout=True)
        flash("Examination time has elapsed. Your answers have been submitted automatically.", "warning")
        return redirect(url_for('candidate.exam_result'))

    # Fetch active questions and current candidate answers
    assessment = attempt.assessment
    questions = Question.query.filter_by(assessment_id=assessment.id, is_active=True).order_by(Question.id.asc()).all()
    saved_answers = {ans.question_id: ans for ans in attempt.answers}

    # Prepare structured questions with current answers
    prepared_questions = []
    for idx, q in enumerate(questions):
        ans = saved_answers.get(q.id)
        prepared_questions.append({
            'index': idx + 1,
            'id': q.id,
            'text': q.question_text,
            'options': q.options,
            'points': q.points,
            'category': q.category,
            'selected_option': ans.selected_option if ans else None,
            'is_answered': ans.is_answered if ans else False,
            'is_flagged': ans.is_flagged if ans else False
        })

    seconds_left = attempt.seconds_remaining

    return render_template(
        'candidate/exam_session.html',
        attempt=attempt,
        assessment=assessment,
        questions=prepared_questions,
        seconds_left=seconds_left
    )

@candidate_bp.route('/api/autosave', methods=['POST'])
def api_autosave():
    """AJAX autosave endpoint for candidate answers."""
    credential = current_user.credential
    if not credential or not credential.attempt:
        return jsonify({'success': False, 'error': 'No active exam attempt found.'}), 400

    attempt = credential.attempt
    data = request.get_json(silent=True) or {}
    question_id = data.get('question_id')
    selected_option = data.get('selected_option')
    is_flagged = data.get('is_flagged')

    if not question_id:
        return jsonify({'success': False, 'error': 'Missing question_id'}), 400

    success, error = autosave_attempt_answer(
        attempt_id=attempt.id,
        candidate_id=current_user.id,
        question_id=int(question_id),
        selected_option=selected_option,
        is_flagged=is_flagged
    )

    if not success:
        return jsonify({'success': False, 'error': error}), 400

    return jsonify({
        'success': True,
        'seconds_left': attempt.seconds_remaining
    })

@candidate_bp.route('/exam/submit', methods=['POST'])
def exam_submit():
    """Manual submission of examination by candidate."""
    credential = current_user.credential
    if not credential or not credential.attempt:
        flash("No active examination to submit.", "danger")
        return redirect(url_for('candidate.dashboard'))

    attempt = credential.attempt
    if attempt.status in ['COMPLETED', 'TIMED_OUT']:
        return redirect(url_for('candidate.exam_result'))

    result, error = submit_examination(attempt.id, auto_timeout=False)
    if error:
        flash(f"Submission error: {error}", "danger")
        return redirect(url_for('candidate.exam_session'))

    flash("Your assessment has been submitted successfully.", "success")
    return redirect(url_for('candidate.exam_result'))

@candidate_bp.route('/exam/result')
def exam_result():
    """Candidate post-submission completion view."""
    credential = current_user.credential
    attempt = credential.attempt if credential else None
    result = attempt.result if attempt else None

    if not attempt or attempt.status not in ['COMPLETED', 'TIMED_OUT']:
        flash("No completed examination found.", "warning")
        return redirect(url_for('candidate.dashboard'))

    return render_template(
        'candidate/exam_result.html',
        attempt=attempt,
        assessment=attempt.assessment,
        result=result
    )
