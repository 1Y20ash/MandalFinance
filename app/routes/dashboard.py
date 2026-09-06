from flask import Blueprint, render_template, jsonify
from flask_login import login_required
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
    
    total_donations = sum(d.amount for d in Donation.query.filter_by(status='SUCCESS').all())
    total_sponsorships = sum(s.received_amount for s in Sponsorship.query.all())
    total_contributions = sum(m.received_amount for m in MemberContribution.query.all())
    
    pending_approvals = Expense.query.filter(Expense.status.in_(['SUBMITTED', 'UNDER_REVIEW'])).count()
    pending_payments = Expense.query.filter_by(status='APPROVED').count()

    budget = Budget.query.filter_by(event_id=event_id).first() if event_id else None

    return render_template(
        'dashboard/index.html',
        summary=summary,
        total_donations=total_donations,
        total_sponsorships=total_sponsorships,
        total_contributions=total_contributions,
        pending_approvals=pending_approvals,
        pending_payments=pending_payments,
        budget=budget,
        active_event=active_event
    )

@dashboard_bp.route('/analytics-data')
@login_required
@permission_required('dashboard.view')
def analytics_data():
    # Category expense distribution
    expenses = Expense.query.filter(Expense.status == 'PAID').all()
    cat_totals = {}
    for e in expenses:
        cat_name = e.category.name if e.category else 'General'
        cat_totals[cat_name] = cat_totals.get(cat_name, 0.0) + float(e.amount)

    # Monthly income/expense trends
    summary = LedgerService.get_ledger_summary()

    return jsonify({
        'categories': list(cat_totals.keys()),
        'category_expenses': list(cat_totals.values()),
        'total_income': float(summary['total_income']),
        'total_expense': float(summary['total_expense']),
        'current_balance': float(summary['current_balance'])
    })
