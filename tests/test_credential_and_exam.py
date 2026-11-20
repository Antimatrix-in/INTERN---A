import pytest
import uuid
from datetime import datetime, timezone, timedelta
from models import db, User, Credential, Attempt, AttemptAnswer, Assessment, Question
from services import (
    create_candidate_credential,
    start_or_resume_examination,
    autosave_attempt_answer,
    submit_examination
)

def test_credential_creation_rules(app, test_assessment_id):
    """Test 48-hour expiration calculation, user ID generation, and hash storage."""
    u = uuid.uuid4().hex[:6]
    with app.app_context():
        cred, cand, raw_pwd, err = create_candidate_credential(
            full_name=f"Bob Smith {u}",
            email=f"bob.smith.{u}@example.com",
            assessment_id=test_assessment_id
        )
        assert err is None
        assert cred is not None
        assert cand is not None
        assert cand.user_id.startswith("AM-")
        assert cand.check_password(raw_pwd) is True
        # Plain text password is NEVER stored in database
        assert cand.password_hash != raw_pwd

        # Exactly 48 hours expiry
        expected_diff = timedelta(hours=48)
        actual_diff = cred.expires_at - cred.created_at
        assert abs(actual_diff.total_seconds() - expected_diff.total_seconds()) < 2
        assert cred.status == 'ACTIVE'
        assert cred.is_expired is False

def test_strict_48_hour_expiry_enforcement(app, test_assessment_id):
    """Test that after 48 hours, no new examination attempt may be started."""
    u = uuid.uuid4().hex[:6]
    with app.app_context():
        cred, cand, raw_pwd, err = create_candidate_credential(
            full_name=f"Expired Candidate {u}",
            email=f"expired.{u}@example.com",
            assessment_id=test_assessment_id
        )
        assert err is None

        # Simulate expiration by setting expires_at to 1 hour in the past (UTC)
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        cred.expires_at = past_time
        db.session.commit()

        assert cred.is_expired is True

        # Attempt to start exam must be rejected
        attempt, is_resumed, error = start_or_resume_examination(cand)
        assert attempt is None
        assert is_resumed is False
        assert "expired" in error.lower()
        assert cred.status == 'EXPIRED'

def test_one_attempt_enforcement_and_resumption(app, test_assessment_id):
    """Test single attempt rule, interruption recovery, and no re-attempt after submission."""
    u = uuid.uuid4().hex[:6]
    with app.app_context():
        cred, cand, raw_pwd, err = create_candidate_credential(
            full_name=f"Charlie Brown {u}",
            email=f"charlie.{u}@example.com",
            assessment_id=test_assessment_id
        )
        assert err is None

        # 1. Start fresh attempt
        attempt1, is_resumed1, err1 = start_or_resume_examination(cand)
        assert err1 is None
        assert is_resumed1 is False
        assert attempt1.status == 'IN_PROGRESS'
        assert attempt1.credential_id == cred.id

        # Autosave an answer for question
        q = Question.query.filter_by(assessment_id=test_assessment_id).first()
        saved, save_err = autosave_attempt_answer(
            attempt_id=attempt1.id,
            candidate_id=cand.id,
            question_id=q.id,
            selected_option='B'
        )
        assert saved is True

        # 2. Simulate interruption and resume
        attempt2, is_resumed2, err2 = start_or_resume_examination(cand)
        assert err2 is None
        assert is_resumed2 is True
        assert attempt2.id == attempt1.id # Must be the EXACT same attempt!

        # Check saved answer was preserved
        ans = AttemptAnswer.query.filter_by(attempt_id=attempt2.id, question_id=q.id).first()
        assert ans.selected_option == 'B'

        # 3. Submit attempt
        result, sub_err = submit_examination(attempt1.id)
        assert sub_err is None
        assert result is not None
        assert result.score > 0
        assert attempt1.status == 'COMPLETED'
        assert cred.status == 'USED'

        # 4. Strict Enforcement: No fresh attempt after submission
        attempt3, is_resumed3, err3 = start_or_resume_examination(cand)
        assert attempt3 is None
        assert "already been submitted" in err3.lower() or "prohibited" in err3.lower()
