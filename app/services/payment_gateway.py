import hashlib
import hmac
import logging
import uuid
from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP

import requests
from flask import current_app


logger = logging.getLogger(__name__)


class PaymentGatewayError(RuntimeError):
    """Safe, user-facing payment gateway failure with no secret leakage."""

    def __init__(self, message, *, code='gateway_error', http_status=None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


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
    """Deterministic local/test gateway. It is never silently used for Razorpay."""

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
            raise PaymentGatewayError(
                'The payment gateway is not configured correctly. Please contact the Mandal administrator.',
                code='configuration_missing',
            )
        return key_id, key_secret

    def _key_secret(self):
        key_secret = current_app.config.get('RAZORPAY_KEY_SECRET', '').strip()
        if not key_secret:
            raise PaymentGatewayError(
                'The payment gateway is not configured correctly. Please contact the Mandal administrator.',
                code='configuration_missing',
            )
        return key_secret

    @staticmethod
    def _error_details(response):
        """Extract only non-secret Razorpay error metadata for server logs."""
        try:
            payload = response.json() or {}
        except ValueError:
            payload = {}
        error = payload.get('error') or {}
        return str(error.get('code') or 'unknown'), str(error.get('description') or '')[:300]

    def create_order(self, amount_decimal, donation_id, donor_name):
        key_id, key_secret = self._credentials()
        amount = Decimal(str(amount_decimal)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if amount <= 0:
            raise PaymentGatewayError('Payment amount must be greater than zero.', code='invalid_amount')

        try:
            response = requests.post(
                'https://api.razorpay.com/v1/orders',
                auth=(key_id, key_secret),
                json={
                    'amount': int(amount * 100),
                    'currency': 'INR',
                    'receipt': f'don_{donation_id}',
                    'notes': {'donor_name': donor_name[:120]},
                },
                timeout=10,
            )
        except requests.RequestException:
            logger.exception('Razorpay order request failed before a response was received')
            raise PaymentGatewayError(
                'The payment gateway could not be reached. Please try again in a moment.',
                code='gateway_unreachable',
            ) from None

        if response.status_code not in (200, 201):
            error_code, error_description = RazorpayGateway._error_details(response)
            logger.error(
                'Razorpay order creation rejected: status=%s code=%s description=%s',
                response.status_code,
                error_code,
                error_description or '<none>',
            )
            if response.status_code in (401, 403):
                message = 'The payment gateway credentials were rejected. Please contact the Mandal administrator.'
                code = 'credentials_rejected'
            elif response.status_code == 429:
                message = 'The payment gateway is temporarily busy. Please try again shortly.'
                code = 'gateway_rate_limited'
            elif 500 <= response.status_code <= 599:
                message = 'The payment gateway is temporarily unavailable. Please try again shortly.'
                code = 'gateway_unavailable'
            else:
                message = 'The payment gateway rejected this donation request. Please verify the amount and try again.'
                code = error_code or 'gateway_rejected'
            raise PaymentGatewayError(message, code=code, http_status=response.status_code)

        try:
            data = response.json()
            order_id = data['id']
            response_amount = int(data['amount'])
            response_currency = data['currency']
            response_status = data['status']
        except (ValueError, KeyError, TypeError):
            logger.exception('Razorpay returned an invalid order response')
            raise PaymentGatewayError(
                'The payment gateway returned an invalid response. Please try again.',
                code='invalid_gateway_response',
            ) from None

        expected_paise = int(amount * 100)
        if response_amount != expected_paise or response_currency != 'INR' or response_status != 'created':
            logger.error(
                'Razorpay order response failed validation: order=%s amount=%s currency=%s status=%s expected_amount=%s',
                order_id,
                response_amount,
                response_currency,
                response_status,
                expected_paise,
            )
            raise PaymentGatewayError(
                'The payment gateway returned an unexpected order response. Please try again.',
                code='invalid_gateway_response',
            )

        return {
            'order_id': order_id,
            'amount_in_paise': response_amount,
            'currency': response_currency,
            'status': response_status,
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
    raise PaymentGatewayError(
        'The payment gateway is not configured correctly. Please contact the Mandal administrator.',
        code='unsupported_driver',
    )
