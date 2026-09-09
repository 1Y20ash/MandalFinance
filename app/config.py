import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or f"sqlite:///{BASE_DIR/'ashtavinayak_mandal.db'}"
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', str(BASE_DIR/'uploads'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16*1024*1024))
    MAX_DOCUMENT_SIZE = int(os.environ.get('MAX_DOCUMENT_SIZE', 10*1024*1024))
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'mandal-financial-documents')
    SUPABASE_STORAGE_PRIVATE = os.environ.get('SUPABASE_STORAGE_PRIVATE', 'true').lower() == 'true'
    PAYMENT_GATEWAY_DRIVER = os.environ.get('PAYMENT_GATEWAY_DRIVER', 'mock').strip().lower()
    ONLINE_DONATION_ACCOUNT_ID = os.environ.get('ONLINE_DONATION_ACCOUNT_ID', '')
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
    RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI') or os.environ.get('REDIS_URL')
    REDIS_PROVIDER_NAME = os.environ.get('REDIS_PROVIDER_NAME', '').strip()
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
    RATELIMIT_STORAGE_URI = 'memory://'


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    @classmethod
    def validate(cls):
        required = ['SECRET_KEY', 'DATABASE_URL', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
        database_url = (os.environ.get('DATABASE_URL') or '').strip().lower()
        if not database_url.startswith(('postgresql://', 'postgres://')):
            raise RuntimeError('DATABASE_URL must use PostgreSQL in production.')
        if cls.PAYMENT_GATEWAY_DRIVER == 'razorpay':
            required += ['RAZORPAY_KEY_ID', 'RAZORPAY_KEY_SECRET', 'RAZORPAY_WEBHOOK_SECRET']
        elif cls.PAYMENT_GATEWAY_DRIVER == 'mock':
            raise RuntimeError('Mock payment gateway is forbidden in production.')
        else:
            raise RuntimeError('Unsupported payment gateway driver in production.')
        if not cls.SUPABASE_STORAGE_PRIVATE:
            raise RuntimeError('SUPABASE_STORAGE_PRIVATE must be true in production.')
        if not cls.RATELIMIT_STORAGE_URI or cls.RATELIMIT_STORAGE_URI.strip().lower().startswith('memory://'):
            required.append('RATELIMIT_STORAGE_URI or REDIS_URL (persistent shared storage)')
        if not cls.REDIS_PROVIDER_NAME:
            required.append('REDIS_PROVIDER_NAME (production processor identity)')
        missing = [name for name in required if not os.environ.get(name)]
        if cls.RATELIMIT_STORAGE_URI and cls.RATELIMIT_STORAGE_URI.strip().lower().startswith('memory://'):
            missing.append('RATELIMIT_STORAGE_URI or REDIS_URL (persistent shared storage)')
        if missing:
            raise RuntimeError('Missing required production environment variables: ' + ', '.join(sorted(set(missing))))


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
