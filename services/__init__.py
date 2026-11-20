from .auth_service import admin_required, candidate_required, create_initial_admin
from .credential_service import (
    create_candidate_credential,
    regenerate_candidate_credential,
    toggle_credential_status,
    get_all_credentials,
    generate_candidate_user_id,
    generate_secure_password,
    find_candidate_by_id,
    send_credential_email
)
from .assessment_service import (
    create_assessment,
    update_assessment,
    toggle_assessment_status
)
from .question_service import (
    CATEGORY_CONFIG,
    get_coding_template,
    get_aptitude_template,
    get_mcq_template,
    get_sample_json_template,
    parse_and_validate_question_json,
    save_imported_questions,
    get_question_bank_stats,
    get_coding_questions_query,
    get_mcq_questions_query
)
from .stats_service import get_admin_dashboard_stats
from .exam_service import (
    start_or_resume_examination,
    autosave_attempt_answer,
    submit_examination
)
from .email_template_service import (
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
    get_email_queue_jobs,
    process_pending_email_jobs,
    get_email_dashboard_stats
)
