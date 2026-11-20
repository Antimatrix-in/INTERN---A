from datetime import datetime, timezone
from models import db, User, Credential, Assessment, Attempt, Result

def get_admin_dashboard_stats():
    """
    Computes real-time, database-driven statistics for the admin dashboard.
    No hardcoded values.
    """
    now = datetime.now(timezone.utc)

    # 1. Total Candidates: users with role 'CANDIDATE'
    total_candidates = User.query.filter_by(role='CANDIDATE').count()

    # 2. Active Credentials: status == 'ACTIVE', not expired, not yet used for an attempt
    active_credentials = Credential.query.filter(
        Credential.status == 'ACTIVE',
        Credential.expires_at > now,
        ~Credential.attempt.has()
    ).count()

    # 3. Pending Assessments: credentials created that are ACTIVE or attempts currently IN_PROGRESS
    pending_assessments = Attempt.query.filter_by(status='IN_PROGRESS').count() + active_credentials

    # 4. Completed Assessments: attempts with status 'COMPLETED'
    completed_assessments = Attempt.query.filter_by(status='COMPLETED').count()

    # 5. Passed Candidates: results with passed=True
    passed_candidates = Result.query.filter_by(passed=True).count()

    # 6. Failed Candidates: results with passed=False
    failed_candidates = Result.query.filter_by(passed=False).count()

    # Additional analytical metrics
    total_assessments = Assessment.query.count()
    active_assessments = Assessment.query.filter_by(is_active=True).count()
    expired_credentials = Credential.query.filter(
        (Credential.status == 'EXPIRED') | ((Credential.status == 'ACTIVE') & (Credential.expires_at <= now))
    ).count()

    # Recent activity feeds
    recent_credentials = Credential.query.order_by(Credential.created_at.desc()).limit(5).all()
    recent_attempts = Attempt.query.order_by(Attempt.started_at.desc()).limit(5).all()
    recent_candidates = User.query.filter_by(role='CANDIDATE').order_by(User.created_at.desc()).limit(5).all()
    recent_results = Result.query.order_by(Result.created_at.desc()).limit(5).all()

    return {
        'total_candidates': total_candidates,
        'active_credentials': active_credentials,
        'pending_assessments': pending_assessments,
        'completed_assessments': completed_assessments,
        'passed_candidates': passed_candidates,
        'failed_candidates': failed_candidates,
        'total_assessments': total_assessments,
        'active_assessments': active_assessments,
        'expired_credentials': expired_credentials,
        'recent_credentials': recent_credentials,
        'recent_attempts': recent_attempts,
        'recent_candidates': recent_candidates,
        'recent_results': recent_results
    }
