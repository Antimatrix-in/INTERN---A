import pytest
import uuid
from models import db, User
from services import create_candidate_credential

def test_admin_login_redirects_to_admin_dashboard(client, admin_user_id):
    """Test admin login redirects specifically to /admin/dashboard."""
    response = client.post('/login', data={
        'username': 'admin_test',
        'password': 'AdminPass123!'
    }, follow_redirects=False)

    assert response.status_code == 302
    assert response.location == '/admin/dashboard'

def test_candidate_login_redirects_to_candidate_dashboard(app, client, test_assessment_id):
    """Test candidate login redirects specifically to /candidate/dashboard."""
    u = uuid.uuid4().hex[:6]
    with app.app_context():
        cred, cand, raw_pwd, err = create_candidate_credential(
            full_name=f"Candidate Alpha {u}",
            email=f"candidate.{u}@example.com",
            assessment_id=test_assessment_id,
            custom_password="CandidatePass123!"
        )
        assert err is None
        cand_user_id = cand.user_id

    # Login using candidate user_id
    response = client.post('/login', data={
        'username': cand_user_id,
        'password': 'CandidatePass123!'
    }, follow_redirects=False)

    assert response.status_code == 302
    assert response.location == '/candidate/dashboard'

def test_candidate_cannot_access_admin_routes(app, client, test_assessment_id):
    """Role-based route protection: Candidates must NEVER access admin routes."""
    u = uuid.uuid4().hex[:6]
    with app.app_context():
        cred, cand, raw_pwd, err = create_candidate_credential(
            full_name=f"Restricted Candidate {u}",
            email=f"restricted.{u}@example.com",
            assessment_id=test_assessment_id,
            custom_password="CandidatePass123!"
        )
        assert err is None
        cand_user_id = cand.user_id

    client.post('/login', data={
        'username': cand_user_id,
        'password': 'CandidatePass123!'
    })

    # Try accessing admin dashboard
    response = client.get('/admin/dashboard')
    assert response.status_code == 403

    # Try accessing admin credential manager
    response_cred = client.get('/admin/credentials')
    assert response_cred.status_code == 403

def test_unauthenticated_user_redirected_to_login(client):
    """Unauthenticated users must be redirected to login page."""
    response = client.get('/admin/dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.location

    response_cand = client.get('/candidate/dashboard', follow_redirects=False)
    assert response_cand.status_code == 302
    assert '/login' in response_cand.location

def test_login_invalid_credentials(client):
    """Test invalid credentials show error and remain on login page."""
    response = client.post('/login', data={
        'username': 'nonexistent_user',
        'password': 'WrongPassword123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid credentials" in response.data
