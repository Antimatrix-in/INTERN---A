import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'anti-matrix-assessment-dev-secret-key-384918237')
    
    # Database
    db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:root@localhost:5432/anti_matrix_db')
    if db_url and db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Engine options for PostgreSQL connection pooling
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
    """Testing configuration with separate database."""
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    # Use test database or sqlite in-memory for unit testing if postgres test db not set
    test_db = os.environ.get('TEST_DATABASE_URL', 'postgresql://postgres:root@localhost:5432/anti_matrix_db')
    SQLALCHEMY_DATABASE_URI = test_db

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
