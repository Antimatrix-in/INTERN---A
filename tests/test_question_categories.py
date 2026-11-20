import json
import pytest
from models import db, Question, CodingQuestion, Assessment, User
from services import (
    get_coding_template,
    get_aptitude_template,
    get_mcq_template,
    get_sample_json_template,
    parse_and_validate_question_json,
    save_imported_questions,
    get_question_bank_stats,
    CATEGORY_CONFIG
)

def test_category_configuration_constants():
    """Verify approved mark and question allocations per category."""
    # Coding: 4 questions, 15 marks each, 60 total
    assert CATEGORY_CONFIG['coding']['target_questions'] == 4
    assert CATEGORY_CONFIG['coding']['marks_per_question'] == 15.0
    assert CATEGORY_CONFIG['coding']['total_marks'] == 60.0

    # Aptitude: 10 questions, 2 marks each, 20 total
    assert CATEGORY_CONFIG['aptitude']['target_questions'] == 10
    assert CATEGORY_CONFIG['aptitude']['marks_per_question'] == 2.0
    assert CATEGORY_CONFIG['aptitude']['total_marks'] == 20.0

    # Technical MCQ: 20 questions, 1 mark each, 20 total
    assert CATEGORY_CONFIG['mcq']['target_questions'] == 20
    assert CATEGORY_CONFIG['mcq']['marks_per_question'] == 1.0
    assert CATEGORY_CONFIG['mcq']['total_marks'] == 20.0

def test_question_bank_stats_and_combined_summary(app, test_assessment_id):
    """Test category count and combined assessment summary (34 questions, 100 marks)."""
    with app.app_context():
        # Insert 1 coding question (15 marks)
        cq = CodingQuestion(
            title="Reverse Linked List",
            problem_statement="Reverse a singly linked list in-place.",
            languages_supported=["Python", "C++"],
            test_cases=[{"input": "1->2->3", "expected_output": "3->2->1", "is_hidden": False}],
            points=15.0,
            assessment_id=test_assessment_id,
            section='CODING',
            is_active=True
        )
        db.session.add(cq)

        # Insert 1 aptitude question (2 marks)
        aq = Question(
            question_text="A can do a work in 15 days and B in 20 days. How long working together?",
            question_type='MCQ',
            section='APTITUDE',
            options=[
                {"id": "A", "text": "8.5 days"},
                {"id": "B", "text": "60/7 days"},
                {"id": "C", "text": "9 days"},
                {"id": "D", "text": "10 days"}
            ],
            correct_option="B",
            points=2.0,
            category="Time & Work",
            assessment_id=test_assessment_id,
            is_active=True
        )
        db.session.add(aq)

        # Insert 1 technical MCQ question (1 mark)
        mq = Question(
            question_text="Which SQL clause is used to filter aggregated group rows?",
            question_type='MCQ',
            section='MCQ',
            options=[
                {"id": "A", "text": "WHERE"},
                {"id": "B", "text": "HAVING"},
                {"id": "C", "text": "GROUP BY"},
                {"id": "D", "text": "ORDER BY"}
            ],
            correct_option="B",
            points=1.0,
            category="Databases",
            assessment_id=test_assessment_id,
            is_active=True
        )
        db.session.add(mq)
        db.session.commit()

        stats = get_question_bank_stats(test_assessment_id)
        assert stats['coding']['count'] == 1
        assert stats['coding']['marks_per_question'] == 15
        assert stats['aptitude']['count'] == 1
        assert stats['aptitude']['marks_per_question'] == 2
        # test_assessment_id already had 1 MCQ from conftest + 1 added here = 2
        assert stats['mcq']['count'] >= 2
        assert stats['mcq']['marks_per_question'] == 1

        # Combined assessment specification target
        assert stats['overall']['total_target_questions'] == 34
        assert stats['overall']['total_target_marks'] == 100

def test_coding_question_json_validation_and_persistence(app, test_assessment_id):
    """Test validation and batch save for Coding questions (15 marks)."""
    with app.app_context():
        template_data = get_coding_template()
        json_str = json.dumps(template_data)

        # 1. Validate valid JSON
        sanitized, errors = parse_and_validate_question_json(json_str, category='coding')
        assert errors is None
        assert len(sanitized) == 2
        for item in sanitized:
            assert item['section'] == 'CODING'
            assert item['points'] == 15.0
            assert len(item['test_cases']) > 0

        # 2. Persist to database
        saved_count, save_err = save_imported_questions(sanitized, category='coding', assessment_id=test_assessment_id)
        assert save_err is None
        assert saved_count == 2

        # 3. Check duplicate prevention
        saved_count2, save_err2 = save_imported_questions(sanitized, category='coding', assessment_id=test_assessment_id)
        assert save_err2 is None
        assert saved_count2 == 0  # Ignored as duplicates

        # 4. Invalid coding JSON: wrong marks (e.g. 10 instead of 15)
        bad_coding = [
            {
                "title": "Invalid Marks Problem",
                "problem_statement": "A problem statement that has invalid marks.",
                "test_cases": [{"input": "1", "expected_output": "1"}],
                "marks": 10
            }
        ]
        bad_res, bad_errs = parse_and_validate_question_json(json.dumps(bad_coding), category='coding')
        assert bad_res is None
        assert any("must be exactly 15 marks" in e for e in bad_errs)

