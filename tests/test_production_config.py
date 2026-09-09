import pytest

from app.config import validate_production_environment


VALID_ENV = {
    'SECRET_KEY': 'a' * 64,
    'DATABASE_URL': 'postgresql://user:password@db.example.com:5432/mandalfinance',
    'SUPABASE_URL': 'https://example.supabase.co',
    'SUPABASE_SERVICE_ROLE_KEY': 'service-role-secret',
    'SUPABASE_STORAGE_BUCKET': 'mandal-financial-documents',
    'SUPABASE_STORAGE_PRIVATE': 'true',
    'ONLINE_DONATION_ACCOUNT_ID': '1',
    'ONLINE_DONATION_ACTOR_ID': '1',
    'PAYMENT_GATEWAY_DRIVER': 'razorpay',
    'RAZORPAY_KEY_ID': 'rzp_test_example',
    'RAZORPAY_KEY_SECRET': 'razorpay-secret',
    'RAZORPAY_WEBHOOK_SECRET': 'webhook-secret',
    'MAX_CONTENT_LENGTH': str(16 * 1024 * 1024),
    'MAX_DOCUMENT_SIZE': str(10 * 1024 * 1024),
}


def test_valid_production_environment_passes():
    assert validate_production_environment(VALID_ENV) is True


@pytest.mark.parametrize('name', [
    'SECRET_KEY',
    'DATABASE_URL',
    'SUPABASE_URL',
    'SUPABASE_SERVICE_ROLE_KEY',
    'SUPABASE_STORAGE_BUCKET',
    'ONLINE_DONATION_ACCOUNT_ID',
    'ONLINE_DONATION_ACTOR_ID',
])
def test_required_production_setting_is_fail_closed(name):
    env = VALID_ENV.copy()
    env.pop(name)
    with pytest.raises(RuntimeError, match='Missing required production environment variables'):
        validate_production_environment(env)


def test_weak_secret_is_rejected():
    env = VALID_ENV.copy()
    env['SECRET_KEY'] = 'change-me-in-production'
    with pytest.raises(RuntimeError, match='strong production secret'):
        validate_production_environment(env)


def test_sqlite_is_rejected_in_production():
    env = VALID_ENV.copy()
    env['DATABASE_URL'] = 'sqlite:///mandalfinance.db'
    with pytest.raises(RuntimeError, match='PostgreSQL'):
        validate_production_environment(env)


def test_supabase_must_use_https():
    env = VALID_ENV.copy()
    env['SUPABASE_URL'] = 'http://example.supabase.co'
    with pytest.raises(RuntimeError, match='HTTPS'):
        validate_production_environment(env)


def test_public_storage_is_rejected():
    env = VALID_ENV.copy()
    env['SUPABASE_STORAGE_PRIVATE'] = 'false'
    with pytest.raises(RuntimeError, match='SUPABASE_STORAGE_PRIVATE'):
        validate_production_environment(env)


def test_mock_gateway_is_rejected():
    env = VALID_ENV.copy()
    env['PAYMENT_GATEWAY_DRIVER'] = 'mock'
    with pytest.raises(RuntimeError, match='razorpay'):
        validate_production_environment(env)


def test_missing_razorpay_secret_is_rejected():
    env = VALID_ENV.copy()
    env.pop('RAZORPAY_WEBHOOK_SECRET')
    with pytest.raises(RuntimeError, match='RAZORPAY_WEBHOOK_SECRET'):
        validate_production_environment(env)


def test_document_limit_cannot_exceed_request_limit():
    env = VALID_ENV.copy()
    env['MAX_DOCUMENT_SIZE'] = str(20 * 1024 * 1024)
    with pytest.raises(RuntimeError, match='MAX_DOCUMENT_SIZE'):
        validate_production_environment(env)
