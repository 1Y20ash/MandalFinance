from pathlib import Path

import pytest

from app import create_app
from app.config import ProductionConfig


ROOT = Path(__file__).resolve().parents[1]


def test_deployment_architecture_policy_exists_and_has_required_boundaries():
    policy = ROOT / 'docs' / 'DEPLOYMENT_ARCHITECTURE.md'
    text = policy.read_text(encoding='utf-8')

    required = [
        'server.py', 'Vercel', 'PostgreSQL', 'Supabase private storage',
        'Shared Redis', 'Razorpay', 'Flask-Migrate/Alembic', 'HTTPS',
        'production configuration validation', 'SQLite', 'db.create_all()',
    ]
    for item in required:
        assert item in text


def test_vercel_configuration_uses_current_canonical_production_entrypoint():
    vercel_text = (ROOT / 'vercel.json').read_text(encoding='utf-8')
    pyproject_text = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')

    # The canonical Vercel entrypoint is explicitly declared in pyproject.toml.
    # server.py remains the repository's production application entrypoint and
    # is intentionally retained as the documented hosting boundary.
    assert 'entrypoint = "app.server:app"' in pyproject_text
    assert '"functions"' in vercel_text
    assert '"includeFiles"' in vercel_text
    # Vercel must bundle the complete Jinja template tree, not only public/*.html,
    # because public templates inherit from the shared base template.
    assert 'app/templates/**/*.html' in vercel_text


def _set_valid_production_environment(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://example')
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'server-only-test-key')
    monkeypatch.setenv('SUPABASE_STORAGE_PRIVATE', 'true')
    monkeypatch.setenv('PAYMENT_GATEWAY_DRIVER', 'razorpay')
    monkeypatch.setenv('RAZORPAY_KEY_ID', 'test-key')
    monkeypatch.setenv('RAZORPAY_KEY_SECRET', 'test-secret')
    monkeypatch.setenv('RAZORPAY_WEBHOOK_SECRET', 'test-webhook-secret')
    monkeypatch.setenv('RATELIMIT_STORAGE_URI', 'redis://localhost:6379/0')
    monkeypatch.setenv('REDIS_PROVIDER_NAME', 'test-redis')
    monkeypatch.setattr(ProductionConfig, 'PAYMENT_GATEWAY_DRIVER', 'razorpay')
    monkeypatch.setattr(ProductionConfig, 'RATELIMIT_STORAGE_URI', 'redis://localhost:6379/0')
    monkeypatch.setattr(ProductionConfig, 'REDIS_PROVIDER_NAME', 'test-redis')
    monkeypatch.setattr(ProductionConfig, 'SUPABASE_STORAGE_PRIVATE', True)


def test_production_app_is_created_through_application_factory(monkeypatch):
    _set_valid_production_environment(monkeypatch)
    app = create_app('production')
    assert app.config['APP_ENV'] == 'production'
    assert app.config['DEBUG'] is False
    assert app.config['SESSION_COOKIE_SECURE'] is True


def test_server_entrypoint_does_not_create_tables_directly():
    text = (ROOT / 'server.py').read_text(encoding='utf-8')
    assert 'db.create_all' not in text
    assert 'upgrade()' in text


def test_production_rejects_sqlite_database_configuration(monkeypatch):
    _set_valid_production_environment(monkeypatch)
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///production.db')
    with pytest.raises(RuntimeError, match='PostgreSQL'):
        ProductionConfig.validate()


def test_production_architecture_preserves_sqlite_only_for_testing():
    config_text = (ROOT / 'app' / 'config.py').read_text(encoding='utf-8').lower()
    assert 'sqlite:///:memory:' in config_text
    assert 'productionconfig' in config_text


def test_production_architecture_keeps_secrets_out_of_base_template():
    template = ROOT / 'app' / 'templates' / 'base.html'
    if template.exists():
        text = template.read_text(encoding='utf-8').lower()
        forbidden = ['supabase_service_role_key', 'razorpay_key_secret', 'razorpay_webhook_secret']
        for marker in forbidden:
            assert marker not in text