def test_aptitude_question_json_validation_and_persistence(app, test_assessment_id):
    """Test validation and batch save for Aptitude questions (2 marks)."""
    with app.app_context():
        template_data = get_aptitude_template()
        json_str = json.dumps(template_data)

        sanitized, errors = parse_and_validate_question_json(json_str, category='aptitude')
        assert errors is None
        assert len(sanitized) == 2
        for item in sanitized:
            assert item['section'] == 'APTITUDE'
            assert item['points'] == 2.0

        saved_count, save_err = save_imported_questions(sanitized, category='aptitude', assessment_id=test_assessment_id)
        assert save_err is None
        assert saved_count == 2

        # Invalid aptitude marks (e.g. 5 marks instead of 2)
        bad_apt = [
            {
                "question_text": "Aptitude question with invalid marks?",
                "options": [
                    {"id": "A", "text": "1"}, {"id": "B", "text": "2"},
                    {"id": "C", "text": "3"}, {"id": "D", "text": "4"}
                ],
                "correct_option": "A",
                "marks": 5
            }
        ]
        bad_res, bad_errs = parse_and_validate_question_json(json.dumps(bad_apt), category='aptitude')
        assert bad_res is None
        assert any("must be exactly 2 mark(s)" in e for e in bad_errs)

def test_mcq_question_json_validation_and_persistence(app, test_assessment_id):
    """Test validation and batch save for Technical MCQ questions (1 mark)."""
    with app.app_context():
        template_data = get_mcq_template()
        json_str = json.dumps(template_data)

        sanitized, errors = parse_and_validate_question_json(json_str, category='mcq')
        assert errors is None
        assert len(sanitized) == 2
        for item in sanitized:
            assert item['section'] == 'MCQ'
            assert item['points'] == 1.0

        saved_count, save_err = save_imported_questions(sanitized, category='mcq', assessment_id=test_assessment_id)
        assert save_err is None
        assert saved_count == 2

def test_template_download_endpoints(client, admin_user_id):
    """Test official template downloads for Coding, Aptitude, and Technical MCQ."""
    # Login as admin
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user_id)
        sess['_fresh'] = True

    # 1. Coding template
    resp_coding = client.get('/admin/questions/template?category=coding')
    assert resp_coding.status_code == 200
    assert 'attachment;filename=coding_questions_template.json' in resp_coding.headers['Content-Disposition']
    data_coding = json.loads(resp_coding.data)
    assert isinstance(data_coding, list)
    assert 'problem_statement' in data_coding[0]

    # 2. Aptitude template
    resp_apt = client.get('/admin/questions/template?category=aptitude')
    assert resp_apt.status_code == 200
    assert 'attachment;filename=aptitude_questions_template.json' in resp_apt.headers['Content-Disposition']
    data_apt = json.loads(resp_apt.data)
    assert isinstance(data_apt, list)
    assert data_apt[0]['marks'] == 2

    # 3. MCQ template
    resp_mcq = client.get('/admin/questions/template?category=mcq')
    assert resp_mcq.status_code == 200
    assert 'attachment;filename=mcq_questions_template.json' in resp_mcq.headers['Content-Disposition']
    data_mcq = json.loads(resp_mcq.data)
    assert isinstance(data_mcq, list)
    assert data_mcq[0]['marks'] == 1

def test_admin_question_bank_ui_tabs(client, admin_user_id):
    """Test question bank UI navigation across Coding, Aptitude, and Technical MCQ tabs."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user_id)
        sess['_fresh'] = True

    for tab in ['coding', 'aptitude', 'mcq']:
        resp = client.get(f'/admin/questions?tab={tab}')
        assert resp.status_code == 200
        # Check presence of the 3 cards and combined summary
        assert b"Combined Assessment Summary" in resp.data
        assert b"34" in resp.data
        assert b"100" in resp.data
        assert b"Coding" in resp.data
        assert b"Aptitude" in resp.data
        assert b"Technical MCQ" in resp.data

def test_coding_crud_routes(client, admin_user_id, test_assessment_id):
    """Test Add, Edit, Delete routes for Coding questions."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user_id)
        sess['_fresh'] = True

    # 1. Add coding question
    post_data = {
        'title': 'Binary Search Peak Element',
        'problem_statement': 'Find a peak element in an array where nums[i] > nums[i+1].',
        'input_description': 'Array of integers',
        'output_description': 'Index of peak element',
        'constraints': '1 <= n <= 10^5',
        'sample_input': '4\n1 2 3 1',
        'sample_output': '2',
        'difficulty': 'MEDIUM',
        'category': 'Algorithms',
        'assessment_id': str(test_assessment_id),
        'languages_supported': ['Python', 'Java', 'C++'],
        'test_cases': json.dumps([{"input": "4\n1 2 3 1", "expected_output": "2", "is_hidden": False}])
    }
    resp = client.post('/admin/questions/coding/new', data=post_data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Coding question created successfully" in resp.data

    # Verify in db
    with client.application.app_context():
        created_q = CodingQuestion.query.filter_by(title='Binary Search Peak Element').first()
        assert created_q is not None
        assert created_q.points == 15.0
        q_id = created_q.id

    # 2. Edit coding question
    edit_data = post_data.copy()
    edit_data['title'] = 'Binary Search Peak Element Updated'
    resp_edit = client.post(f'/admin/questions/coding/{q_id}/edit', data=edit_data, follow_redirects=True)
    assert resp_edit.status_code == 200
    assert b"Coding question updated successfully" in resp_edit.data

    with client.application.app_context():
        updated_q = db.session.get(CodingQuestion, q_id)
        assert updated_q.title == 'Binary Search Peak Element Updated'

    # 3. Delete coding question
    resp_del = client.post(f'/admin/questions/coding/{q_id}/delete', follow_redirects=True)
    assert resp_del.status_code == 200
    assert b"Coding question deleted successfully" in resp_del.data

    with client.application.app_context():
        assert db.session.get(CodingQuestion, q_id) is None
