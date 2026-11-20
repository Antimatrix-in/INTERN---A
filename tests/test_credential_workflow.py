import pytest
import json
from datetime import datetime, timezone, timedelta
from models import db, User, Assessment, Credential, EmailTemplate
from services import find_candidate_by_id, create_candidate_credential, send_credential_email

@pytest.fixture
def sample_candidate(app):
    """Creates a sample candidate with a generic candidate ID."""
    with app.app_context():
        cand = User(
            user_id='CAND-001',
            username='cand001',
            email='john.doe@example.com',
            full_name='John Doe',
            role='CANDIDATE',
            is_active=True
        )
        cand.set_password('OldInitialPass!')
        db.session.add(cand)
        db.session.commit()
        return cand.id

def test_candidate_lookup_valid_and_invalid(client, admin_user_id, sample_candidate):
    """Test Step 1 & 2: Lookup candidate by generic ID and return details or error."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user_id)
        sess['_fresh'] = True

    # 1. Valid Candidate Lookup
    res = client.get('/admin/candidates/lookup?candidate_id=CAND-001')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['candidate']['user_id'] == 'CAND-001'
    assert data['candidate']['full_name'] == 'John Doe'
    assert data['candidate']['email'] == 'john.doe@example.com'
    assert data['has_active_credential'] is False

    # 2. Case-insensitive / Username lookup
    res_lower = client.get('/admin/candidates/lookup?candidate_id=cand-001')
    assert res_lower.status_code == 200
    assert res_lower.get_json()['success'] is True

    # 3. Invalid Candidate Lookup
    res_inv = client.get('/admin/candidates/lookup?candidate_id=NONEXISTENT-999')
    assert res_inv.status_code == 404
    data_inv = res_inv.get_json()
    assert data_inv['success'] is False
    assert "Candidate not found. Please check the Candidate ID." in data_inv['message']

def test_generate_credentials_workflow_and_persistence(client, app, admin_user_id, sample_candidate, test_assessment_id):
    """Test Step 3: Automatic credential generation, 48h expiry, and hash storage."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user_id)
        sess['_fresh'] = True

    # Generate credentials for CAND-001
    post_payload = {
        'candidate_id': 'CAND-001',
        'assessment_id': test_assessment_id
    }
    res = client.post('/admin/credentials/create',
                      data=json.dumps(post_payload),
                      content_type='application/json')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    cred_info = data['credential']

    assert cred_info['candidate_id'] == 'CAND-001'
    assert cred_info['candidate_name'] == 'John Doe'
    assert cred_info['login_user_id'] == 'CAND-001'
    assert cred_info['password'] is not None
    assert len(cred_info['password']) >= 12
    assert cred_info['validity'] == '48 Hours'
    assert cred_info['email_status'] == 'PENDING'

    # Verify Database Persistence
    with app.app_context():
        cand = db.session.get(User, sample_candidate)
        assert cand.credential is not None
        cred = cand.credential
        assert cred.assessment_id == test_assessment_id
        assert cred.status == 'ACTIVE'
        assert cred.email_status == 'PENDING'

        # Verify password is hash-stored, not plain text
        assert cand.check_password(cred_info['password']) is True
        assert cand.password_hash != cred_info['password']

        # Verify strict 48-hour expiration
        diff = cred.expires_at - cred.created_at
        assert abs(diff.total_seconds() - 48 * 3600) < 5

def test_prevent_duplicate_credential_generation(client, admin_user_id, sample_candidate, test_assessment_id):
    """Test duplicate active credential prevention for the same assessment."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user_id)
        sess['_fresh'] = True

    post_payload = {
        'candidate_id': 'CAND-001',
        'assessment_id': test_assessment_id
    }

    # First generation -> succeeds
    res1 = client.post('/admin/credentials/create',
                       data=json.dumps(post_payload),
                       content_type='application/json')
    assert res1.status_code == 200

    # Second generation for same assessment while active -> must be blocked
    res2 = client.post('/admin/credentials/create',
                       data=json.dumps(post_payload),
                       content_type='application/json')
    assert res2.status_code == 400
    data2 = res2.get_json()
    assert data2['success'] is False
    assert "Candidate already has an active credential for this assessment." in data2['message']

def test_page_refresh_does_not_duplicate_credentials(client, app, admin_user_id, sample_candidate, test_assessment_id):
    """Test that refreshing or reloading the page displays credentials without duplicating."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user_id)
        sess['_fresh'] = True

    # Generate initial credential via POST
    res = client.post('/admin/credentials/create',
                      data=json.dumps({'candidate_id': 'CAND-001', 'assessment_id': test_assessment_id}),
                      content_type='application/json')
    assert res.status_code == 200
    cred_id = res.get_json()['credential']['id']

    # Refresh page with GET request
    get_res = client.get(f'/admin/credentials/create?credential_id={cred_id}')
    assert get_res.status_code == 200
    assert b"Generated Credentials" in get_res.data
    assert b"CAND-001" in get_res.data

    # Verify count of credentials in DB remains exactly 1
    with app.app_context():
        count = Credential.query.filter_by(user_id=sample_candidate).count()
        assert count == 1

def test_send_credentials_email_workflow(client, app, admin_user_id, sample_candidate, test_assessment_id):
    """Test Step 4 & 5: Email delivery, placeholder replacement, delivery status, and resend protection."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user_id)
        sess['_fresh'] = True

    # 1. Generate credentials
    res = client.post('/admin/credentials/create',
                      data=json.dumps({'candidate_id': 'CAND-001', 'assessment_id': test_assessment_id}),
                      content_type='application/json')
    cred_id = res.get_json()['credential']['id']

    # 2. Dispatch email
    email_res = client.post(f'/admin/credentials/{cred_id}/send-email',
                            data=json.dumps({'resend': False}),
                            content_type='application/json')
    assert email_res.status_code == 200
    data = email_res.get_json()
    assert data['success'] is True
    assert data['email_status'] == 'SENT'
    assert data['email_sent_at'] is not None

    # Verify in DB
    with app.app_context():
        cred = db.session.get(Credential, cred_id)
        assert cred.email_status == 'SENT'
        assert cred.email_sent_at is not None

    # 3. Duplicate send without resend flag must be prevented
    dup_res = client.post(f'/admin/credentials/{cred_id}/send-email',
                          data=json.dumps({'resend': False}),
                          content_type='application/json')
    assert dup_res.status_code == 400
    assert "already been sent" in dup_res.get_json()['message']

    # 4. Controlled Resend with resend=True succeeds
    resend_res = client.post(f'/admin/credentials/{cred_id}/send-email',
                             data=json.dumps({'resend': True}),
                             content_type='application/json')
    assert resend_res.status_code == 200
    assert resend_res.get_json()['success'] is True
