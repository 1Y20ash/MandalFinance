import json

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import or_

from app.extensions import csrf, db, limiter
from app.models.income import Donation
from app.services.audit_service import AuditService
from app.services.payment_gateway import get_payment_gateway


webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/webhooks')


@webhooks_bp.post('/razorpay')
@csrf.exempt
@limiter.exempt
def razorpay_webhook():
    """Receive and authenticate Razorpay webhook deliveries.

    Razorpay signs the exact raw request body with the webhook secret.  The
    webhook is intentionally not used to post the accounting ledger entry:
    the existing online-payment confirmation flow performs that operation
    atomically with its evidence checks, preventing duplicate financial posts
    when Razorpay retries an event.
    """
    if current_app.config.get('PAYMENT_GATEWAY_DRIVER', 'mock').strip().lower() != 'razorpay':
        return jsonify({'status': 'disabled'}), 404

    raw_body = request.get_data(cache=True)
    signature = request.headers.get('X-Razorpay-Signature', '')
    event_id = request.headers.get('X-Razorpay-Event-Id', '')

    try:
        gateway = get_payment_gateway()
        if not gateway.verify_webhook_signature(raw_body, signature):
            current_app.logger.warning('Rejected Razorpay webhook: invalid signature')
            return jsonify({'status': 'invalid_signature'}), 400
    except Exception:
        current_app.logger.exception('Razorpay webhook signature validation failed')
        return jsonify({'status': 'invalid_signature'}), 400

    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return jsonify({'status': 'invalid_payload'}), 400

    event = str(payload.get('event', '')).strip()
    if not event:
        return jsonify({'status': 'invalid_payload'}), 400

    if event == 'payment.failed':
        payment_entity = ((payload.get('payload') or {}).get('payment') or {}).get('entity') or {}
        order_id = payment_entity.get('order_id')
        payment_id = payment_entity.get('id')
        if order_id:
            donation = Donation.query.filter(Donation.gateway_order_id == order_id).first()
            if donation and donation.status == 'PENDING':
                donation.status = 'FAILED'
                if payment_id:
                    donation.gateway_payment_id = payment_id
                db.session.commit()

    AuditService.log_action(
        'WEBHOOK',
        'RAZORPAY',
        event_id or None,
        f'Received verified Razorpay webhook: {event}',
        details={'event': event, 'event_id': event_id or None},
        commit=True,
    )

    return jsonify({'status': 'ok'}), 200
