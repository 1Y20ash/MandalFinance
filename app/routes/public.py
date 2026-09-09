from decimal import Decimal

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_limiter.util import get_remote_address

from app.extensions import csrf, db, limiter
from app.models.income import Donation
from app.models.ledger import Account
from app.models.mandal import Event, Mandal
from app.services.donation_service import DonationService
from app.services.ledger_service import LedgerService
from app.services.payment_gateway import get_payment_gateway


public_bp = Blueprint('public', __name__)


def _online_donation_account():
    configured_id = current_app.config.get('ONLINE_DONATION_ACCOUNT_ID')
    if configured_id:
        account = Account.query.filter_by(id=configured_id, is_active=True).first()
    else:
        account = Account.query.filter(
            Account.is_active.is_(True),
            Account.account_type.in_(['bank', 'upi']),
        ).first()
    if not account:
        raise ValueError('No active online-donation receiving account is configured.')
    return account


@public_bp.route('/transparency')
def transparency():
    mandal = Mandal.query.first()
    active_event = Event.query.filter_by(is_active=True).first()
    event_id = active_event.id if active_event else None
    summary = LedgerService.get_ledger_summary(event_id=event_id)
    approved_donations = Donation.query.filter_by(status='SUCCESS').count()
    return render_template(
        'public/transparency.html',
        mandal=mandal,
        active_event=active_event,
        summary=summary,
        approved_donations=approved_donations,
    )


@public_bp.route('/donate', methods=['GET', 'POST'])
@limiter.limit('10 per hour', methods=['POST'], key_func=get_remote_address)
def public_donate():
    active_event = Event.query.filter_by(is_active=True).first()
    if not active_event:
        flash('Donation portal is currently inactive.', 'warning')
        return redirect(url_for('public.transparency'))

    if request.method == 'POST':
        donor_name = request.form.get('donor_name', '').strip()
        donor_phone = request.form.get('donor_phone', '').strip() or None
        donor_email = request.form.get('donor_email', '').strip() or None
        amount_str = request.form.get('amount', '').strip()
        purpose = request.form.get('purpose', 'General Utsav Donation').strip()

        try:
            amount_dec = DonationService._normalize_amount(amount_str)
            if len(donor_name) < 2:
                raise ValueError('Donor name must contain at least 2 characters.')

            donation = Donation(
                donation_number=DonationService._generate_donation_number(),
                event_id=active_event.id,
                donor_name=donor_name,
                donor_phone=donor_phone,
                donor_email=donor_email,
                amount=amount_dec,
                purpose=purpose or 'General Utsav Donation',
                donation_type='ONLINE',
                payment_mode='ONLINE_GATEWAY',
                status='PENDING',
            )
            db.session.add(donation)
            db.session.flush()

            gateway = get_payment_gateway()
            order_info = gateway.create_order(amount_dec, donation.id, donor_name)
            donation.gateway_order_id = order_info['order_id']
            db.session.commit()

            return render_template(
                'public/checkout.html',
                donation=donation,
                order_info=order_info,
                active_event=active_event,
            )
        except Exception as exc:
            db.session.rollback()
            flash(f'Donation setup failed: {exc}', 'danger')

    return render_template('public/donate.html', active_event=active_event)


@public_bp.route('/donate/confirm', methods=['POST'])
@limiter.limit('20 per minute', methods=['POST'], key_func=get_remote_address)
def confirm_online_payment():
    donation_id = request.form.get('donation_id', type=int)
    payment_id = request.form.get('gateway_payment_id', '').strip()
    order_id = request.form.get('gateway_order_id', '').strip()
    signature = request.form.get('gateway_signature', '').strip()

    if not donation_id:
        flash('Invalid donation reference.', 'danger')
        return redirect(url_for('public.public_donate'))

    donation = Donation.query.get_or_404(donation_id)
    if donation.status == 'SUCCESS':
        return redirect(url_for('donations.download_receipt', donation_id=donation.id))

    if not donation.gateway_order_id or order_id != donation.gateway_order_id:
        donation.status = 'FAILED'
        db.session.commit()
        flash('Payment verification failed because the order reference did not match.', 'danger')
        return redirect(url_for('public.public_donate'))

    gateway = get_payment_gateway()
    if not gateway.verify_payment_signature(donation.gateway_order_id, payment_id, signature):
        donation.status = 'FAILED'
        db.session.commit()
        flash('Payment verification failed due to an invalid gateway signature.', 'danger')
        return redirect(url_for('public.public_donate'))

    try:
        account = _online_donation_account()
        DonationService.confirm_online_donation(
            donation.id,
            payment_id,
            signature,
            account.id,
        )
    except Exception as exc:
        flash(f'Payment could not be recorded: {exc}', 'danger')
        return redirect(url_for('public.public_donate'))

    flash(f'Thank you! Your donation was successful. Receipt No: {donation.receipt_number}', 'success')
    return redirect(url_for('donations.download_receipt', donation_id=donation.id))


@csrf.exempt
@public_bp.route('/donate/webhook', methods=['POST'])
@limiter.exempt
def payment_webhook():
    payload = request.get_data()
    signature = request.headers.get('X-Razorpay-Signature', '')
    event_id = request.headers.get('x-razorpay-event-id', '')

    gateway = get_payment_gateway()
    if not gateway.verify_webhook_signature(payload, signature):
        return jsonify({'status': 'invalid signature'}), 400

    data = request.get_json(silent=True) or {}
    event_type = data.get('event')
    if event_type not in {'payment.captured', 'order.paid'}:
        return jsonify({'status': 'ignored', 'event_id': event_id}), 200

    payment_entity = data.get('payload', {}).get('payment', {}).get('entity', {})
    order_entity = data.get('payload', {}).get('order', {}).get('entity', {})
    order_id = payment_entity.get('order_id') or order_entity.get('id')
    payment_id = payment_entity.get('id')

    donation = Donation.query.filter_by(gateway_order_id=order_id).first()
    if not donation:
        return jsonify({'status': 'unknown order', 'event_id': event_id}), 200
    if donation.status == 'SUCCESS':
        return jsonify({'status': 'already processed', 'event_id': event_id}), 200

    amount_paise = payment_entity.get('amount')
    status = payment_entity.get('status')
    captured = payment_entity.get('captured')
    expected_paise = int(Decimal(str(donation.amount)) * 100)
    if amount_paise is not None and int(amount_paise) != expected_paise:
        return jsonify({'status': 'amount mismatch', 'event_id': event_id}), 400
    if status not in (None, 'captured') and captured is not True:
        return jsonify({'status': 'payment not captured', 'event_id': event_id}), 200
    if not payment_id:
        return jsonify({'status': 'missing payment id', 'event_id': event_id}), 400

    try:
        account = _online_donation_account()
        DonationService.confirm_online_donation(
            donation.id,
            payment_id,
            f'WEBHOOK_VERIFIED:{event_id or "unknown"}',
            account.id,
        )
    except ValueError as exc:
        if 'already exists' in str(exc).lower() or 'already' in str(exc).lower():
            return jsonify({'status': 'already processed', 'event_id': event_id}), 200
        return jsonify({'status': 'processing failed'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'status': 'processing failed'}), 500

    return jsonify({'status': 'ok', 'event_id': event_id}), 200
