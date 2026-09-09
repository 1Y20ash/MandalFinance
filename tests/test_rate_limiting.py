import pytest
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config import ProductionConfig


def test_registration_rate_limit_returns_safe_429(client):
    for index in range(5):
        response = client.post('/auth/register', data={
            'full_name': f'Test User {index}',
            'username': f'newuser{index}',
            'email': f'newuser{index}@example.com',
            'phone': '',
            'password': 'short',
            'confirm_password': 'short',
        })
        assert response.status_code in (200, 302)

    response = client.post('/auth/register', data={
        'full_name': 'Blocked User',
        'username': 'blocked-user',
        'email': 'blocked@example.com',
        'password': 'short',
        'confirm_password': 'short',
    })
    assert response.status_code == 429
    assert b'Too many requests' in response.data
    assert b'Please wait a moment and try again' in response.data
    assert b'Internal Server Error' not in response.data
    assert response.headers.get('Retry-After')


def test_public_donation_initiation_is_rate_limited(client):
    for _ in range(10):
        response = client.post('/donate', data={
            'donor_name': 'Rate Limit Test',
            'donor_phone': '',
            'donor_email': '',
            'amount': '10',
            'purpose': 'Testing',
        })
        assert response.status_code != 429

    response = client.post('/donate', data={
        'donor_name': 'Rate Limit Test',
        'amount': '10',
        'purpose': 'Testing',
    })
    assert response.status_code == 429


def test_health_probes_are_exempt_from_rate_limiting(client):
    for _ in range(5):
        response = client.get('/health/live')
        assert response.status_code == 200


def _set_valid_production_environment(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://example')
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'server-only-test-key')
    monkeypatch.setenv('PAYMENT_GATEWAY_DRIVER', 'razorpay')
    monkeypatch.setenv('RAZORPAY_KEY_ID', 'test-key')
    monkeypatch.setenv('RAZORPAY_KEY_SECRET', 'test-secret')
    monkeypatch.setenv('RAZORPAY_WEBHOOK_SECRET', 'test-webhook-secret')
    monkeypatch.setenv('SUPABASE_STORAGE_PRIVATE', 'true')
    monkeypatch.setenv('REDIS_PROVIDER_NAME', 'test-redis-provider')
    monkeypatch.setattr(ProductionConfig, 'PAYMENT_GATEWAY_DRIVER', 'razorpay')
    monkeypatch.setattr(ProductionConfig, 'REDIS_PROVIDER_NAME', 'test-redis-provider')


def test_production_requires_shared_persistent_rate_limit_storage(monkeypatch):
    _set_valid_production_environment(monkeypatch)
    monkeypatch.delenv('RATELIMIT_STORAGE_URI', raising=False)
    monkeypatch.delenv('REDIS_URL', raising=False)
    monkeypatch.setattr(ProductionConfig, 'RATELIMIT_STORAGE_URI', None)

    with pytest.raises(RuntimeError, match='RATELIMIT_STORAGE_URI or REDIS_URL'):
        ProductionConfig.validate()


def test_production_rejects_memory_rate_limit_storage(monkeypatch):
    _set_valid_production_environment(monkeypatch)
    monkeypatch.setenv('RATELIMIT_STORAGE_URI', 'memory://')
    monkeypatch.setattr(ProductionConfig, 'RATELIMIT_STORAGE_URI', 'memory://')

    with pytest.raises(RuntimeError, match='RATELIMIT_STORAGE_URI or REDIS_URL'):
        ProductionConfig.validate()


def test_production_accepts_non_memory_shared_storage(monkeypatch):
    _set_valid_production_environment(monkeypatch)
    monkeypatch.setenv('RATELIMIT_STORAGE_URI', 'redis://localhost:6379/0')
    monkeypatch.setattr(ProductionConfig, 'RATELIMIT_STORAGE_URI', 'redis://localhost:6379/0')

    ProductionConfig.validate()


def test_flask_limiter_uses_configured_redis_backend():
    app = Flask(__name__)
    app.config['RATELIMIT_STORAGE_URI'] = 'redis://localhost:6379/0'
    configured_limiter = Limiter(
        key_func=get_remote_address,
        default_limits=['10 per minute'],
    )
    configured_limiter.init_app(app)

    assert type(configured_limiter.storage).__name__ == 'RedisStorage'
