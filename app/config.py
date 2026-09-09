import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or f"sqlite:///{BASE_DIR/'ashtavinayak_mandal.db'}"
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', str(BASE_DIR / 'uploads'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    MAX_DOCUMENT_SIZE = int(os.environ.get('MAX_DOCUMENT_SIZE', 10 * 1024 * 1024))
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'mandal-financial-documents')
    SUPABASE_STORAGE_PRIVATE = os.environ.get('SUPABASE_STORAGE_PRIVATE', 'true').lower() == 'true'
    PAYMENT_GATEWAY_DRIVER = os.environ.get('PAYMENT_GATEWAY_DRIVER', 'mock').strip().lower()
    ONLINE_DONATION_ACCOUNT_ID = os.environ.get('ONLINE_DONATION_ACCOUNT_ID', '')
    ONLINE_DONATION_ACTOR_ID = os.environ.get('ONLINE_DONATION_ACTOR_ID', '')
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
    RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY', 'development-only-change-me')


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = 'testing-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


def validate_production_environment(environ=None):
    """Fail closed when production is missing a security-critical setting."""
    env = os.environ if environ is None else environ
    required = [
        'SECRET_KEY',
        'DATABASE_URL',
        'SUPABASE_URL',
        'SUPABASE_SERVICE_ROLE_KEY',
        'SUPABASE_STORAGE_BUCKET',
        'ONLINE_DONATION_ACCOUNT_ID',
        'ONLINE_DONATION_ACTOR_ID',
    ]
    missing = [name for name in required if not env.get(name)]
    if missing:
        raise RuntimeError(
            'Missing required production environment variables: '
            + ', '.join(sorted(set(missing)))
        )

    secret_key = env.get('SECRET_KEY', '')
    if len(secret_key) < 32 or secret_key.lower() in {
        'change-me', 'change-me-in-production', 'dev-secret-key',
        'development-only-change-me', 'testing-secret-key',
    }:
        raise RuntimeError('SECRET_KEY must be a strong production secret of at least 32 characters.')

    database_url = env.get('DATABASE_URL', '').strip()
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    if not database_url.startswith('postgresql://'):
        raise RuntimeError('DATABASE_URL must use PostgreSQL in production.')

    supabase_url = env.get('SUPABASE_URL', '').strip()
    parsed_supabase = urlparse(supabase_url)
    if parsed_supabase.scheme != 'https' or not parsed_supabase.netloc:
        raise RuntimeError('SUPABASE_URL must be a valid HTTPS URL in production.')
    if env.get('SUPABASE_SERVICE_ROLE_KEY', '').lower().startswith('your-'):
        raise RuntimeError('SUPABASE_SERVICE_ROLE_KEY still contains a placeholder value.')

    if env.get('SUPABASE_STORAGE_PRIVATE', 'true').strip().lower() != 'true':
        raise RuntimeError('SUPABASE_STORAGE_PRIVATE must be true in production.')

    driver = env.get('PAYMENT_GATEWAY_DRIVER', '').strip().lower()
    if driver != 'razorpay':
        raise RuntimeError('PAYMENT_GATEWAY_DRIVER must be razorpay in production.')
    payment_required = ['RAZORPAY_KEY_ID', 'RAZORPAY_KEY_SECRET', 'RAZORPAY_WEBHOOK_SECRET']
    payment_missing = [name for name in payment_required if not env.get(name)]
    if payment_missing:
        raise RuntimeError(
            'Missing required Razorpay production environment variables: '
            + ', '.join(payment_missing)
        )

    max_content_length = int(env.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    max_document_size = int(env.get('MAX_DOCUMENT_SIZE', 10 * 1024 * 1024))
    if max_content_length <= 0 or max_document_size <= 0:
        raise RuntimeError('Upload size limits must be positive.')
    if max_document_size > max_content_length:
        raise RuntimeError('MAX_DOCUMENT_SIZE cannot exceed MAX_CONTENT_LENGTH.')

    return True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    @classmethod
    def validate(cls):
        validate_production_environment()


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
