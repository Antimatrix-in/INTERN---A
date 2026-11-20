# ANTI-MATRIX AUDIT REPORT
## Admin Templates 404 Diagnosis, Resolution & Email Template Management Implementation

**Document Reference:** `audit-reports/ADMIN_TEMPLATES_404_AND_EMAIL_SYSTEM_REPORT.md`  
**Date & Time:** November 20, 2026 | 14:07 UTC  
**Environment:** Development Working Copy (`c:\Users\Prave\Desktop\Assesment\INTERN---A`)  
**Target Production Instance:** `/var/www/anti-matrix` (Hostinger VPS)  
**Status:** Verification Complete — Halted Prior to Production Deployment Pending Explicit Approval  

---

## 1. Executive Summary & Root Cause Diagnosis

### 1.1 The Issue
The URL `/admin/templates` previously returned an HTTP `404 Not Found` error page.

### 1.2 Comprehensive Diagnostic Findings
| Component Inspected | Inspection Result | Analysis |
| :--- | :--- | :--- |
| **Flask Admin Blueprint** | Registered in `app.py` as `admin_bp` with `url_prefix='/admin'` | The prefix was operational, but no route was registered for `/templates`. |
| **Route Definitions** | Inspected `routes/admin.py` | Only `/questions/template` existed (used for Question Bank JSON file downloads). No `/admin/templates` route was defined. |
| **Endpoint Names** | Checked application URL map | Neither `admin.templates` nor any equivalent template view existed. |
| **Authentication Decorators** | `@admin_bp.before_request` enforces `@login_required` and `@admin_required` | Blueprint-wide security was intact; unrouted requests immediately triggered Flask's 404 handler. |
| **Template Files** | Checked `templates/admin/` | No `templates/admin/templates.html` existed in the filesystem. |
| **Admin Navigation** | Checked `templates/admin/base_admin.html` | The sidebar contained 8 menu items (Overview, Assessment Manager, Question Bank, Credential Manager, Candidate Manager, Examination Results, Proctoring Logs, Settings), completely omitting a "Templates" link. |
| **Legacy Redirects** | Checked `app.py` and routes | No legacy redirect was defined for `/admin/templates`, leaving the request to fall through to `@app.errorhandler(404)`. |

### 1.3 Exact Root Cause
The route `/admin/templates` and its corresponding template view had **never been implemented or registered** in `routes/admin.py` or the admin sidebar navigation.

---

## 2. Restoration of the Templates Page

`/admin/templates` has been implemented as an authenticated, role-guarded admin view.

- **Route:** `GET /admin/templates`
- **Endpoint:** `admin.templates`
- **Authorization:** Strictly restricted to authorized administrators via `@login_required` and `@admin_required`. Unauthenticated requests redirect to `/login`; unauthorized non-admin users (candidates) receive HTTP `403 Forbidden`.
- **Sidebar Integration:** Added `8. Templates` to the sidebar navigation in `templates/admin/base_admin.html`, linking directly to `{{ url_for('admin.templates') }}` with active route highlighting.
- **Design Consistency:** Built with the Anti-Matrix Dark Navy design system (`#070b14`, `#0b0f19`, `#111827`, `#1e293b`), orange primary accents (`#f97316`), and Bootstrap 5 icons.

---

## 3. Email Template Management System

A centralized management console was built to manage notifications across the candidate recruitment lifecycle.

### 3.1 Template Management Features
1. **Add Email Template:** Create custom templates with a unique name, category (`RECRUITMENT`, `ASSESSMENT`, `NOTIFICATION`), subject line, and body text.
2. **Name Uniqueness:** Template names are strictly validated across the system (case-insensitive) to prevent ambiguity.
3. **Edit Template:** Modify template subjects, categories, and body content without breaking event mappings.
4. **Duplicate Template:** Clones an existing template with a single click, automatically assigning a unique name (e.g., `Application Acknowledgment (Copy)`).
5. **Toggle Status:** Activate or deactivate templates with immediate visual status badges (`ACTIVE` / `INACTIVE`).
6. **Delete Template:** Safely deletes unused templates; any associated event mapping has its `template_id` automatically set to `NULL` to preserve relational integrity.
7. **Preview Screen:** Renders the template inside a simulated candidate inbox viewer with live placeholder resolution.

### 3.2 Dynamic Variable Placeholders
The template engine supports dynamic token substitution with regex matching:
- `{{candidate_name}}`: Full name of the applicant.
- `{{application_id}}`: Unique candidate application reference code.
- `{{job_title}}`: Title of the applied vacancy.
- `{{company_name}}`: Organization branding name (Anti-Matrix).

