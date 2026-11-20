import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, Response
from flask_login import login_required, current_user
from models import db, User, Assessment, Question, CodingQuestion, Credential, Attempt, Result, ProctoringEvent, EmailTemplate, EmailEventMapping, ScheduledEmailJob
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
    get_question_bank_stats,
    get_coding_questions_query,
    get_mcq_questions_query,
    CATEGORY_CONFIG,
    get_all_templates,
    get_template_by_id,
    create_email_template,
    update_email_template,
    duplicate_email_template,
    toggle_email_template_status,
    delete_email_template,
    get_all_event_mappings,
    update_event_mapping,
    render_template_placeholders,
    schedule_email_event,
    get_email_queue_jobs,
    process_pending_email_jobs,
    get_email_dashboard_stats
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
# 3. Question Bank Interface (Categorized: Coding, Aptitude, MCQ)
# -------------------------------------------------------------
@admin_bp.route('/questions')
def questions():
    tab = request.args.get('tab', 'coding').lower()
    if tab not in ['coding', 'aptitude', 'mcq']:
        tab = 'coding'

    assessment_id = request.args.get('assessment_id', type=int)
    category = request.args.get('category')
    difficulty = request.args.get('difficulty')
    search = request.args.get('search')

    all_assessments = Assessment.query.order_by(Assessment.title.asc()).all()
    stats = get_question_bank_stats(assessment_id)

    if tab == 'coding':
        questions_list = get_coding_questions_query(assessment_id, category, difficulty, search).all()
        categories = [r[0] for r in db.session.query(CodingQuestion.category).distinct().filter(CodingQuestion.category != None).all()]
    elif tab == 'aptitude':
        questions_list = get_mcq_questions_query('APTITUDE', assessment_id, category, difficulty, search).all()
        categories = [r[0] for r in db.session.query(Question.category).filter_by(section='APTITUDE').distinct().filter(Question.category != None).all()]
    else: # tab == 'mcq'
        questions_list = get_mcq_questions_query('MCQ', assessment_id, category, difficulty, search).all()
        categories = [r[0] for r in db.session.query(Question.category).filter_by(section='MCQ').distinct().filter(Question.category != None).all()]

    return render_template(
        'admin/question_bank.html',
        active_tab=tab,
        questions=questions_list,
        stats=stats,
        category_config=CATEGORY_CONFIG.get(tab),
        assessments=all_assessments,
        selected_assessment_id=assessment_id,
        categories=categories,
        selected_category=category,
        selected_difficulty=difficulty,
        search_query=search
    )

