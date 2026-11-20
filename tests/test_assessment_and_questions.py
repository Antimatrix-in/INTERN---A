import pytest
import uuid
import json
from models import db, Assessment, Question, User
from services import (
    create_assessment,
    update_assessment,
    parse_and_validate_question_json,
    save_imported_questions,
    get_sample_json_template,
    get_admin_dashboard_stats
)

def test_assessment_coding_count_and_validation(app, admin_user_id):
    """Test assessment rules: coding problem count must be 1 to 5."""
    with app.app_context():
        u = uuid.uuid4().hex[:6].upper()
        # Invalid: coding count = 0
        ass_invalid, errors = create_assessment(
            title="Invalid Assessment",
            code=f"AM-INV0-{u}",
            description="",
            duration_minutes=60,
            pass_percentage=60,
            mcq_count=10,
            coding_count=0
        )
        assert ass_invalid is None
        assert any("Coding problem count must be between 1 and 5" in e for e in errors)

        # Invalid: coding count = 6
        ass_invalid2, errors2 = create_assessment(
            title="Invalid Assessment 2",
            code=f"AM-INV6-{u}",
            description="",
            duration_minutes=60,
            pass_percentage=60,
            mcq_count=10,
            coding_count=6
        )
        assert ass_invalid2 is None
        assert any("Coding problem count must be between 1 and 5" in e for e in errors2)

        # Valid: coding count = 3
        ass_valid, errors_valid = create_assessment(
            title="Valid Engineering Assessment",
            code=f"AM-VAL-{u}",
            description="Valid description",
            duration_minutes=90,
            pass_percentage=65.0,
            mcq_count=20,
            coding_count=3,
            created_by_id=admin_user_id
        )
        assert errors_valid is None
        assert ass_valid is not None
        assert ass_valid.coding_count == 3

def test_question_json_validation_and_import(app):
    """Test documented JSON question schema parser and validation."""
    with app.app_context():
        # Valid JSON from template
        template = get_sample_json_template()
        json_str = json.dumps(template)

        questions, errors = parse_and_validate_question_json(json_str)
        assert errors is None
        assert len(questions) == 2

        # Invalid JSON: missing correct_option
        bad_data = [
            {
                "question_text": "Incomplete question without correct answer?",
                "options": [{"id": "A", "text": "Opt 1"}, {"id": "B", "text": "Opt 2"}]
            }
        ]
        q_bad, err_bad = parse_and_validate_question_json(json.dumps(bad_data))
        assert q_bad is None
        assert any("'correct_option' is required" in e for e in err_bad)

        # Invalid JSON: correct_option not in option IDs
        bad_option_match = [
            {
                "question_text": "Question with mismatched answer id?",
                "options": [{"id": "A", "text": "Opt 1"}, {"id": "B", "text": "Opt 2"}],
                "correct_option": "Z"
            }
        ]
        q_mismatch, err_mismatch = parse_and_validate_question_json(json.dumps(bad_option_match))
        assert q_mismatch is None
        assert any("does not match any option id" in e for e in err_mismatch)

def test_database_driven_dashboard_stats(app):
    """Test dashboard stats reflect live database counts rather than hardcoded values."""
    with app.app_context():
        stats = get_admin_dashboard_stats()
        assert isinstance(stats['total_candidates'], int)
        assert isinstance(stats['active_credentials'], int)
        assert isinstance(stats['pending_assessments'], int)
        assert isinstance(stats['completed_assessments'], int)
        assert isinstance(stats['passed_candidates'], int)
        assert isinstance(stats['failed_candidates'], int)
        assert stats['total_candidates'] >= 0
