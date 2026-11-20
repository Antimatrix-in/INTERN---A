"""
ANTI-MATRIX — Online Assessment Platform
Phase 1: Flask Application Foundation, Authentication & Admin Dashboard
"""

from app import create_app, app
from models import db, User, Assessment, Question, Credential, Attempt, AttemptAnswer, Result, ProctoringEvent

__all__ = [
    'create_app',
    'app',
    'db',
    'User',
    'Assessment',
    'Question',
    'Credential',
    'Attempt',
    'AttemptAnswer',
    'Result',
    'ProctoringEvent'
]
