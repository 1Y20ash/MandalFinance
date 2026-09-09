from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db, limiter
from app.models.contribution import SponsorshipPayment, MemberContributionPayment
from app.models.income import Sponsorship, MemberContribution
from app.models.ledger import Account
from app.models.mandal import Event
from app.services.contribution_service import ContributionService
from app.utils.decorators import permission_required

contributions_bp = Blueprint('contributions', __name__, url_prefix='/contributions')


@contributions_bp.get('/')
@login_required
@permission_required('finance.view')
def index():
    event = Event.query.filter_by(is_active=True).first()
    sponsorships = Sponsorship.query.filter_by(event_id=event.id).order_by(Sponsorship.created_at.desc()).all() if event else []
    members = MemberContribution.query.filter_by(event_id=event.id).order_by(MemberContribution.created_at.desc()).all() if event else []
    sponsorship_summary = ContributionService.sponsorship_summary(event.id) if event else {}
    member_summary = ContributionService.member_summary(event.id) if event else {}
    accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
    return render_template('contributions/index.html', active_event=event, sponsorships=sponsorships,
                           members=members, sponsorship_summary=sponsorship_summary,
                           member_summary=member_summary, accounts=accounts)


@contributions_bp.post('/sponsorships/create')
@login_required
@permission_required('finance.manage')
@limiter.limit('20 per minute')
def create_sponsorship():
    event = Event.query.filter_by(is_active=True).first()
    if not event:
        flash('No active event is available.', 'warning')
        return redirect(url_for('contributions.index'))
    try:
        ContributionService.create_sponsorship(
            event_id=event.id, sponsor_name=request.form.get('sponsor_name'),
            sponsorship_type=request.form.get('sponsorship_type'),
            committed_amount=request.form.get('committed_amount'), created_by_id=current_user.id,
            contact_person=request.form.get('contact_person'), contact_phone=request.form.get('contact_phone'),
            contact_email=request.form.get('contact_email'), notes=request.form.get('notes'),
        )
        flash('Sponsorship commitment recorded.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    return redirect(url_for('contributions.index'))


@contributions_bp.post('/members/create')
@login_required
@permission_required('finance.manage')
@limiter.limit('20 per minute')
def create_member_contribution():
    event = Event.query.filter_by(is_active=True).first()
    if not event:
        flash('No active event is available.', 'warning')
        return redirect(url_for('contributions.index'))
    try:
        ContributionService.create_member_contribution(
            event_id=event.id, member_name=request.form.get('member_name'),
            target_amount=request.form.get('target_amount'), created_by_id=current_user.id,
            member_phone=request.form.get('member_phone'), designation=request.form.get('designation'),
            notes=request.form.get('notes'),
        )
        flash('Member contribution target recorded.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    return redirect(url_for('contributions.index'))


@contributions_bp.post('/sponsorships/<int:sponsorship_id>/payments')
@login_required
@permission_required('finance.manage')
@limiter.limit('20 per minute')
def record_sponsorship_payment(sponsorship_id):
    try:
        ContributionService.record_sponsorship_payment(
            sponsorship_id=sponsorship_id, account_id=request.form.get('account_id', type=int),
            amount=request.form.get('amount'), payment_mode=request.form.get('payment_mode'),
            transaction_ref=request.form.get('transaction_ref'), created_by_id=current_user.id,
            notes=request.form.get('notes'),
        )
        flash('Sponsorship payment recorded and posted to the central ledger.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    return redirect(url_for('contributions.index'))


@contributions_bp.post('/members/<int:contribution_id>/payments')
@login_required
@permission_required('finance.manage')
@limiter.limit('20 per minute')
def record_member_payment(contribution_id):
    try:
        ContributionService.record_member_payment(
            contribution_id=contribution_id, account_id=request.form.get('account_id', type=int),
            amount=request.form.get('amount'), payment_mode=request.form.get('payment_mode'),
            transaction_ref=request.form.get('transaction_ref'), created_by_id=current_user.id,
            notes=request.form.get('notes'),
        )
        flash('Member contribution payment recorded and posted to the central ledger.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    return redirect(url_for('contributions.index'))