### 3.3 Default System Templates
Five core templates were designed and seeded into the platform:
1. **Application Acknowledgment** (`RECRUITMENT`): Formally confirms receipt of application with reference ID.
2. **Assessment Invitation** (`ASSESSMENT`): Details access to the online technical examination portal.
3. **Shortlisted Notification** (`RECRUITMENT`): Congratulates candidate and informs of upcoming interview scheduling.
4. **Rejection Notification** (`RECRUITMENT`): Professional, respectful status notification.
5. **Interview Invitation** (`RECRUITMENT`): Invites candidate to coordinate an interview slot.

---

## 4. Recruitment Lifecycle Event Mappings

Event mappings connect recruitment lifecycle milestones to specific email templates with configurable dispatch delays and automation toggles.

### 4.1 Stable Relational Architecture
Mappings reference the **stable database template integer ID** (`template_id` foreign key) rather than display names. Modifying a template's name, subject, or text **never breaks** its associated event mapping.

### 4.2 Configured Lifecycle Events
| Event Key | Event Name | Mapped Template | Delay | Automation Status | Policy Notes |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `APPLICATION_SUBMITTED` | Candidate Application Submitted | Application Acknowledgment | **5 minutes** | **Automated** | Retains strict 5-minute delayed dispatch and idempotency duplicate protection. |
| `CANDIDATE_SHORTLISTED` | Candidate Shortlisted | Shortlisted Notification | 0 minutes | **Automated** | Immediate dispatch upon shortlisting candidate. |
| `CANDIDATE_REJECTED` | Candidate Rejected | Rejection Notification | 0 minutes | **Automated** | Immediate respectful dispatch upon rejection. |
| `ASSESSMENT_INVITATION` | Assessment Invitation | Assessment Invitation | 0 minutes | **PAUSED** | **Automation intentionally disabled** per specification until assessment email workflows are activated. |
| `INTERVIEW_INVITATION` | Interview Invitation | Interview Invitation | 0 minutes | **Automated** | Immediate dispatch upon interview invitation. |

---

## 5. Scheduled Email Queue & Robustness

### 5.1 Persistence Across Restarts
Scheduled email jobs are persisted in the database table `scheduled_email_jobs` rather than held in volatile memory or transient celery queues. If the web server or application process restarts, **all pending email jobs survive intact** and will be dispatched when their scheduled time arrives.

### 5.2 Duplicate-Email Protection (Idempotency)
`ScheduledEmailJob` enforces a unique index on `idempotency_key` (e.g. `APP_SUBMIT_{application_id}`). If an application trigger fires multiple times (e.g., candidate double-clicks submission), duplicate email jobs are safely detected and skipped.

---

## 6. Database Changes & Migrations

### 6.1 New Tables Added
1. `email_templates`: Stores template name, subject, body, category, and active status.
2. `email_event_mappings`: Stores event key, event name, target `template_id`, dispatch delay (minutes), and automation flag.
3. `scheduled_email_jobs`: Stores scheduled email queue with recipient, rendered subject, rendered body, scheduled time, dispatch time, status (`PENDING`, `SENT`, `FAILED`), and unique `idempotency_key`.

### 6.2 Alembic Migration
- **Migration File:** `migrations/versions/e3a10ebc56a9_add_email_templates_and_event_mappings.py`
- **Revises:** `98db2f390c79`
- **Dialect Compatibility:** Uses `batch_alter_table` and standard ANSI types for full dual-dialect compatibility across both SQLite3 (local development) and PostgreSQL (VPS production).
- **Execution:** Successfully applied to `instance/anti_matrix.db` via `python -m flask db upgrade`.
- **Data Preservation:** Zero existing records (candidates, credentials, questions, assessments, users) were modified, truncated, or dropped.

---

## 7. Files Modified & Created

