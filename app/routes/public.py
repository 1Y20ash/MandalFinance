from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from app.models.income import Donation
from app.models.ledger import Account
from app.models.mandal import Event, Mandal
from app.services.ledger_service import LedgerService
from app.services.payment_gateway import get_payment_gateway
from app.services.donation_service import DonationService
from app.extensions import db

public_bp = Blueprint('public', __name__)

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
        approved_donations=approved_donations
    )


@public_bp.route('/donate', methods=['GET', 'POST'])
def public_donate():
    active_event = Event.query.filter_by(is_active=True).first()
    if not active_event:
        flash('Donation portal is currently inactive.', 'warning')
        return redirect(url_for('public.transparency'))

    if request.method == 'POST':
        donor_name = request.form.get('donor_name', '').strip()
        donor_phone = request.form.get('donor_phone', '').strip()
        donor_email = request.form.get('donor_email', '').strip()
        amount_str = request.form.get('amount')
        purpose = request.form.get('purpose', 'General Donation').strip()

        try:
            amount_dec = Decimal(amount_str)
            if amount_dec <= Decimal('0.00'):
                raise ValueError("Amount must be greater than zero.")

            # Create PENDING donation record
            donation_num = DonationService._generate_donation_number()
            donation = Donation(
                donation_number=donation_num,
                event_id=active_event.id,
                donor_name=donor_name,
                donor_phone=donor_phone,
                donor_email=donor_email,
                amount=amount_dec,
                purpose=purpose,
                donation_type='ONLINE',
                payment_mode='ONLINE_GATEWAY',
                status='PENDING'
            )
            db.session.add(donation)
            db.session.commit()

            # Create Order via Payment Gateway Abstraction
            gateway = get_payment_gateway()
            order_info = gateway.create_order(amount_dec, donation.id, donor_name)
            donation.gateway_order_id = order_info['order_id']
            db.session.commit()

            return render_template(
                'public/checkout.html',
                donation=donation,
                order_info=order_info,
                active_event=active_event
            )
        except Exception as e:
            flash(f'Donation setup failed: {str(e)}', 'danger')

    return render_template('public/donate.html', active_event=active_event)


@public_bp.route('/donate/confirm', methods=['POST'])
def confirm_online_payment():
    donation_id = request.form.get('donation_id', type=int)
    payment_id = request.form.get('gateway_payment_id')
    signature = request.form.get('gateway_signature')

    donation = Donation.query.get_or_404(donation_id)
    gateway = get_payment_gateway()

    is_valid = gateway.verify_payment_signature(donation.gateway_order_id, payment_id, signature)
    if not is_valid:
        donation.status = 'FAILED'
        db.session.commit()
        flash('Payment verification failed due to invalid signature.', 'danger')
        return redirect(url_for('public.public_donate'))

    # Confirm donation and post to Ledger using default Bank/UPI account
    account = Account.query.filter_by(is_active=True).first()
    account_id = account.id if account else 1

    DonationService.confirm_online_donation(donation.id, payment_id, signature, account_id)
    flash(f'Thank you! Your donation was successful. Receipt No: {donation.receipt_number}', 'success')
    return redirect(url_for('donations.download_receipt', donation_id=donation.id))


@public_bp.route('/donate/webhook', methods=['POST'])
def payment_webhook():
    payload = request.get_data()
    signature = request.headers.get('X-Razorpay-Signature', '')

    gateway = get_payment_gateway()
    if not gateway.verify_webhook_signature(payload, signature):
        return jsonify({'status': 'invalid signature'}), 400

    data = request.get_json(silent=True) or {}
    event_type = data.get('event')

    if event_type == 'payment.captured':
        payment_entity = data.get('payload', {}).get('payment', {}).get('entity', {})
        order_id = payment_entity.get('order_id')
        payment_id = payment_entity.get('id')

        donation = Donation.query.filter_by(gateway_order_id=order_id).first()
        if donation and donation.status != 'SUCCESS':
            account = Account.query.filter_by(is_active=True).first()
            account_id = account.id if account else 1
            DonationService.confirm_online_donation(donation.id, payment_id, 'WEBHOOK_VERIFIED', account_id)

    return jsonify({'status': 'ok'}), 200
