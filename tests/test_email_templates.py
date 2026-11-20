import pytest
from datetime import datetime, timezone, timedelta
from models import db, EmailTemplate, EmailEventMapping, ScheduledEmailJob, User
from services import (
    seed_default_templates_and_mappings,
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
    process_pending_email_jobs
)

@pytest.fixture(autouse=True)
def init_templates(app):
    """Ensure default templates and mappings exist for test runs."""
    with app.app_context():
        seed_default_templates_and_mappings()

def test_admin_templates_page_accessible_and_200(client, admin_user_id):
    """Phase 5.1 & 5.3: Verify /admin/templates returns HTTP 200 for authorized admins and navbar link works."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user_id)
        sess['_fresh'] = True

    resp = client.get('/admin/templates')
    assert resp.status_code == 200
    assert b"Email Template Management" in resp.data
    assert b"Application Acknowledgment" in resp.data
    assert b"Assessment Invitation" in resp.data
    assert b"Shortlisted Notification" in resp.data
    assert b"Rejection Notification" in resp.data
    assert b"Interview Invitation" in resp.data

    # Check navbar Templates link is present
    assert b'href="/admin/templates"' in resp.data or b"Templates" in resp.data

def test_unauthorized_access_blocked(client, app):
    """Phase 5.2: Verify unauthorized access to /admin/templates is strictly blocked."""
    # 1. Anonymous user redirected to login
    resp_anon = client.get('/admin/templates', follow_redirects=False)
    assert resp_anon.status_code == 302
    assert '/login' in resp_anon.headers['Location']

    # 2. Candidate role receives 403 Forbidden
    with app.app_context():
        cand = User.query.filter_by(username='cand_temp_auth').first()
        if not cand:
            cand = User(
                user_id='AM-CAND-AUTH-99',
                username='cand_temp_auth',
                email='cand_auth99@example.com',
                full_name='Auth Candidate',
                role='CANDIDATE',
                is_active=True
            )
            cand.set_password('CandPass123!')
            db.session.add(cand)
            db.session.commit()

    login_resp = client.post('/login', data={
        'username': 'cand_temp_auth',
        'password': 'CandPass123!'
    })
    assert login_resp.status_code == 302

    resp_cand = client.get('/admin/templates')
    assert resp_cand.status_code == 403

def test_create_multiple_templates_and_name_uniqueness(app):
    """Phase 5.4 & 5.5: Multiple templates can be created and names must be unique."""
    with app.app_context():
        # Create Template 1
        t1, err1 = create_email_template(
            name="Offer Letter Notification",
            subject="Job Offer — {{company_name}}",
            body="Dear {{candidate_name}}, we are pleased to offer you the role of {{job_title}}.",
            category="RECRUITMENT"
        )
        assert err1 is None
        assert t1 is not None
        assert t1.id is not None

        # Create Template 2
        t2, err2 = create_email_template(
            name="Onboarding Guide",
            subject="Welcome to {{company_name}} Onboarding",
            body="Dear {{candidate_name}}, here are your onboarding instructions.",
            category="NOTIFICATION"
        )
        assert err2 is None
        assert t2 is not None

        # Duplicate name attempt (case-insensitive)
        t_dup, err_dup = create_email_template(
            name="offer letter notification",
            subject="Duplicate Subject",
            body="Duplicate Body"
        )
        assert t_dup is None
        assert "already exists" in err_dup

def test_editing_mapped_template_preserves_mapping(app):
    """Phase 5.6: Editing a mapped template does not break its event mapping."""
    with app.app_context():
        # Find mapping for APPLICATION_SUBMITTED
        mapping = EmailEventMapping.query.filter_by(event_key='APPLICATION_SUBMITTED').first()
        assert mapping is not None
        orig_template_id = mapping.template_id
        assert orig_template_id is not None

        # Edit template
        updated_t, err = update_email_template(
            template_id=orig_template_id,
            name="Application Acknowledgment Revised",
            subject="Updated: Your Application to {{company_name}}",
            body="Dear {{candidate_name}}, application {{application_id}} has been received."
        )
        assert err is None
        assert updated_t.name == "Application Acknowledgment Revised"

        # Verify mapping still points to the same template ID and resolves correctly
        refreshed_mapping = EmailEventMapping.query.filter_by(event_key='APPLICATION_SUBMITTED').first()
        assert refreshed_mapping.template_id == orig_template_id
        assert refreshed_mapping.template.name == "Application Acknowledgment Revised"
        assert refreshed_mapping.template.subject == "Updated: Your Application to {{company_name}}"

def test_five_minute_application_acknowledgment_and_placeholders(app):
    """Phase 5.7: Verify the five-minute delayed acknowledgment and dynamic placeholders."""
    with app.app_context():
        context = {
            'candidate_name': 'Eleanor Shellstrop',
            'application_id': 'AM-APP-2026-7788',
            'job_title': 'Lead Architect',
            'company_name': 'Anti-Matrix'
        }
        before_time = datetime.now(timezone.utc)
        
        job, err = schedule_email_event(
            event_key='APPLICATION_SUBMITTED',
            recipient_email='eleanor@example.com',
            recipient_name='Eleanor Shellstrop',
            context_data=context,
            idempotency_key='APP_SUBMIT_AM-APP-2026-7788'
        )
        assert err is None
        assert job is not None
        assert job.status == 'PENDING'

        # Check 5 minute delay (normalize timezone for SQLite naive datetime)
        sched_time = job.scheduled_at
        if sched_time.tzinfo is None:
            sched_time = sched_time.replace(tzinfo=timezone.utc)

        expected_scheduled_at = before_time + timedelta(minutes=5)
        # Difference within 5 seconds
        time_diff = abs((sched_time - expected_scheduled_at).total_seconds())
        assert time_diff < 5

        # Check placeholder substitution in subject and body
        assert "Lead Architect" in job.subject
        assert "Anti-Matrix" in job.subject
        assert "Dear Eleanor Shellstrop" in job.body
        assert "AM-APP-2026-7788" in job.body
        assert "Lead Architect" in job.body
        assert "Anti-Matrix" in job.body

def test_duplicate_email_protection(app):
    """Verify duplicate-email protection via idempotency keys."""
    with app.app_context():
        idemp = "APP_SUBMIT_DUP_TEST_01"
        job1, err1 = schedule_email_event(
            event_key='APPLICATION_SUBMITTED',
            recipient_email='dup@example.com',
            recipient_name='Dup Test',
            idempotency_key=idemp
        )
        assert err1 is None
        assert job1.status == 'PENDING'

        # Second schedule call with exact same idempotency key
        job2, err2 = schedule_email_event(
            event_key='APPLICATION_SUBMITTED',
            recipient_email='dup@example.com',
            recipient_name='Dup Test',
            idempotency_key=idemp
        )
        assert "Duplicate email prevented" in err2
        assert job2.id == job1.id

def test_assessment_invitation_automation_is_paused(app):
    """Verify assessment email automation is NOT active by default."""
    with app.app_context():
        mapping = EmailEventMapping.query.filter_by(event_key='ASSESSMENT_INVITATION').first()
        assert mapping is not None
        assert mapping.is_automated is False  # Must be paused

        job, err = schedule_email_event(
            event_key='ASSESSMENT_INVITATION',
            recipient_email='candidate@example.com',
            recipient_name='Assessment Candidate'
        )
        assert job is None
        assert "Automation is disabled" in err

def test_pending_email_jobs_survive_restarts(app):
    """Phase 5.8: Verify pending email jobs persist in the database and survive restarts."""
    with app.app_context():
        job, err = schedule_email_event(
            event_key='APPLICATION_SUBMITTED',
            recipient_email='restart_test@example.com',
            recipient_name='Restart Tester',
            idempotency_key='RESTART_KEY_01'
        )
        job_id = job.id
        db.session.commit()

    # Re-open session simulating server reboot
    with app.app_context():
        loaded_job = db.session.get(ScheduledEmailJob, job_id)
        assert loaded_job is not None
        assert loaded_job.recipient_email == 'restart_test@example.com'
        assert loaded_job.status == 'PENDING'

def test_template_duplication_and_toggle(app, client, admin_user_id):
    """Verify template duplication and active/inactive toggling."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user_id)
        sess['_fresh'] = True

    with app.app_context():
        template = EmailTemplate.query.filter_by(name="Shortlisted Notification").first()
        t_id = template.id

    # Duplicate via POST
    resp_dup = client.post(f'/admin/templates/{t_id}/duplicate', follow_redirects=True)
    assert resp_dup.status_code == 200

    with app.app_context():
        dup = EmailTemplate.query.filter_by(name="Shortlisted Notification (Copy)").first()
        assert dup is not None
        assert dup.subject == template.subject
        dup_id = dup.id

    # Toggle status via POST
    resp_toggle = client.post(f'/admin/templates/{dup_id}/toggle', follow_redirects=True)
    assert resp_toggle.status_code == 200

    with app.app_context():
        dup_refreshed = db.session.get(EmailTemplate, dup_id)
        assert dup_refreshed.is_active is False
