from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.extensions import db, limiter
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
        account = Account.query.filter(Account.is_active.is_(True), Account.account_type.in_(['bank', 'upi'])).first()
    if not account:
        raise ValueError('No active online-donation receiving account is configured.')
    return account


@public_bp.route('/privacy')
def privacy():
    return render_template('public/privacy.html')


@public_bp.route('/transparency')
def transparency():
    mandal = Mandal.query.first()
    active_event = Event.query.filter_by(is_active=True).first()
    event_id = active_event.id if active_event else None
    summary = LedgerService.get_ledger_summary(event_id=event_id)
    approved_donations = Donation.query.filter_by(status='SUCCESS').count()
    return render_template('public/transparency.html', mandal=mandal, active_event=active_event, summary=summary, approved_donations=approved_donations)


@public_bp.route('/donate', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
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
            if request.form.get('privacy_ack') != 'on':
                raise ValueError('Please acknowledge the privacy notice before continuing.')
            donation = Donation(
                donation_number=DonationService._generate_donation_number(), event_id=active_event.id,
                donor_name=donor_name, donor_phone=donor_phone, donor_email=donor_email,
                amount=amount_dec, purpose=purpose or 'General Utsav Donation',
                donation_type='ONLINE', payment_mode='ONLINE_GATEWAY', status='PENDING',
            )
            db.session.add(donation)
            db.session.flush()
            order_info = get_payment_gateway().create_order(amount_dec, donation.id, donor_name)
            donation.gateway_order_id = order_info['order_id']
            db.session.commit()
            return render_template('public/checkout.html', donation=donation, order_info=order_info, active_event=active_event)
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), 'warning')
        except Exception:
            db.session.rollback()
            flash('Donation setup failed. Please try again later.', 'danger')
    return render_template('public/donate.html', active_event=active_event)


@public_bp.route('/donate/confirm', methods=['POST'])
@limiter.limit('10 per minute')
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
        DonationService.confirm_online_donation(donation.id, payment_id, signature, account.id)
    except Exception:
        flash('Payment could not be recorded. Please contact the Mandal administrator if funds were debited.', 'danger')
        return redirect(url_for('public.public_donate'))
    flash(f'Thank you! Your donation was successful. Receipt No: {donation.receipt_number}', 'success')
    return redirect(url_for('donations.download_receipt', donation_id=donation.id))
