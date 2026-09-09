from decimal import Decimal

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from app.extensions import csrf, db
from app.models.auth import User
from app.models.income import Donation
from app.models.ledger import Account
from app.models.mandal import Event, Mandal
from app.models.payment_event import PaymentWebhookEvent
from app.services.donation_service import DonationService
from app.services.ledger_service import LedgerService
from app.services.payment_gateway import get_payment_gateway


public_bp = Blueprint('public', __name__)


def _online_donation_account():
    configured_id = current_app.config.get('ONLINE_DONATION_ACCOUNT_ID')
    if not configured_id:
        raise ValueError('Online donation receiving account is not configured.')
    account = Account.query.filter_by(id=int(configured_id), is_active=True).first()
    if not account:
        raise ValueError('Configured online-donation receiving account is unavailable.')
    if account.account_type not in {'bank', 'upi'}:
        raise ValueError('Online donations must post to an active bank or UPI account.')
    return account


def _online_donation_actor():
    configured_id = current_app.config.get('ONLINE_DONATION_ACTOR_ID')
    if not configured_id:
        raise ValueError('Online donation system actor is not configured.')
    actor = User.query.filter_by(id=int(configured_id), is_active=True).first()
    if not actor:
        raise ValueError('Configured online-donation system actor is unavailable.')
    return actor


def _verified_payment_or_raise(gateway, donation, payment_id):
    return gateway.verify_payment(
        donation.gateway_order_id,
        payment_id,
        donation.amount,
        expected_currency='INR',
    )


@public_bp.route('/transparency')
def transparency():
    mandal = Mandal.query.first()
    active_event = Event.query.filter_by(is_active=True).first()
    event_id = active_event.id if active_event else None
    summary = LedgerService.get_ledger_summary(event_id=event_id)
    approved_donations = Donation.query.filter_by(status='SUCCESS').count()
    return render_template('public/transparency.html', mandal=mandal, active_event=active_event,
                           summary=summary, approved_donations=approved_donations)


@public_bp.route('/donate', methods=['GET', 'POST'])
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
            system_actor = _online_donation_actor()
            donation = Donation(
                donation_number=DonationService._generate_donation_number(), event_id=active_event.id,
                donor_name=donor_name, donor_phone=donor_phone, donor_email=donor_email,
                amount=amount_dec, purpose=purpose or 'General Utsav Donation',
                donation_type='ONLINE', payment_mode='ONLINE_GATEWAY', status='PENDING',
                created_by_id=system_actor.id,
            )
            db.session.add(donation)
            db.session.flush()
            gateway = get_payment_gateway()
            order_info = gateway.create_order(amount_dec, donation.id, donor_name)
            if int(order_info['amount_in_paise']) != int(amount_dec * 100) or order_info['currency'] != 'INR':
                raise ValueError('Payment gateway returned an unexpected order amount or currency.')
            donation.gateway_order_id = order_info['order_id']
            db.session.commit()
            return render_template('public/checkout.html', donation=donation, order_info=order_info,
                                   active_event=active_event)
        except Exception:
            db.session.rollback()
            flash('Donation setup failed. Please try again.', 'danger')
    return render_template('public/donate.html', active_event=active_event)


@public_bp.route('/donate/confirm', methods=['POST'])
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
        flash('Payment verification failed. Please restart the payment.', 'danger')
        return redirect(url_for('public.public_donate'))

    gateway = get_payment_gateway()
    if not gateway.verify_payment_signature(donation.gateway_order_id, payment_id, signature):
        flash('Payment verification failed. Please try again or wait for payment confirmation.', 'danger')
        return redirect(url_for('public.public_donate'))

    try:
        verified = _verified_payment_or_raise(gateway, donation, payment_id)
        account = _online_donation_account()
        DonationService.confirm_online_donation(
            donation.id, payment_id, signature, account.id,
            verified_order_id=verified['order_id'], verified_amount_paise=verified['amount'],
            verified_currency=verified['currency'], verified_status=verified['status'],
        )
    except Exception:
        db.session.rollback()
        flash('Payment could not be verified or recorded. Your donation remains pending.', 'danger')
        return redirect(url_for('public.public_donate'))

    flash(f'Thank you! Your donation was successful. Receipt No: {donation.receipt_number}', 'success')
    return redirect(url_for('donations.download_receipt', donation_id=donation.id))


@csrf.exempt
@public_bp.route('/donate/webhook', methods=['POST'])
def payment_webhook():
    payload = request.get_data()
    signature = request.headers.get('X-Razorpay-Signature', '')
    event_id = request.headers.get('x-razorpay-event-id', '').strip()
    gateway = get_payment_gateway()
    if not gateway.verify_webhook_signature(payload, signature):
        return jsonify({'status': 'invalid signature'}), 400
    if not event_id:
        return jsonify({'status': 'missing event id'}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'status': 'invalid payload'}), 400
    event_type = data.get('event')
    if event_type not in {'payment.captured', 'order.paid'}:
        try:
            db.session.add(PaymentWebhookEvent(event_id=event_id,
                                               event_type=str(event_type or 'unknown')[:80],
                                               status='IGNORED'))
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return jsonify({'status': 'ignored', 'event_id': event_id}), 200

    payment_entity = data.get('payload', {}).get('payment', {}).get('entity', {})
    order_entity = data.get('payload', {}).get('order', {}).get('entity', {})
    order_id = payment_entity.get('order_id') or order_entity.get('id')
    payment_id = payment_entity.get('id')
    if not order_id or not payment_id:
        return jsonify({'status': 'missing payment identity'}), 400
    if PaymentWebhookEvent.query.filter_by(event_id=event_id).first():
        return jsonify({'status': 'already processed', 'event_id': event_id}), 200

    donation = Donation.query.filter_by(gateway_order_id=order_id).first()
    if not donation:
        return jsonify({'status': 'unknown order', 'event_id': event_id}), 200

    amount_paise = payment_entity.get('amount')
    currency = payment_entity.get('currency')
    status = payment_entity.get('status')
    captured = payment_entity.get('captured')
    expected_paise = int(Decimal(str(donation.amount)) * 100)
    if amount_paise is None or int(amount_paise) != expected_paise:
        return jsonify({'status': 'amount mismatch', 'event_id': event_id}), 400
    if currency != 'INR':
        return jsonify({'status': 'currency mismatch', 'event_id': event_id}), 400
    if status != 'captured' or captured is not True:
        return jsonify({'status': 'payment not captured', 'event_id': event_id}), 200

    try:
        verified = _verified_payment_or_raise(gateway, donation, payment_id)
        account = _online_donation_account()
        event_record = PaymentWebhookEvent(
            event_id=event_id, event_type=event_type, order_id=order_id,
            payment_id=payment_id, donation_id=donation.id, status='PROCESSED',
        )
        db.session.add(event_record)
        db.session.flush()
        if donation.status == 'SUCCESS':
            event_record.status = 'IGNORED'
            db.session.commit()
            return jsonify({'status': 'already processed', 'event_id': event_id}), 200

        DonationService.confirm_online_donation(
            donation.id, payment_id, None, account.id,
            verified_order_id=verified['order_id'], verified_amount_paise=verified['amount'],
            verified_currency=verified['currency'], verified_status=verified['status'], commit=False,
        )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'status': 'already processed', 'event_id': event_id}), 200
    except Exception:
        db.session.rollback()
        return jsonify({'status': 'processing failed', 'event_id': event_id}), 500
    return jsonify({'status': 'ok', 'event_id': event_id}), 200