@admin_bp.route('/questions/template')
def question_template():
    """Download the official documented JSON question template per category."""
    category = request.args.get('category', 'mcq').lower()
    if category not in ['coding', 'aptitude', 'mcq']:
        category = 'mcq'

    filename_map = {
        'coding': 'coding_questions_template.json',
        'aptitude': 'aptitude_questions_template.json',
        'mcq': 'mcq_questions_template.json'
    }
    filename = filename_map.get(category, 'mcq_questions_template.json')
    template_data = get_sample_json_template(category)
    json_str = json.dumps(template_data, indent=2)
    return Response(
        json_str,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@admin_bp.route('/questions/upload', methods=['POST'])
def question_upload():
    category = request.form.get('category', 'mcq').lower()
    if category not in ['coding', 'aptitude', 'mcq']:
        category = 'mcq'

    if 'json_file' not in request.files:
        flash("No file was selected for upload.", "danger")
        return redirect(url_for('admin.questions', tab=category))

    file = request.files['json_file']
    if file.filename == '':
        flash("Please select a valid JSON file.", "danger")
        return redirect(url_for('admin.questions', tab=category))

    assessment_id = request.form.get('target_assessment_id', type=int)

    try:
        content = file.read()
        sanitized_questions, errors = parse_and_validate_question_json(content, category=category)
        if errors:
            for err in errors[:5]: # show first 5 errors to avoid huge banner
                flash(err, "danger")
            if len(errors) > 5:
                flash(f"...and {len(errors) - 5} more validation errors.", "danger")
            return redirect(url_for('admin.questions', tab=category))

        # Store in session for preview screen
        session['question_upload_staging'] = {
            'category': category,
            'questions': sanitized_questions,
            'assessment_id': assessment_id,
            'filename': file.filename
        }
        return redirect(url_for('admin.question_preview'))

    except Exception as e:
        flash(f"Error reading uploaded file: {str(e)}", "danger")
        return redirect(url_for('admin.questions', tab=category))

@admin_bp.route('/questions/preview')
def question_preview():
    staging = session.get('question_upload_staging')
    if not staging:
        flash("No uploaded questions found in review buffer.", "warning")
        return redirect(url_for('admin.questions'))

    target_assessment = None
    if staging.get('assessment_id'):
        target_assessment = Assessment.query.get(staging['assessment_id'])

    category = staging.get('category', 'mcq')
    category_info = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG['mcq'])

    return render_template(
        'admin/question_preview.html',
        category=category,
        category_info=category_info,
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

    category = staging.get('category', 'mcq')
    assessment_id = staging.get('assessment_id')
    saved_count, error = save_imported_questions(staging['questions'], category=category, assessment_id=assessment_id)

    if error:
        flash(error, "danger")
        return redirect(url_for('admin.question_preview'))

    session.pop('question_upload_staging', None)
    cat_name = CATEGORY_CONFIG.get(category, {}).get('name', 'Questions')
    flash(f"Successfully validated and saved {saved_count} {cat_name} questions into the question bank.", "success")
    return redirect(url_for('admin.questions', tab=category, assessment_id=assessment_id if assessment_id else ''))

# -------------------------------------------------------------
# Coding Questions Add / Edit / Delete
# -------------------------------------------------------------
@admin_bp.route('/questions/coding/new', methods=['GET', 'POST'])
def coding_question_new():
    all_assessments = Assessment.query.order_by(Assessment.title.asc()).all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        problem_statement = request.form.get('problem_statement', '').strip()
        input_description = request.form.get('input_description', '').strip()
        output_description = request.form.get('output_description', '').strip()
        constraints = request.form.get('constraints', '').strip()
        sample_input = request.form.get('sample_input', '').strip()
        sample_output = request.form.get('sample_output', '').strip()
        difficulty = request.form.get('difficulty', 'MEDIUM').strip()
        category = request.form.get('category', 'Algorithms').strip()
        assessment_id = request.form.get('assessment_id', type=int)

        # Languages supported
        langs_input = request.form.getlist('languages_supported')
        if not langs_input:
            raw_langs = request.form.get('languages_custom', '')
            if raw_langs:
                langs_input = [x.strip() for x in raw_langs.split(',') if x.strip()]
            else:
                langs_input = ["Python", "Java", "C++", "JavaScript", "C"]

        # Test cases
        test_cases_raw = request.form.get('test_cases', '').strip()
        test_cases = []
        if test_cases_raw:
            try:
                test_cases = json.loads(test_cases_raw)
                if not isinstance(test_cases, list):
                    flash("Test cases must be a JSON array of objects with 'input' and 'expected_output'.", "danger")
                    return render_template('admin/coding_question_form.html', question=None, assessments=all_assessments, form_data=request.form)
            except Exception as e:
                flash(f"Invalid JSON format for test cases: {str(e)}", "danger")
                return render_template('admin/coding_question_form.html', question=None, assessments=all_assessments, form_data=request.form)

        if not test_cases:
            if sample_input and sample_output:
                test_cases = [{"input": sample_input, "expected_output": sample_output, "is_hidden": False}]
            else:
                flash("At least one test case or sample input/output is required.", "danger")
                return render_template('admin/coding_question_form.html', question=None, assessments=all_assessments, form_data=request.form)

        if not title or len(title) < 3:
            flash("Title must be at least 3 characters long.", "danger")
            return render_template('admin/coding_question_form.html', question=None, assessments=all_assessments, form_data=request.form)

        if not problem_statement or len(problem_statement) < 10:
            flash("Problem statement must be at least 10 characters long.", "danger")
            return render_template('admin/coding_question_form.html', question=None, assessments=all_assessments, form_data=request.form)

        coding_q = CodingQuestion(
            title=title,
            problem_statement=problem_statement,
            input_description=input_description,
            output_description=output_description,
            constraints=constraints,
            sample_input=sample_input,
            sample_output=sample_output,
            languages_supported=langs_input,
            test_cases=test_cases,
            points=15.0, # Strictly 15 marks
            difficulty=difficulty,
            category=category,
            assessment_id=assessment_id if assessment_id else None,
            section='CODING',
            is_active=True
        )
        db.session.add(coding_q)
        db.session.commit()
        flash("Coding question created successfully (15 marks allocated).", "success")
        return redirect(url_for('admin.questions', tab='coding'))

    return render_template('admin/coding_question_form.html', question=None, assessments=all_assessments, form_data={})

@admin_bp.route('/questions/coding/<int:question_id>/edit', methods=['GET', 'POST'])
def coding_question_edit(question_id):
    question = CodingQuestion.query.get_or_404(question_id)
    all_assessments = Assessment.query.order_by(Assessment.title.asc()).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        problem_statement = request.form.get('problem_statement', '').strip()
        input_description = request.form.get('input_description', '').strip()
        output_description = request.form.get('output_description', '').strip()
        constraints = request.form.get('constraints', '').strip()
        sample_input = request.form.get('sample_input', '').strip()
        sample_output = request.form.get('sample_output', '').strip()
        difficulty = request.form.get('difficulty', 'MEDIUM').strip()
        category = request.form.get('category', 'Algorithms').strip()
        assessment_id = request.form.get('assessment_id', type=int)

        langs_input = request.form.getlist('languages_supported')
        if not langs_input:
            raw_langs = request.form.get('languages_custom', '')
            if raw_langs:
                langs_input = [x.strip() for x in raw_langs.split(',') if x.strip()]
            else:
                langs_input = question.languages_supported or ["Python", "Java", "C++"]

        test_cases_raw = request.form.get('test_cases', '').strip()
        test_cases = question.test_cases or []
        if test_cases_raw:
            try:
                test_cases = json.loads(test_cases_raw)
                if not isinstance(test_cases, list):
                    flash("Test cases must be a JSON array of objects.", "danger")
                    return render_template('admin/coding_question_form.html', question=question, assessments=all_assessments, form_data=request.form)
            except Exception as e:
                flash(f"Invalid JSON format for test cases: {str(e)}", "danger")
                return render_template('admin/coding_question_form.html', question=question, assessments=all_assessments, form_data=request.form)

        question.title = title
        question.problem_statement = problem_statement
        question.input_description = input_description
        question.output_description = output_description
        question.constraints = constraints
        question.sample_input = sample_input
        question.sample_output = sample_output
        question.languages_supported = langs_input
        question.test_cases = test_cases
        question.points = 15.0 # Strict
        question.difficulty = difficulty
        question.category = category
        question.assessment_id = assessment_id if assessment_id else None

        db.session.commit()
        flash("Coding question updated successfully.", "success")
        return redirect(url_for('admin.questions', tab='coding'))

    return render_template('admin/coding_question_form.html', question=question, assessments=all_assessments, form_data={})

@admin_bp.route('/questions/coding/<int:question_id>/delete', methods=['POST'])
def coding_question_delete(question_id):
    question = CodingQuestion.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    flash("Coding question deleted successfully.", "info")
    return redirect(url_for('admin.questions', tab='coding'))

# -------------------------------------------------------------
# Aptitude & Technical MCQ Add / Edit / Delete
# -------------------------------------------------------------
@admin_bp.route('/questions/aptitude/new', methods=['GET', 'POST'])
def aptitude_question_new():
    all_assessments = Assessment.query.order_by(Assessment.title.asc()).all()
    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        topic = request.form.get('category', 'General Aptitude').strip()
        difficulty = request.form.get('difficulty', 'MEDIUM')
        correct_option = request.form.get('correct_option', 'A').strip().upper()
        explanation = request.form.get('explanation', '').strip()
        assessment_id = request.form.get('assessment_id', type=int)

        options = [
            {"id": "A", "text": request.form.get('opt_A', '').strip()},
            {"id": "B", "text": request.form.get('opt_B', '').strip()},
            {"id": "C", "text": request.form.get('opt_C', '').strip()},
            {"id": "D", "text": request.form.get('opt_D', '').strip()}
        ]

        if not question_text or len(question_text) < 5:
            flash("Question text must be at least 5 characters.", "danger")
            return render_template('admin/question_form.html', question=None, section='APTITUDE', assessments=all_assessments, form_data=request.form)

        for opt in options:
            if not opt['text']:
                flash(f"Option {opt['id']} text is required.", "danger")
                return render_template('admin/question_form.html', question=None, section='APTITUDE', assessments=all_assessments, form_data=request.form)

        q = Question(
            question_text=question_text,
            question_type='MCQ',
            section='APTITUDE',
            options=options,
            correct_option=correct_option,
            explanation=explanation,
            points=2.0, # Strictly 2 marks for Aptitude
            difficulty=difficulty,
            category=topic,
            assessment_id=assessment_id if assessment_id else None,
            is_active=True
        )
        db.session.add(q)
        db.session.commit()
        flash("Aptitude question created successfully (2 marks allocated).", "success")
        return redirect(url_for('admin.questions', tab='aptitude'))

    return render_template('admin/question_form.html', question=None, section='APTITUDE', assessments=all_assessments, form_data={})

@admin_bp.route('/questions/mcq/new', methods=['GET', 'POST'])
def mcq_question_new():
    all_assessments = Assessment.query.order_by(Assessment.title.asc()).all()
    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        category = request.form.get('category', 'General').strip()
        difficulty = request.form.get('difficulty', 'MEDIUM')
        correct_option = request.form.get('correct_option', 'A').strip().upper()
        explanation = request.form.get('explanation', '').strip()
        assessment_id = request.form.get('assessment_id', type=int)

        options = [
            {"id": "A", "text": request.form.get('opt_A', '').strip()},
            {"id": "B", "text": request.form.get('opt_B', '').strip()},
            {"id": "C", "text": request.form.get('opt_C', '').strip()},
            {"id": "D", "text": request.form.get('opt_D', '').strip()}
        ]

        if not question_text or len(question_text) < 5:
            flash("Question text must be at least 5 characters.", "danger")
            return render_template('admin/question_form.html', question=None, section='MCQ', assessments=all_assessments, form_data=request.form)

        for opt in options:
            if not opt['text']:
                flash(f"Option {opt['id']} text is required.", "danger")
                return render_template('admin/question_form.html', question=None, section='MCQ', assessments=all_assessments, form_data=request.form)

        q = Question(
            question_text=question_text,
            question_type='MCQ',
            section='MCQ',
            options=options,
            correct_option=correct_option,
            explanation=explanation,
            points=1.0, # Strictly 1 mark for Technical MCQ
            difficulty=difficulty,
            category=category,
            assessment_id=assessment_id if assessment_id else None,
            is_active=True
        )
        db.session.add(q)
        db.session.commit()
        flash("Technical MCQ question created successfully (1 mark allocated).", "success")
        return redirect(url_for('admin.questions', tab='mcq'))

    return render_template('admin/question_form.html', question=None, section='MCQ', assessments=all_assessments, form_data={})

@admin_bp.route('/questions/<int:question_id>/edit', methods=['GET', 'POST'])
def question_edit(question_id):
    question = Question.query.get_or_404(question_id)
    all_assessments = Assessment.query.order_by(Assessment.title.asc()).all()
    section = question.section or 'MCQ'

    if request.method == 'POST':
        question_text = request.form.get('question_text')
        assessment_id = request.form.get('assessment_id', type=int)
        difficulty = request.form.get('difficulty', 'MEDIUM')
        category = request.form.get('category', 'General')
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
        # Fixed points: 2.0 for Aptitude, 1.0 for MCQ
        question.points = 2.0 if question.section == 'APTITUDE' else 1.0
        question.difficulty = difficulty
        question.category = category

        db.session.commit()
        cat_tab = 'aptitude' if question.section == 'APTITUDE' else 'mcq'
        flash(f"{'Aptitude' if question.section == 'APTITUDE' else 'MCQ'} question updated successfully.", "success")
        return redirect(url_for('admin.questions', tab=cat_tab))

    return render_template('admin/question_form.html', question=question, section=section, assessments=all_assessments)

@admin_bp.route('/questions/<int:question_id>/delete', methods=['POST'])
def question_delete(question_id):
    question = Question.query.get_or_404(question_id)
    cat_tab = 'aptitude' if question.section == 'APTITUDE' else 'mcq'
    db.session.delete(question)
    db.session.commit()
    flash(f"{'Aptitude' if cat_tab == 'aptitude' else 'MCQ'} question successfully deleted from the bank.", "info")
    return redirect(url_for('admin.questions', tab=cat_tab))

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

# -------------------------------------------------------------
# 9. Email Template Management & Recruitment Lifecycle Mappings
# -------------------------------------------------------------
@admin_bp.route('/templates')
def templates():
    """
    Centralized Email Template Management page.
    Resolves previous 404 issue and provides templates repository, event mappings, and queue.
    """
    tab = request.args.get('tab', 'templates').lower()
    search = request.args.get('search')
    category = request.args.get('category')
    status = request.args.get('status')

    all_templates = get_all_templates(search=search, category=category, status=status)
    mappings = get_all_event_mappings()
    queue_jobs = get_email_queue_jobs(limit=50)
    stats = get_email_dashboard_stats()

    # Active templates for mapping dropdowns
    active_templates = [t for t in all_templates if t.is_active]
    if not active_templates:
        active_templates = EmailTemplate.query.filter_by(is_active=True).order_by(EmailTemplate.name.asc()).all()

    return render_template(
        'admin/templates.html',
        active_tab=tab,
        templates=all_templates,
        active_templates=active_templates,
        mappings=mappings,
        queue_jobs=queue_jobs,
        stats=stats,
        search_query=search,
        selected_category=category,
        selected_status=status
    )

@admin_bp.route('/templates/new', methods=['GET', 'POST'])
def template_new():
    """Create a new email template with unique name validation."""
    if request.method == 'POST':
        name = request.form.get('name')
        subject = request.form.get('subject')
        body = request.form.get('body')
        category = request.form.get('category', 'RECRUITMENT')
        is_active = bool(request.form.get('is_active'))

        template, error = create_email_template(
            name=name,
            subject=subject,
            body=body,
            category=category,
            is_active=is_active
        )
        if error:
            flash(error, "danger")
            return render_template('admin/template_form.html', template=None, form_data=request.form)

        flash(f"Email template '{template.name}' created successfully.", "success")
        return redirect(url_for('admin.templates'))

    return render_template('admin/template_form.html', template=None, form_data={'is_active': True, 'category': 'RECRUITMENT'})

@admin_bp.route('/templates/<int:template_id>/edit', methods=['GET', 'POST'])
def template_edit(template_id):
    """Edit existing email template. Preserves event mappings."""
    template = get_template_by_id(template_id)
    if not template:
        flash("Email template not found.", "warning")
        return redirect(url_for('admin.templates'))

    if request.method == 'POST':
        name = request.form.get('name')
        subject = request.form.get('subject')
        body = request.form.get('body')
        category = request.form.get('category')
        is_active = bool(request.form.get('is_active'))

        updated_t, error = update_email_template(
            template_id=template.id,
            name=name,
            subject=subject,
            body=body,
            category=category,
            is_active=is_active
        )
        if error:
            flash(error, "danger")
            return render_template('admin/template_form.html', template=template, form_data=request.form)

        flash(f"Email template '{updated_t.name}' updated successfully.", "success")
        return redirect(url_for('admin.templates'))

    return render_template('admin/template_form.html', template=template, form_data=template.__dict__)

@admin_bp.route('/templates/<int:template_id>/duplicate', methods=['POST'])
def template_duplicate(template_id):
    """Duplicates an existing template with a unique name."""
    duplicate, error = duplicate_email_template(template_id)
    if error:
        flash(error, "danger")
    else:
        flash(f"Template duplicated successfully as '{duplicate.name}'.", "success")
    return redirect(url_for('admin.templates'))

@admin_bp.route('/templates/<int:template_id>/toggle', methods=['POST'])
def template_toggle(template_id):
    """Toggles active/inactive status."""
    template, error = toggle_email_template_status(template_id)
    if error:
        flash(error, "danger")
    else:
        state = "activated" if template.is_active else "deactivated"
        flash(f"Template '{template.name}' has been {state}.", "info")
    return redirect(url_for('admin.templates'))

@admin_bp.route('/templates/<int:template_id>/delete', methods=['POST'])
def template_delete(template_id):
    """Deletes template and safely detaches it from mappings."""
    template = get_template_by_id(template_id)
    name = template.name if template else "Template"
    success, error = delete_email_template(template_id)
    if error:
        flash(error, "danger")
    else:
        flash(f"Email template '{name}' deleted successfully.", "info")
    return redirect(url_for('admin.templates'))

@admin_bp.route('/templates/<int:template_id>/preview')
def template_preview(template_id):
    """Preview rendered email template with mock candidate data."""
    template = get_template_by_id(template_id)
    if not template:
        flash("Email template not found.", "warning")
        return redirect(url_for('admin.templates'))

    mock_context = {
        'candidate_name': 'Alex Vance',
        'application_id': 'AM-2026-APP-8842',
        'job_title': 'Software Engineering Intern',
        'company_name': 'Anti-Matrix'
    }

    rendered_subject = render_template_placeholders(template.subject, mock_context)
    rendered_body = render_template_placeholders(template.body, mock_context)

    return render_template(
        'admin/template_preview.html',
        template=template,
        rendered_subject=rendered_subject,
        rendered_body=rendered_body,
        mock_context=mock_context
    )

@admin_bp.route('/templates/mappings/update', methods=['POST'])
def event_mapping_update():
    """Update event mapping configuration (template ID, delay minutes, automation toggle)."""
    event_key = request.form.get('event_key')
    template_id = request.form.get('template_id', type=int)
    delay_minutes = request.form.get('delay_minutes', 0, type=int)
    is_automated = bool(request.form.get('is_automated'))

    mapping, error = update_event_mapping(
        event_key=event_key,
        template_id=template_id,
        delay_minutes=delay_minutes,
        is_automated=is_automated
    )
    if error:
        flash(error, "danger")
    else:
        t_name = mapping.template.name if mapping.template else "Unassigned"
        auto_str = "Automated" if mapping.is_automated else "Paused"
        flash(f"Mapping for '{mapping.event_name}' updated: Template '{t_name}' ({mapping.delay_minutes}m delay, {auto_str}).", "success")

    return redirect(url_for('admin.templates', tab='mappings'))

@admin_bp.route('/templates/queue/process', methods=['POST'])
def process_email_queue():
    """Manually trigger dispatch of eligible scheduled email jobs."""
    processed = process_pending_email_jobs()
    flash(f"Dispatched {processed} scheduled email job(s) from queue.", "info")
    return redirect(url_for('admin.templates', tab='queue'))
