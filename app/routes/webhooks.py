from flask import Blueprint, current_app, jsonify

from app.extensions import csrf
from app.routes.public import payment_webhook as secure_payment_webhook


webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/webhooks')


@webhooks_bp.post('/razorpay')
@csrf.exempt
def razorpay_webhook():
    """Compatibility endpoint using the same hardened payment webhook flow."""
    if current_app.config.get('PAYMENT_GATEWAY_DRIVER', 'mock').strip().lower() != 'razorpay':
        return jsonify({'status': 'disabled'}), 404
    return secure_payment_webhook()
