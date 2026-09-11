import hashlib
import hmac
import json
from decimal import Decimal

import pytest
import requests

from app.extensions import db
from app.models.income import Donation
from app.services.payment_gateway import MockPaymentGateway, PaymentGatewayError, RazorpayGateway


def test_mock_gateway_requires_exact_payment_signature():
    gateway = MockPaymentGateway()
    order = gateway.create_order(Decimal('501.00'), 1, 'Test Donor')
    assert gateway.verify_payment_signature(
        order['order_id'], order['mock_payment_id'], order['mock_signature']
    )
    assert not gateway.verify_payment_signature(order['order_id'], order['mock_payment_id'], 'valid_anything')


def test_razorpay_payment_signature_verification(app):
    with app.app_context():
        app.config.update(RAZORPAY_KEY_SECRET='test-secret')
        order_id = 'order_test_123'
        payment_id = 'pay_test_456'
        signature = hmac.new(
            b'test-secret',
            f'{order_id}|{payment_id}'.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        gateway = RazorpayGateway()
        assert gateway.verify_payment_signature(order_id, payment_id, signature)
        assert not gateway.verify_payment_signature(order_id, payment_id, 'bad-signature')


def test_razorpay_webhook_signature_uses_raw_payload(app):
    with app.app_context():
        app.config.update(RAZORPAY_WEBHOOK_SECRET='webhook-secret')
        payload = json.dumps({'event': 'payment.captured'}, separators=(',', ':')).encode('utf-8')
        signature = hmac.new(b'webhook-secret', payload, hashlib.sha256).hexdigest()
        gateway = RazorpayGateway()
        assert gateway.verify_webhook_signature(payload, signature)
        assert not gateway.verify_webhook_signature(payload + b' ', signature)


def test_razorpay_order_rejects_invalid_credentials_without_leaking_secrets(app, monkeypatch):
    class FakeResponse:
        status_code = 401

        def json(self):
            return {
                'error': {
                    'code': 'BAD_REQUEST_ERROR',
                    'description': 'Authentication failed',
                }
            }

    with app.app_context():
        app.config.update(RAZORPAY_KEY_ID='rzp_live_example', RAZORPAY_KEY_SECRET='secret-value')
        monkeypatch.setattr('app.services.payment_gateway.requests.post', lambda *args, **kwargs: FakeResponse())
        with pytest.raises(PaymentGatewayError, match='credentials were rejected') as exc_info:
            RazorpayGateway().create_order(Decimal('501.00'), 1, 'Test Donor')
        assert 'secret-value' not in str(exc_info.value)


def test_razorpay_order_handles_network_failure(app, monkeypatch):
    with app.app_context():
        app.config.update(RAZORPAY_KEY_ID='rzp_test_example', RAZORPAY_KEY_SECRET='secret-value')

        def fail_request(*args, **kwargs):
            raise requests.Timeout('simulated timeout')

        monkeypatch.setattr('app.services.payment_gateway.requests.post', fail_request)
        with pytest.raises(PaymentGatewayError, match='could not be reached'):
            RazorpayGateway().create_order(Decimal('501.00'), 1, 'Test Donor')


def test_razorpay_order_validates_gateway_response(app, monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                'id': 'order_test_123',
                'amount': 99900,
                'currency': 'INR',
                'status': 'created',
            }

    with app.app_context():
        app.config.update(RAZORPAY_KEY_ID='rzp_test_example', RAZORPAY_KEY_SECRET='secret-value')
        monkeypatch.setattr('app.services.payment_gateway.requests.post', lambda *args, **kwargs: FakeResponse())
        with pytest.raises(PaymentGatewayError, match='unexpected order response'):
            RazorpayGateway().create_order(Decimal('501.00'), 1, 'Test Donor')


def test_online_donation_is_not_ledger_posted_before_confirmation(app):
    with app.app_context():
        from app.models.mandal import Event

        event = Event.query.first()
        donation = Donation(
            donation_number='DON-TEST-PHASE8',
            event_id=event.id,
            donor_name='Pending Donor',
            amount=Decimal('501.00'),
            purpose='General Utsav Donation',
            donation_type='ONLINE',
            payment_mode='ONLINE_GATEWAY',
            status='PENDING',
            gateway_order_id='order_pending_test',
        )
        db.session.add(donation)
        db.session.commit()

        assert donation.status == 'PENDING'
