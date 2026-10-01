from app import create_app
from app.config import ProductionConfig
from app.extensions import db


def test_security_headers_are_present():
    app = create_app('testing')
    response = app.test_client().get('/health')

    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    assert response.headers['Permissions-Policy'] == 'camera=(), microphone=(), geolocation=()'
    assert response.headers['Cross-Origin-Opener-Policy'] == 'same-origin'
    assert response.headers['Cross-Origin-Resource-Policy'] == 'same-origin'

    csp = response.headers['Content-Security-Policy']
    for directive in (
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://checkout.razorpay.com",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",
        "img-src 'self' data: blob: https://*.razorpay.com",
        "connect-src 'self' https://*.razorpay.com",
        "frame-src 'self' https://*.razorpay.com",
        "manifest-src 'self'",
        "worker-src 'self'",
        'upgrade-insecure-requests',
    ):
        assert directive in csp


def test_production_hsts_is_enabled(monkeypatch):
    monkeypatch.setattr(ProductionConfig, 'validate', classmethod(lambda cls: None))
    app = create_app('production')
    try:
        response = app.test_client().get('/health')
        assert response.headers['Strict-Transport-Security'] == 'max-age=31536000; includeSubDomains'
    finally:
        # The production health endpoint exercises the real PostgreSQL engine.
        # Close the scoped session before disposing the test app's engine so
        # Psycopg 3 connections are returned to the pool and closed.
        with app.app_context():
            db.session.remove()
            for engine in db.engines.values():
                engine.dispose()
