import hashlib
import hmac
import json
from decimal import Decimal

import pytest

from app.extensions import db
from app.models.income import Donation
from app.models.ledger import Account, Transaction
from app.models.payment_event import PaymentWebhookEvent
from app.services.donation_service import DonationService
from app.services.payment_gateway import MockPaymentGateway, RazorpayGateway


def test_mock_gateway_requires_exact_payment_signature():
    gateway = MockPaymentGateway()
    order = gateway.create_order(Decimal('501.00'), 1, 'Test Donor')
    assert gateway.verify_payment_signature(
        order['order_id'], order['mock_payment_id'], order['mock_signature']
    )
    assert not gateway.verify_payment_signature(order['order_id'], order['mock_payment_id'], 'valid_anything')


def test_mock_gateway_server_verification_rejects_wrong_order_or_amount():
    gateway = MockPaymentGateway()
    order = gateway.create_order(Decimal('501.00'), 1, 'Test Donor')
    verified = gateway.verify_payment(
        order['order_id'], order['mock_payment_id'], Decimal('501.00')
    )
    assert verified['order_id'] == order['order_id']
    assert verified['amount'] == 50100
    assert verified['status'] == 'captured'

    with pytest.raises(ValueError, match='does not belong'):
        gateway.verify_payment('order_other', order['mock_payment_id'], Decimal('501.00'))


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


def test_razorpay_payment_server_verification_checks_identity_amount_and_capture(app, monkeypatch):
    with app.app_context():
        app.config.update(RAZORPAY_KEY_ID='key', RAZORPAY_KEY_SECRET='secret')
        gateway = RazorpayGateway()

        class Response:
            status_code = 200

            @staticmethod
            def json():
                return {
                    'id': 'pay_123',
                    'order_id': 'order_123',
                    'amount': 50100,
                    'currency': 'INR',
                    'status': 'captured',
                    'captured': True,
                }

        monkeypatch.setattr('app.services.payment_gateway.requests.get', lambda *args, **kwargs: Response())
        result = gateway.verify_payment('order_123', 'pay_123', Decimal('501.00'))
        assert result['status'] == 'captured'

        with pytest.raises(ValueError, match='amount mismatch'):
            gateway.verify_payment('order_123', 'pay_123', Decimal('502.00'))


def test_razorpay_webhook_signature_uses_raw_payload(app):
    with app.app_context():
        app.config.update(RAZORPAY_WEBHOOK_SECRET='webhook-secret')
        payload = json.dumps({'event': 'payment.captured'}, separators=(',', ':')).encode('utf-8')
        signature = hmac.new(b'webhook-secret', payload, hashlib.sha256).hexdigest()
        gateway = RazorpayGateway()
        assert gateway.verify_webhook_signature(payload, signature)
        assert not gateway.verify_webhook_signature(payload + b' ', signature)


def test_online_donation_is_not_ledger_posted_before_confirmation(app):
    with app.app_context():
        from app.models.mandal import Event

        event = Event.query.first()
        donation = Donation(
            donation_number='DON-TEST-PHASE12-PENDING',
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
        assert Transaction.query.filter_by(source_module='DONATION', source_id=donation.id).count() == 0


def test_online_confirmation_requires_verified_server_payment(app):
    with app.app_context():
        from app.models.mandal import Event

        event = Event.query.first()
        account = Account.query.filter_by(name='Main Cash').first()
        donation = Donation(
            donation_number='DON-TEST-PHASE12-CONFIRM',
            event_id=event.id,
            donor_name='Confirmed Donor',
            amount=Decimal('501.00'),
            purpose='General Utsav Donation',
            donation_type='ONLINE',
            payment_mode='ONLINE_GATEWAY',
            status='PENDING',
            gateway_order_id='order_mock_confirmation',
        )
        db.session.add(donation)
        db.session.commit()

        gateway = MockPaymentGateway()
        payment_id = 'pay_mock_order_mock_confirmation'
        signature = 'mock_sig_order_mock_confirmation_pay_mock_order_mock_confirmation'
        verified = gateway.verify_payment(
            donation.gateway_order_id, payment_id, donation.amount
        )
        saved = DonationService.confirm_online_donation(
            donation.id,
            payment_id,
            signature,
            account.id,
            verified_order_id=verified['order_id'],
            verified_amount_paise=verified['amount'],
            verified_currency=verified['currency'],
            verified_status=verified['status'],
        )
        assert saved.status == 'SUCCESS'
        assert saved.gateway_payment_id == payment_id
        assert Transaction.query.filter_by(external_ref=payment_id).count() == 1


def test_webhook_is_idempotent_and_does_not_double_post(app):
    with app.app_context():
        from app.models.mandal import Event

        event = Event.query.first()
        account = Account.query.filter_by(name='Main Cash').first()
        app.config['ONLINE_DONATION_ACCOUNT_ID'] = account.id
        donation = Donation(
            donation_number='DON-TEST-PHASE12-WEBHOOK',
            event_id=event.id,
            donor_name='Webhook Donor',
            amount=Decimal('501.00'),
            purpose='General Utsav Donation',
            donation_type='ONLINE',
            payment_mode='ONLINE_GATEWAY',
            status='PENDING',
            gateway_order_id='order_mock_webhook',
        )
        db.session.add(donation)
        db.session.commit()

        payment_id = 'pay_mock_order_mock_webhook'
        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': payment_id,
                        'order_id': donation.gateway_order_id,
                        'amount': 50100,
                        'currency': 'INR',
                        'status': 'captured',
                        'captured': True,
                    }
                }
            },
        }
        raw = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        headers = {
            'X-Razorpay-Signature': 'valid_mock_webhook_sig',
            'x-razorpay-event-id': 'evt_phase12_001',
            'Content-Type': 'application/json',
        }

        client = app.test_client()
        first = client.post('/donate/webhook', data=raw, headers=headers)
        second = client.post('/donate/webhook', data=raw, headers=headers)

        assert first.status_code == 200
        assert second.status_code == 200
        db.session.expire_all()
        saved = db.session.get(Donation, donation.id)
        assert saved.status == 'SUCCESS'
        assert Transaction.query.filter_by(external_ref=payment_id).count() == 1
        assert PaymentWebhookEvent.query.filter_by(event_id='evt_phase12_001').count() == 1
