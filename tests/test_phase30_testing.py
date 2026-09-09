from pathlib import Path

import hashlib
import hmac

from app.services.payment_gateway import RazorpayGateway, MockPaymentGateway


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / 'tests'


def test_phase30_testing_strategy_exists():
    policy = ROOT / 'docs' / 'TESTING_STRATEGY.md'
    assert policy.exists()
    text = policy.read_text(encoding='utf-8')
    required_sections = [
        '## Test layers',
        '## Mandatory regression areas',
        '## Test isolation',
        '## CI gate',
        '## Coverage philosophy',
    ]
    for section in required_sections:
        assert section in text


def test_critical_regression_inventory_is_present():
    required_test_modules = {
        'authentication': ['test_auth.py'],
        'donations': ['test_donations.py'],
        'financial_controls': ['test_financial_controls.py'],
        'ledger': ['test_ledger.py', 'test_ledger_reconciliation.py'],
        'documents': ['test_documents.py', 'test_document_security.py'],
        'audit_logging': ['test_audit_logging.py'],
        'operational_logging': ['test_logging.py'],
        'dependency_controls': ['test_phase29_dependency_audit.py'],
        'testing_controls': ['test_phase30_testing.py'],
    }
    for area, candidates in required_test_modules.items():
        assert any((TESTS / name).exists() for name in candidates), area


def test_razorpay_payment_signature_accepts_only_exact_hmac(app):
    with app.app_context():
        app.config['RAZORPAY_KEY_SECRET'] = 'phase30-test-secret'
        gateway = RazorpayGateway()
        order_id = 'order_phase30'
        payment_id = 'pay_phase30'
        message = f'{order_id}|{payment_id}'.encode('utf-8')
        signature = hmac.new(
            b'phase30-test-secret', message, hashlib.sha256
        ).hexdigest()

        assert gateway.verify_payment_signature(order_id, payment_id, signature)
        assert not gateway.verify_payment_signature(order_id, payment_id, signature[:-1] + '0')
        assert not gateway.verify_payment_signature(order_id, 'pay-other', signature)
        assert not gateway.verify_payment_signature(order_id, payment_id, '')


def test_razorpay_webhook_signature_accepts_only_exact_hmac(app):
    with app.app_context():
        app.config['RAZORPAY_WEBHOOK_SECRET'] = 'phase30-webhook-secret'
        gateway = RazorpayGateway()
        payload = b'{"event":"payment.captured"}'
        signature = hmac.new(
            b'phase30-webhook-secret', payload, hashlib.sha256
        ).hexdigest()

        assert gateway.verify_webhook_signature(payload, signature)
        assert not gateway.verify_webhook_signature(payload + b' ', signature)
        assert not gateway.verify_webhook_signature(payload, 'invalid')
        assert not gateway.verify_webhook_signature(payload, '')


def test_mock_gateway_signature_is_bound_to_order_and_payment():
    gateway = MockPaymentGateway()
    order = gateway.create_order('100.00', 42, 'Test Donor')
    assert gateway.verify_payment_signature(
        order['order_id'], order['mock_payment_id'], order['mock_signature']
    )
    assert not gateway.verify_payment_signature(
        order['order_id'], 'pay_other', order['mock_signature']
    )


def test_public_donation_provider_failure_does_not_leak_exception(client, app, monkeypatch):
    class ExplodingGateway:
        def create_order(self, *args, **kwargs):
            raise RuntimeError('SECRET_PROVIDER_FAILURE_123')

    monkeypatch.setattr('app.routes.public.get_payment_gateway', lambda: ExplodingGateway())
    response = client.post(
        '/donate',
        data={
            'donor_name': 'Test Donor',
            'donor_email': 'donor@example.com',
            'amount': '100.00',
            'purpose': 'General Utsav Donation',
        },
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Donation setup could not be completed' in body
    assert 'SECRET_PROVIDER_FAILURE_123' not in body
