import hmac
import hashlib
import uuid
from abc import ABC, abstractmethod
from flask import current_app

class PaymentGatewayInterface(ABC):
    @abstractmethod
    def create_order(self, amount_decimal, donation_id, donor_name):
        pass

    @abstractmethod
    def verify_payment_signature(self, order_id, payment_id, signature):
        pass

    @abstractmethod
    def verify_webhook_signature(self, payload_bytes, signature_header):
        pass


class MockPaymentGateway(PaymentGatewayInterface):
    def create_order(self, amount_decimal, donation_id, donor_name):
        order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
        return {
            'order_id': order_id,
            'amount_in_paise': int(amount_decimal * 100),
            'currency': 'INR',
            'status': 'created',
            'key_id': 'mock_key_id'
        }

    def verify_payment_signature(self, order_id, payment_id, signature):
        # Mock verification: succeeds if signature starts with 'valid_' or equals mock expected
        return signature and (signature.startswith('valid_') or signature == f"mock_sig_{order_id}_{payment_id}")

    def verify_webhook_signature(self, payload_bytes, signature_header):
        return signature_header == "valid_mock_webhook_sig"


class RazorpayGateway(PaymentGatewayInterface):
    def create_order(self, amount_decimal, donation_id, donor_name):
        key_id = current_app.config.get('RAZORPAY_KEY_ID')
        key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')
        
        # If credentials missing in environment, fallback to mock simulation safely
        if not key_id or not key_secret:
            current_app.logger.warning("Razorpay credentials missing. Using mock order creation.")
            return MockPaymentGateway().create_order(amount_decimal, donation_id, donor_name)

        amount_in_paise = int(amount_decimal * 100)
        import requests
        resp = requests.post(
            'https://api.razorpay.com/v1/orders',
            auth=(key_id, key_secret),
            json={
                'amount': amount_in_paise,
                'currency': 'INR',
                'receipt': f"don_{donation_id}",
                'notes': {'donor_name': donor_name}
            },
            timeout=10
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            return {
                'order_id': data['id'],
                'amount_in_paise': data['amount'],
                'currency': data['currency'],
                'status': data['status'],
                'key_id': key_id
            }
        raise RuntimeError(f"Razorpay Order creation failed: {resp.text}")

    def verify_payment_signature(self, order_id, payment_id, signature):
        key_secret = current_app.config.get('RAZORPAY_KEY_SECRET', '')
        if not key_secret:
            return MockPaymentGateway().verify_payment_signature(order_id, payment_id, signature)

        msg = f"{order_id}|{payment_id}".encode('utf-8')
        generated_sig = hmac.new(key_secret.encode('utf-8'), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(generated_sig, signature)

    def verify_webhook_signature(self, payload_bytes, signature_header):
        webhook_secret = current_app.config.get('RAZORPAY_WEBHOOK_SECRET', '')
        if not webhook_secret:
            return False

        generated_sig = hmac.new(webhook_secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(generated_sig, signature_header)


def get_payment_gateway():
    driver = current_app.config.get('PAYMENT_GATEWAY_DRIVER', 'mock').lower()
    if driver == 'razorpay':
        return RazorpayGateway()
    return MockPaymentGateway()