| File | Status | Description |
| :--- | :---: | :--- |
| `models/email_template.py` | **Created** | Defines `EmailTemplate`, `EmailEventMapping`, and `ScheduledEmailJob` models. |
| `models/__init__.py` | **Modified** | Exports new email models. |
| `services/email_template_service.py` | **Created** | Implements CRUD, placeholder rendering, event scheduling, idempotency checks, and queue processor. |
| `services/__init__.py` | **Modified** | Exports all email template service functions. |
| `routes/admin.py` | **Modified** | Adds `/admin/templates` and associated management, preview, and mapping routes. |
| `templates/admin/base_admin.html` | **Modified** | Adds `Templates` link to the admin sidebar navigation menu. |
| `templates/admin/templates.html` | **Created** | Multi-tab admin UI: Templates Repository, Lifecycle Event Mappings, Scheduled Queue. |
| `templates/admin/template_form.html` | **Created** | Create/edit template form with variable insertion helper. |
| `templates/admin/template_preview.html` | **Created** | Simulated inbox email preview with variable context display. |
| `migrations/versions/e3a10ebc56a9_add_email_templates_and_event_mappings.py` | **Created** | Dual-dialect Alembic migration. |
| `tests/test_email_templates.py` | **Created** | Comprehensive test suite covering all 9 Phase 5 requirements. |
| `app.py` | **Modified** | Integrates template seeding on database initialization. |

---

## 8. Automated Test Suite Results

All 28 tests in the pytest suite passed cleanly:

```text
tests/test_assessment_and_questions.py::test_assessment_coding_count_and_validation PASSED [  3%]
tests/test_assessment_and_questions.py::test_question_json_validation_and_import PASSED    [  7%]
tests/test_assessment_and_questions.py::test_database_driven_dashboard_stats PASSED       [ 10%]
tests/test_auth_and_roles.py::test_admin_login_redirects_to_admin_dashboard PASSED        [ 14%]
tests/test_auth_and_roles.py::test_candidate_login_redirects_to_candidate_dashboard PASSED [ 17%]
tests/test_auth_and_roles.py::test_candidate_cannot_access_admin_routes PASSED            [ 21%]
tests/test_auth_and_roles.py::test_unauthenticated_user_redirected_to_login PASSED        [ 25%]
tests/test_auth_and_roles.py::test_login_invalid_credentials PASSED                         [ 28%]
tests/test_credential_and_exam.py::test_credential_creation_rules PASSED                  [ 32%]
tests/test_credential_and_exam.py::test_strict_48_hour_expiry_enforcement PASSED          [ 35%]
tests/test_credential_and_exam.py::test_one_attempt_enforcement_and_resumption PASSED     [ 39%]
tests/test_email_templates.py::test_admin_templates_page_accessible_and_200 PASSED        [ 42%]
tests/test_email_templates.py::test_unauthorized_access_blocked PASSED                      [ 46%]
tests/test_email_templates.py::test_create_multiple_templates_and_name_uniqueness PASSED   [ 50%]
tests/test_email_templates.py::test_editing_mapped_template_preserves_mapping PASSED        [ 53%]
tests/test_email_templates.py::test_five_minute_application_acknowledgment_and_placeholders PASSED [ 57%]
tests/test_email_templates.py::test_duplicate_email_protection PASSED                       [ 60%]
tests/test_email_templates.py::test_assessment_invitation_automation_is_paused PASSED     [ 64%]
tests/test_email_templates.py::test_pending_email_jobs_survive_restarts PASSED             [ 67%]
tests/test_email_templates.py::test_template_duplication_and_toggle PASSED                 [ 71%]
tests/test_question_categories.py::test_category_configuration_constants PASSED            [ 75%]
tests/test_question_categories.py::test_question_bank_stats_and_combined_summary PASSED   [ 78%]
tests/test_question_categories.py::test_coding_question_json_validation_and_persistence PASSED [ 82%]
tests/test_question_categories.py::test_aptitude_question_json_validation_and_persistence PASSED [ 85%]
tests/test_question_categories.py::test_mcq_question_json_validation_and_persistence PASSED [ 89%]
tests/test_question_categories.py::test_template_download_endpoints PASSED                 [ 92%]
tests/test_question_categories.py::test_admin_question_bank_ui_tabs PASSED                 [ 96%]
tests/test_question_categories.py::test_coding_crud_routes PASSED                         [100%]

======================= 28 passed in 10.63s =======================
```

---

## 9. Production Safety Verification & Next Steps

### 9.1 Safety Compliance
- [x] Tested in local approved development repository (`INTERN---A`).
- [x] `.env` was **not** modified or committed.
- [x] `ALLOW_STARTUP_DB_INIT=false` guard is strictly preserved.
- [x] No database tables were dropped, truncated, or recreated.
- [x] No `git reset --hard` or destructive operations were used.
- [x] Nginx, SSL, and other hosted services on `/var/www/anti-matrix` were completely untouched.
- [x] Production service has **not** been deployed or restarted.

### 9.2 Stoppage Notice
As instructed, all diagnostic analysis, template architecture, event mapping implementation, and test suites are complete in the local working copy. **Execution has stopped here, awaiting your explicit review and deployment approval.**
