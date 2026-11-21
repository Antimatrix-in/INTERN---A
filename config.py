import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)

# Default local SQLite database file in instance/ directory
DEFAULT_SQLITE_PATH = os.path.join(INSTANCE_DIR, 'anti_matrix.db')
DEFAULT_SQLITE_URI = f"sqlite:///{DEFAULT_SQLITE_PATH.replace(os.sep, '/')}"

class Config:
    """Base configuration with environment-driven database switching."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'anti-matrix-assessment-dev-secret-key-384918237')
    
    # Environment-based database configuration:
    # - Assessment database (Primary): set ASSESSMENT_DATABASE_URL or DATABASE_URL
    # - Local development: defaults to SQLite3 inside instance/anti_matrix.db
    # - VPS production: PostgreSQL anti_matrix_assessment_db
    raw_db_url = os.environ.get('ASSESSMENT_DATABASE_URL') or os.environ.get('DATABASE_URL')
    if not raw_db_url:
        db_url = DEFAULT_SQLITE_URI
    elif raw_db_url.startswith('postgres://'):
        # Fix legacy Heroku/host provider postgres:// schema prefix
        db_url = raw_db_url.replace('postgres://', 'postgresql://', 1)
    else:
        db_url = raw_db_url
        
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Source Anti-Matrix production database for Candidate Identity Lookup (Strict Read-Only)
    raw_readonly_url = os.environ.get('ANTIMATRIX_READONLY_DATABASE_URL')
    if raw_readonly_url and raw_readonly_url.startswith('postgres://'):
        raw_readonly_url = raw_readonly_url.replace('postgres://', 'postgresql://', 1)
    ANTIMATRIX_READONLY_DATABASE_URL = raw_readonly_url
    
    # Engine options dynamic based on dialect (PostgreSQL vs SQLite)
    if db_url.startswith('sqlite'):
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
        }
    else:
        # PostgreSQL connection pooling options
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_size': 10,
            'max_overflow': 20,
        }
    
    # Security & Sessions
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # Upload limits (5MB maximum)
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 5 * 1024 * 1024))
    
    # Anti-Matrix Business Rules
    CREDENTIAL_EXPIRY_HOURS = int(os.environ.get('CREDENTIAL_EXPIRY_HOURS', 48))

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Testing configuration with dedicated test database."""
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    
    default_test_sqlite = f"sqlite:///{os.path.join(INSTANCE_DIR, 'test_anti_matrix.db').replace(os.sep, '/')}"
    test_db = os.environ.get('TEST_DATABASE_URL', default_test_sqlite)
    SQLALCHEMY_DATABASE_URI = test_db
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # In production, ensure DATABASE_URL is utilized
    if not os.environ.get('DATABASE_URL'):
        SQLALCHEMY_DATABASE_URI = DEFAULT_SQLITE_URI

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
