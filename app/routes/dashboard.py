from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from decimal import Decimal
from app.services.ledger_service import LedgerService
from app.models.income import Donation, Sponsorship, MemberContribution
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.mandal import Event
from app.utils.decorators import permission_required

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
@permission_required('dashboard.view')
def index():
    active_event = Event.query.filter_by(is_active=True).first()
    event_id = active_event.id if active_event else None
    summary = LedgerService.get_ledger_summary(event_id=event_id)

    donation_query = Donation.query.filter_by(status='SUCCESS')
    sponsorship_query = Sponsorship.query
    contribution_query = MemberContribution.query
    expense_query = Expense.query
    if event_id:
        donation_query = donation_query.filter(Donation.event_id == event_id)
        sponsorship_query = sponsorship_query.filter(Sponsorship.event_id == event_id)
        contribution_query = contribution_query.filter(MemberContribution.event_id == event_id)
        expense_query = expense_query.filter(Expense.event_id == event_id)

    total_donations = sum((d.amount for d in donation_query.all()), Decimal('0.00'))
    total_sponsorships = sum((s.received_amount for s in sponsorship_query.all()), Decimal('0.00'))
    total_contributions = sum((m.received_amount for m in contribution_query.all()), Decimal('0.00'))
    pending_approvals = expense_query.filter(Expense.status.in_(['SUBMITTED', 'UNDER_REVIEW'])).count()
    pending_payments = expense_query.filter_by(status='APPROVED').count()
    budget = Budget.query.filter_by(event_id=event_id).first() if event_id else None

    return render_template('dashboard/index.html', summary=summary,
        total_donations=total_donations, total_sponsorships=total_sponsorships,
        total_contributions=total_contributions, pending_approvals=pending_approvals,
        pending_payments=pending_payments, budget=budget, active_event=active_event)

@dashboard_bp.route('/analytics-data')
@login_required
@permission_required('dashboard.view')
def analytics_data():
    active_event = Event.query.filter_by(is_active=True).first()
    event_id = active_event.id if active_event else None
    expense_query = Expense.query.filter(Expense.status == 'PAID')
    if event_id:
        expense_query = expense_query.filter(Expense.event_id == event_id)

    # Financial values remain Decimal; JSON represents money as decimal strings.
    cat_totals = {}
    for expense in expense_query.all():
        cat_name = expense.category.name if expense.category else 'General'
        cat_totals[cat_name] = cat_totals.get(cat_name, Decimal('0.00')) + Decimal(expense.amount)

    summary = LedgerService.get_ledger_summary(event_id=event_id)
    return jsonify({
        'categories': list(cat_totals.keys()),
        'category_expenses': [str(value) for value in cat_totals.values()],
        'total_income': str(summary['total_income']),
        'total_expense': str(summary['total_expense']),
        'current_balance': str(summary['current_balance'])
    })
