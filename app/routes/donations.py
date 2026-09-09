from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from app.models.income import Donation
from app.models.ledger import Account
from app.models.mandal import Event
from app.services.donation_service import DonationService
from app.utils.pdf_generator import generate_donation_receipt_pdf
from app.utils.decorators import permission_required
from app.extensions import limiter

donations_bp = Blueprint('donations', __name__, url_prefix='/donations')

@donations_bp.route('/')
@login_required
@permission_required('donation.view')
def list_donations():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = Donation.query
    if search_query:
        query = query.filter((Donation.donor_name.ilike(f'%{search_query}%')) |
                             (Donation.donation_number.ilike(f'%{search_query}%')) |
                             (Donation.receipt_number.ilike(f'%{search_query}%')))
    if status_filter:
        query = query.filter_by(status=status_filter)

    pagination = query.order_by(Donation.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('donations/list.html', pagination=pagination, search_query=search_query, status_filter=status_filter)


@donations_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('donation.create')
@limiter.limit('20 per minute', methods=['POST'])
def create_donation():
    if request.method == 'POST':
        event_id = request.form.get('event_id', type=int)
        donor_name = request.form.get('donor_name', '').strip()
        donor_phone = request.form.get('donor_phone', '').strip()
        donor_email = request.form.get('donor_email', '').strip()
        donor_address = request.form.get('donor_address', '').strip()
        pan_number = request.form.get('pan_number', '').strip()
        amount = request.form.get('amount')
        purpose = request.form.get('purpose', 'General Donation').strip()
        payment_mode = request.form.get('payment_mode')
        account_id = request.form.get('account_id', type=int)
        transaction_ref = request.form.get('transaction_ref', '').strip()
        notes = request.form.get('notes', '').strip()

        try:
            donation = DonationService.record_offline_donation(
                event_id=event_id,
                donor_name=donor_name,
                amount=amount,
                payment_mode=payment_mode,
                account_id=account_id,
                created_by_id=current_user.id,
                donor_phone=donor_phone,
                donor_email=donor_email,
                donor_address=donor_address,
                pan_number=pan_number,
                purpose=purpose,
                transaction_ref=transaction_ref,
                notes=notes
            )
            flash(f'Donation recorded successfully! Receipt No: {donation.receipt_number}', 'success')
            return redirect(url_for('donations.view_donation', donation_id=donation.id))
        except Exception:
            flash('Unable to record the donation. Please verify the details and try again.', 'danger')

    events = Event.query.filter_by(is_active=True).all()
    accounts = Account.query.filter_by(is_active=True).all()
    return render_template('donations/create.html', events=events, accounts=accounts)


@donations_bp.route('/<int:donation_id>')
@login_required
@permission_required('donation.view')
def view_donation(donation_id):
    donation = Donation.query.get_or_404(donation_id)
    return render_template('donations/view.html', donation=donation)


@donations_bp.route('/<int:donation_id>/receipt')
@login_required
@permission_required('donation.receipt')
@limiter.limit('30 per minute')
def download_receipt(donation_id):
    donation = Donation.query.get_or_404(donation_id)
    if donation.status != 'SUCCESS':
        flash('Receipts are only available for confirmed successful donations.', 'warning')
        return redirect(url_for('donations.view_donation', donation_id=donation.id))

    event_title = donation.event.title if donation.event else "Ganesh Utsav 2026"
    pdf_bytes = generate_donation_receipt_pdf(donation, event_title=event_title)

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=Receipt_{donation.receipt_number or donation.donation_number}.pdf'
    return response
