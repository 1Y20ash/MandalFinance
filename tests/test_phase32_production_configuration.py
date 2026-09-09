import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_production_config.py"


VALID_PRODUCTION_ENV = {
    "FLASK_ENV": "production",
    "SECRET_KEY": "ci-production-secret-value",
    "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/mandalfinance_ci",
    "SUPABASE_URL": "https://ci-example.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "ci-production-service-role-key",
    "SUPABASE_STORAGE_PRIVATE": "true",
    "PAYMENT_GATEWAY_DRIVER": "razorpay",
    "RAZORPAY_KEY_ID": "rzp_test_ci_key",
    "RAZORPAY_KEY_SECRET": "ci-razorpay-secret",
    "RAZORPAY_WEBHOOK_SECRET": "ci-razorpay-webhook-secret",
    "RATELIMIT_STORAGE_URI": "redis://localhost:6379/0",
    "REDIS_PROVIDER_NAME": "ci-redis-service",
}


def run_preflight(overrides=None):
    env = os.environ.copy()
    for key in (
        "SECRET_KEY",
        "DATABASE_URL",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_STORAGE_PRIVATE",
        "PAYMENT_GATEWAY_DRIVER",
        "RAZORPAY_KEY_ID",
        "RAZORPAY_KEY_SECRET",
        "RAZORPAY_WEBHOOK_SECRET",
        "RATELIMIT_STORAGE_URI",
        "REDIS_URL",
        "REDIS_PROVIDER_NAME",
    ):
        env.pop(key, None)
    env.update(VALID_PRODUCTION_ENV)
    env.update(overrides or {})
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_valid_production_configuration_passes():
    result = run_preflight()
    assert result.returncode == 0, result.stderr + result.stdout
    assert "Production configuration preflight: PASS" in result.stdout


def test_production_rejects_sqlite_database():
    result = run_preflight({"DATABASE_URL": "sqlite:///local.db"})
    assert result.returncode != 0
    assert "DATABASE_URL must use PostgreSQL in production" in result.stderr


def test_production_rejects_mock_gateway():
    result = run_preflight({"PAYMENT_GATEWAY_DRIVER": "mock"})
    assert result.returncode != 0
    assert "Mock payment gateway is forbidden in production" in result.stderr


def test_production_rejects_public_supabase_storage():
    result = run_preflight({"SUPABASE_STORAGE_PRIVATE": "false"})
    assert result.returncode != 0
    assert "SUPABASE_STORAGE_PRIVATE must be true in production" in result.stderr


def test_production_requires_persistent_rate_limit_storage():
    result = run_preflight({"RATELIMIT_STORAGE_URI": "memory://"})
    assert result.returncode != 0
    assert "persistent shared storage" in result.stderr


def test_production_requires_redis_provider_identity():
    result = run_preflight({"REDIS_PROVIDER_NAME": ""})
    assert result.returncode != 0
    assert "REDIS_PROVIDER_NAME" in result.stderr


def test_production_requires_razorpay_webhook_secret():
    result = run_preflight({"RAZORPAY_WEBHOOK_SECRET": ""})
    assert result.returncode != 0
    assert "RAZORPAY_WEBHOOK_SECRET" in result.stderr


def test_production_cookie_security_is_explicit():
    env = os.environ.copy()
    env.update(VALID_PRODUCTION_ENV)
    code = (
        "from app.config import ProductionConfig; "
        "assert ProductionConfig.DEBUG is False; "
        "assert ProductionConfig.SESSION_COOKIE_SECURE is True; "
        "assert ProductionConfig.SESSION_COOKIE_HTTPONLY is True; "
        "assert ProductionConfig.SESSION_COOKIE_SAMESITE == 'Lax'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_production_preflight_does_not_need_external_service_connections():
    result = run_preflight()
    assert "connection refused" not in result.stderr.lower()
    assert "timeout" not in result.stderr.lower()
