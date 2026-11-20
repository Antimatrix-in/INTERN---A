import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, Response
from flask_login import login_required, current_user
from models import db, User, Assessment, Question, Credential, Attempt, Result, ProctoringEvent
from services import (
    admin_required,
    get_admin_dashboard_stats,
    create_assessment,
    update_assessment,
    toggle_assessment_status,
    create_candidate_credential,
    regenerate_candidate_credential,
    toggle_credential_status,
    get_all_credentials,
    get_sample_json_template,
    parse_and_validate_question_json,
    save_imported_questions,
    get_questions_query
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
@admin_required
def enforce_admin():
    """Ensure all admin routes are strictly guarded."""
    pass

# -------------------------------------------------------------
# 1. Overview
# -------------------------------------------------------------
@admin_bp.route('/dashboard')
def dashboard():
    stats = get_admin_dashboard_stats()
    return render_template('admin/dashboard.html', stats=stats)

# -------------------------------------------------------------
# 2. Assessment Manager
# -------------------------------------------------------------
@admin_bp.route('/assessments')
def assessments():
    all_assessments = Assessment.query.order_by(Assessment.created_at.desc()).all()
    return render_template('admin/assessment_manager.html', assessments=all_assessments)

@admin_bp.route('/assessments/new', methods=['GET', 'POST'])
def assessment_new():
    if request.method == 'POST':
        title = request.form.get('title')
        code = request.form.get('code')
        description = request.form.get('description')
        duration_minutes = request.form.get('duration_minutes', 60)
        pass_percentage = request.form.get('pass_percentage', 60.0)
        mcq_count = request.form.get('mcq_count', 20)
        coding_count = request.form.get('coding_count', 2)
        is_active = bool(request.form.get('is_active'))

        assessment, errors = create_assessment(
            title=title,
            code=code,
            description=description,
            duration_minutes=duration_minutes,
            pass_percentage=pass_percentage,
            mcq_count=mcq_count,
            coding_count=coding_count,
            is_active=is_active,
            created_by_id=current_user.id
        )

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template('admin/assessment_form.html', assessment=None, form_data=request.form)

        flash(f"Assessment '{assessment.title}' ({assessment.code}) successfully created.", "success")
        return redirect(url_for('admin.assessments'))

    return render_template('admin/assessment_form.html', assessment=None, form_data={})

@admin_bp.route('/assessments/<int:assessment_id>/edit', methods=['GET', 'POST'])
def assessment_edit(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    if request.method == 'POST':
        title = request.form.get('title')
        code = request.form.get('code')
        description = request.form.get('description')
        duration_minutes = request.form.get('duration_minutes', 60)
        pass_percentage = request.form.get('pass_percentage', 60.0)
        mcq_count = request.form.get('mcq_count', 20)
        coding_count = request.form.get('coding_count', 2)
        is_active = bool(request.form.get('is_active'))

        updated_assessment, errors = update_assessment(
            assessment_id=assessment.id,
            title=title,
            code=code,
            description=description,
            duration_minutes=duration_minutes,
            pass_percentage=pass_percentage,
            mcq_count=mcq_count,
            coding_count=coding_count,
            is_active=is_active
        )

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template('admin/assessment_form.html', assessment=assessment, form_data=request.form)

        flash(f"Assessment '{updated_assessment.title}' successfully updated.", "success")
        return redirect(url_for('admin.assessments'))

    return render_template('admin/assessment_form.html', assessment=assessment, form_data=assessment.__dict__)

@admin_bp.route('/assessments/<int:assessment_id>/toggle', methods=['POST'])
def assessment_toggle(assessment_id):
    assessment, error = toggle_assessment_status(assessment_id)
    if error:
        flash(error, "danger")
    else:
        state = "activated" if assessment.is_active else "deactivated"
        flash(f"Assessment '{assessment.title}' has been {state}.", "info")
    return redirect(url_for('admin.assessments'))

# -------------------------------------------------------------
# 3. Question Bank Interface
# -------------------------------------------------------------
@admin_bp.route('/questions')
def questions():
    assessment_id = request.args.get('assessment_id', type=int)
    category = request.args.get('category')
    difficulty = request.args.get('difficulty')
    search = request.args.get('search')

    all_assessments = Assessment.query.order_by(Assessment.title.asc()).all()
    questions_list = get_questions_query(assessment_id, category, difficulty, search).all()

    # Get distinct categories
    categories = [r[0] for r in db.session.query(Question.category).distinct().filter(Question.category != None).all()]

    return render_template(
        'admin/question_bank.html',
        questions=questions_list,
        assessments=all_assessments,
        selected_assessment_id=assessment_id,
        categories=categories,
        selected_category=category,
        selected_difficulty=difficulty,
        search_query=search
    )

@admin_bp.route('/questions/template')
def question_template():
    """Download the official documented JSON question template."""
    template_data = get_sample_json_template()
    json_str = json.dumps(template_data, indent=2)
    return Response(
        json_str,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=antimatrix_question_template.json"}
    )

@admin_bp.route('/questions/upload', methods=['POST'])
def question_upload():
    if 'json_file' not in request.files:
        flash("No file was selected for upload.", "danger")
        return redirect(url_for('admin.questions'))

    file = request.files['json_file']
    if file.filename == '':
        flash("Please select a valid JSON file.", "danger")
        return redirect(url_for('admin.questions'))

    assessment_id = request.form.get('target_assessment_id', type=int)

    try:
        content = file.read()
        sanitized_questions, errors = parse_and_validate_question_json(content)
        if errors:
            for err in errors[:5]: # show first 5 errors to avoid huge banner
                flash(err, "danger")
            if len(errors) > 5:
                flash(f"...and {len(errors) - 5} more validation errors.", "danger")
            return redirect(url_for('admin.questions'))

        # Store in session for preview screen
        session['question_upload_staging'] = {
            'questions': sanitized_questions,
            'assessment_id': assessment_id,
            'filename': file.filename
        }
        return redirect(url_for('admin.question_preview'))

    except Exception as e:
        flash(f"Error reading uploaded file: {str(e)}", "danger")
        return redirect(url_for('admin.questions'))

@admin_bp.route('/questions/preview')
def question_preview():
    staging = session.get('question_upload_staging')
    if not staging:
        flash("No uploaded questions found in review buffer.", "warning")
        return redirect(url_for('admin.questions'))

    target_assessment = None
    if staging.get('assessment_id'):
        target_assessment = Assessment.query.get(staging['assessment_id'])

    return render_template(
        'admin/question_preview.html',
        questions=staging['questions'],
        assessment=target_assessment,
        filename=staging.get('filename')
    )

@admin_bp.route('/questions/save-batch', methods=['POST'])
def question_save_batch():
    staging = session.get('question_upload_staging')
    if not staging or not staging.get('questions'):
        flash("Staged questions have expired or were already saved.", "warning")
        return redirect(url_for('admin.questions'))

    assessment_id = staging.get('assessment_id')
    saved_count, error = save_imported_questions(staging['questions'], assessment_id=assessment_id)

    if error:
        flash(error, "danger")
        return redirect(url_for('admin.question_preview'))

    session.pop('question_upload_staging', None)
    flash(f"Successfully validated and saved {saved_count} questions into the question bank.", "success")
    return redirect(url_for('admin.questions', assessment_id=assessment_id if assessment_id else ''))

@admin_bp.route('/questions/<int:question_id>/edit', methods=['GET', 'POST'])
def question_edit(question_id):
    question = Question.query.get_or_404(question_id)
    all_assessments = Assessment.query.order_by(Assessment.title.asc()).all()

    if request.method == 'POST':
        question_text = request.form.get('question_text')
        assessment_id = request.form.get('assessment_id', type=int)
        difficulty = request.form.get('difficulty', 'MEDIUM')
        category = request.form.get('category', 'General')
        points = float(request.form.get('points', 1.0))
        correct_option = request.form.get('correct_option', 'A')
        explanation = request.form.get('explanation', '')

        # Build options from form
        opt_a = request.form.get('opt_A', '')
        opt_b = request.form.get('opt_B', '')
        opt_c = request.form.get('opt_C', '')
        opt_d = request.form.get('opt_D', '')

        options = [
            {"id": "A", "text": opt_a},
            {"id": "B", "text": opt_b},
            {"id": "C", "text": opt_c},
            {"id": "D", "text": opt_d}
        ]

        question.question_text = question_text
        question.assessment_id = assessment_id if assessment_id else None
        question.options = options
        question.correct_option = correct_option
        question.explanation = explanation
        question.points = points
        question.difficulty = difficulty
        question.category = category

        db.session.commit()
        flash("Question updated successfully.", "success")
        return redirect(url_for('admin.questions'))

    return render_template('admin/question_form.html', question=question, assessments=all_assessments)

@admin_bp.route('/questions/<int:question_id>/delete', methods=['POST'])
def question_delete(question_id):
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    flash("Question successfully deleted from the bank.", "info")
    return redirect(url_for('admin.questions'))

# -------------------------------------------------------------
# 4. Credential Manager (Core Feature)
# -------------------------------------------------------------
@admin_bp.route('/credentials')
def credentials():
    search = request.args.get('search')
    status_filter = request.args.get('status')
    assessment_id = request.args.get('assessment_id', type=int)

    all_assessments = Assessment.query.order_by(Assessment.title.asc()).all()
    creds = get_all_credentials(search, status_filter, assessment_id)

    return render_template(
        'admin/credential_manager.html',
        credentials=creds,
        assessments=all_assessments,
        selected_status=status_filter,
        selected_assessment_id=assessment_id,
        search_query=search
    )

@admin_bp.route('/credentials/create', methods=['GET', 'POST'])
def credential_create():
    all_assessments = Assessment.query.filter_by(is_active=True).order_by(Assessment.title.asc()).all()

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        assessment_id = request.form.get('assessment_id', type=int)
        custom_password = request.form.get('custom_password')
        custom_password = custom_password.strip() if custom_password else None

        if not full_name or not email or not assessment_id:
            flash("Candidate Full Name, Email, and Assigned Assessment are required.", "danger")
            return render_template('admin/credential_create.html', assessments=all_assessments, form_data=request.form)

        credential, candidate, raw_password, error = create_candidate_credential(
            full_name=full_name,
            email=email,
            assessment_id=assessment_id,
            custom_password=custom_password
        )

        if error:
            flash(error, "danger")
            return render_template('admin/credential_create.html', assessments=all_assessments, form_data=request.form)

        # Store in session for the confirmation screen
        session['latest_created_credential'] = {
            'credential_id': credential.id,
            'credential_key': credential.credential_key,
            'candidate_name': candidate.full_name,
            'candidate_email': candidate.email,
            'candidate_user_id': candidate.user_id,
            'raw_password': raw_password,
            'assessment_title': credential.assessment.title,
            'assessment_code': credential.assessment.code,
            'created_at': credential.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'expires_at': credential.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'duration_minutes': credential.assessment.duration_minutes
        }

        return redirect(url_for('admin.credential_confirm', credential_id=credential.id))

    return render_template('admin/credential_create.html', assessments=all_assessments, form_data={})

@admin_bp.route('/credentials/<int:credential_id>/confirm')
def credential_confirm(credential_id):
    """Candidate credential creation confirmation screen with one-time visible password."""
    cred_data = session.get('latest_created_credential')
    if not cred_data or cred_data.get('credential_id') != credential_id:
        # Fallback to fetching basic record (password hash is not exposed)
        cred = Credential.query.get_or_404(credential_id)
        cred_data = {
            'credential_id': cred.id,
            'credential_key': cred.credential_key,
            'candidate_name': cred.candidate.full_name,
            'candidate_email': cred.candidate.email,
            'candidate_user_id': cred.candidate.user_id,
            'raw_password': None, # hidden after first confirmation session
            'assessment_title': cred.assessment.title,
            'assessment_code': cred.assessment.code,
            'created_at': cred.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'expires_at': cred.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'duration_minutes': cred.assessment.duration_minutes
        }

    return render_template('admin/credential_confirm.html', credential=cred_data)

@admin_bp.route('/credentials/<int:credential_id>/regenerate', methods=['POST'])
def credential_regenerate(credential_id):
    """Explicit admin action: regenerate password and extend 48h validity."""
    cred, raw_password, error = regenerate_candidate_credential(credential_id)
    if error:
        flash(error, "danger")
        return redirect(url_for('admin.credentials'))

    # Store for confirmation screen
    session['latest_created_credential'] = {
        'credential_id': cred.id,
        'credential_key': cred.credential_key,
        'candidate_name': cred.candidate.full_name,
        'candidate_email': cred.candidate.email,
        'candidate_user_id': cred.candidate.user_id,
        'raw_password': raw_password,
        'assessment_title': cred.assessment.title,
        'assessment_code': cred.assessment.code,
        'created_at': cred.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'expires_at': cred.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'duration_minutes': cred.assessment.duration_minutes
    }
    flash(f"Candidate credential for {cred.candidate.full_name} has been regenerated.", "success")
    return redirect(url_for('admin.credential_confirm', credential_id=cred.id))

@admin_bp.route('/credentials/<int:credential_id>/toggle', methods=['POST'])
def credential_toggle(credential_id):
    cred, error = toggle_credential_status(credential_id)
    if error:
        flash(error, "danger")
    else:
        state = "disabled" if cred.status == 'DISABLED' else "active"
        flash(f"Credential {cred.credential_key} is now {state}.", "info")
    return redirect(url_for('admin.credentials'))

# -------------------------------------------------------------
# 5. Candidate Manager
# -------------------------------------------------------------
@admin_bp.route('/candidates')
def candidates():
    all_candidates = User.query.filter_by(role='CANDIDATE').order_by(User.created_at.desc()).all()
    return render_template('admin/candidate_manager.html', candidates=all_candidates)

# -------------------------------------------------------------
# 6. Examination Results
# -------------------------------------------------------------
@admin_bp.route('/results')
def results():
    all_results = Result.query.order_by(Result.created_at.desc()).all()
    return render_template('admin/results.html', results=all_results)

# -------------------------------------------------------------
# 7. Proctoring Logs
# -------------------------------------------------------------
@admin_bp.route('/proctoring')
def proctoring():
    logs = ProctoringEvent.query.order_by(ProctoringEvent.created_at.desc()).limit(100).all()
    return render_template('admin/proctoring_logs.html', logs=logs)

# -------------------------------------------------------------
# 8. Settings
# -------------------------------------------------------------
@admin_bp.route('/settings')
def settings():
    return render_template('admin/settings.html', admin_user=current_user)
