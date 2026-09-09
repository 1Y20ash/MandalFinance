import hashlib
import hmac
import uuid
from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP

import requests
from flask import current_app


class PaymentGatewayInterface(ABC):
    @abstractmethod
    def create_order(self, amount_decimal, donation_id, donor_name):
        raise NotImplementedError

    @abstractmethod
    def verify_payment_signature(self, order_id, payment_id, signature):
        raise NotImplementedError

    @abstractmethod
    def verify_webhook_signature(self, payload_bytes, signature_header):
        raise NotImplementedError


class MockPaymentGateway(PaymentGatewayInterface):
    def create_order(self, amount_decimal, donation_id, donor_name):
        order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
        payment_id = f"pay_mock_{order_id}"
        return {
            'order_id': order_id,
            'amount_in_paise': int(Decimal(str(amount_decimal)).quantize(Decimal('0.01')) * 100),
            'currency': 'INR',
            'status': 'created',
            'key_id': 'mock_key_id',
            'mock_payment_id': payment_id,
            'mock_signature': f"mock_sig_{order_id}_{payment_id}",
        }

    def verify_payment_signature(self, order_id, payment_id, signature):
        expected = f"mock_sig_{order_id}_{payment_id}"
        return bool(signature) and hmac.compare_digest(expected, signature)

    def verify_webhook_signature(self, payload_bytes, signature_header):
        return bool(signature_header) and hmac.compare_digest('valid_mock_webhook_sig', signature_header)


class RazorpayGateway(PaymentGatewayInterface):
    def _credentials(self):
        key_id = current_app.config.get('RAZORPAY_KEY_ID', '').strip()
        key_secret = current_app.config.get('RAZORPAY_KEY_SECRET', '').strip()
        if not key_id or not key_secret:
            raise RuntimeError('Razorpay credentials are not configured.')
        return key_id, key_secret

    def _key_secret(self):
        key_secret = current_app.config.get('RAZORPAY_KEY_SECRET', '').strip()
        if not key_secret:
            raise RuntimeError('Razorpay key secret is not configured.')
        return key_secret

    def create_order(self, amount_decimal, donation_id, donor_name):
        key_id, key_secret = self._credentials()
        amount = Decimal(str(amount_decimal)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if amount <= 0:
            raise ValueError('Payment amount must be greater than zero.')

        response = requests.post(
            'https://api.razorpay.com/v1/orders',
            auth=(key_id, key_secret),
            json={
                'amount': int(amount * 100),
                'currency': 'INR',
                'receipt': f'don_{donation_id}',
            },
            timeout=10,
        )
        if response.status_code not in (200, 201):
            raise RuntimeError(f'Razorpay order creation failed ({response.status_code}).')

        data = response.json()
        return {
            'order_id': data['id'],
            'amount_in_paise': data['amount'],
            'currency': data['currency'],
            'status': data['status'],
            'key_id': key_id,
        }

    def verify_payment_signature(self, order_id, payment_id, signature):
        key_secret = self._key_secret()
        if not order_id or not payment_id or not signature:
            return False
        message = f'{order_id}|{payment_id}'.encode('utf-8')
        expected = hmac.new(key_secret.encode('utf-8'), message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_webhook_signature(self, payload_bytes, signature_header):
        webhook_secret = current_app.config.get('RAZORPAY_WEBHOOK_SECRET', '').strip()
        if not webhook_secret or not signature_header:
            return False
        expected = hmac.new(webhook_secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header)


def get_payment_gateway():
    driver = current_app.config.get('PAYMENT_GATEWAY_DRIVER', 'mock').strip().lower()
    if driver == 'razorpay':
        return RazorpayGateway()
    if driver == 'mock':
        return MockPaymentGateway()
    raise RuntimeError(f'Unsupported payment gateway driver: {driver}')
