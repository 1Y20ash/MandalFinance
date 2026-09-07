from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.models.budget import Budget, BudgetCategory
from app.models.mandal import Event
from app.models.expense import ExpenseCategory
from app.services.budget_service import BudgetService
from app.services.audit_service import AuditService
from app.extensions import db
from app.utils.decorators import permission_required

budgets_bp = Blueprint('budgets', __name__, url_prefix='/budgets')


def _money(value):
    try:
        amount = Decimal(str(value or '0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError('Budget amounts must be valid monetary values.')
    if amount < 0:
        raise ValueError('Budget amounts cannot be negative.')
    return amount


@budgets_bp.route('/')
@login_required
@permission_required('budget.view')
def index():
    active_event = Event.query.filter_by(is_active=True).first()
    event_id = active_event.id if active_event else None
    if event_id:
        BudgetService.recalculate_event_budget(event_id)
    budget = Budget.query.filter_by(event_id=event_id).first() if event_id else None
    budget_categories = BudgetCategory.query.filter_by(event_id=event_id).all() if event_id else []
    return render_template('budgets/index.html', budget=budget, budget_categories=budget_categories, active_event=active_event)


@budgets_bp.route('/manage', methods=['GET', 'POST'])
@login_required
@permission_required('budget.edit')
def manage_budget():
    active_event = Event.query.filter_by(is_active=True).first()
    if not active_event:
        flash('No active event found to set budget.', 'warning')
        return redirect(url_for('budgets.index'))
    active_event.assert_editable()
    budget = Budget.query.filter_by(event_id=active_event.id).first()

    if request.method == 'POST':
        try:
            income_target = _money(request.form.get('total_income_target'))
            expense_limit = _money(request.form.get('total_expense_limit'))
            if not budget:
                budget = Budget(event_id=active_event.id, total_income_target=income_target,
                                total_expense_limit=expense_limit, created_by_id=current_user.id, status='DRAFT')
                db.session.add(budget)
                db.session.flush()
            else:
                if not budget.is_editable:
                    budget.status = 'REVISED'
                    budget.revision_no += 1
                    budget.revision_reason = request.form.get('revision_reason', '').strip() or 'Budget revision requested.'
                budget.total_income_target = income_target
                budget.total_expense_limit = expense_limit

            categories = ExpenseCategory.query.filter_by(is_active=True).all()
            for cat in categories:
                raw = request.form.get(f'cat_limit_{cat.id}')
                if raw is None:
                    continue
                limit_val = _money(raw)
                bcat = BudgetCategory.query.filter_by(event_id=active_event.id, expense_category_id=cat.id).first()
                if not bcat:
                    bcat = BudgetCategory(event_id=active_event.id, expense_category_id=cat.id, allocated_amount=limit_val)
                    db.session.add(bcat)
                else:
                    bcat.allocated_amount = limit_val

            BudgetService.recalculate_event_budget(active_event.id)
            AuditService.log_action('UPDATE', 'BUDGET', budget.id,
                                    f'Budget revision {budget.revision_no} configured for event {active_event.title}.', commit=False)
            db.session.commit()
            flash('Budget configured successfully. It remains pending approval.', 'success')
        except (ValueError, TypeError) as exc:
            db.session.rollback()
            flash(str(exc), 'danger')
        return redirect(url_for('budgets.index'))

    categories = ExpenseCategory.query.filter_by(is_active=True).all()
    bcats = BudgetCategory.query.filter_by(event_id=active_event.id).all() if budget else []
    bcat_map = {bc.expense_category_id: bc.allocated_amount for bc in bcats}
    return render_template('budgets/manage.html', budget=budget, categories=categories, bcat_map=bcat_map, active_event=active_event)


@budgets_bp.post('/<int:budget_id>/approve')
@login_required
@permission_required('budget.approve')
def approve_budget(budget_id):
    budget = db.session.get(Budget, budget_id)
    if not budget:
        abort(404)
    if budget.status not in {'DRAFT', 'REVISED'}:
        flash('Only draft or revised budgets can be approved.', 'warning')
        return redirect(url_for('budgets.index'))
    event = db.session.get(Event, budget.event_id)
    event.assert_editable()
    if budget.created_by_id == current_user.id:
        abort(403)
    budget.status = 'APPROVED'
    budget.approved_by_id = current_user.id
    budget.approved_at = datetime.utcnow()
    AuditService.log_action('APPROVE', 'BUDGET', budget.id, f'Budget revision {budget.revision_no} approved.', commit=False)
    db.session.commit()
    flash('Budget approved.', 'success')
    return redirect(url_for('budgets.index'))


@budgets_bp.post('/<int:budget_id>/revise')
@login_required
@permission_required('budget.edit')
def revise_budget(budget_id):
    budget = db.session.get(Budget, budget_id)
    if not budget:
        abort(404)
    db.session.get(Event, budget.event_id).assert_editable()
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('A revision reason is required.', 'danger')
        return redirect(url_for('budgets.index'))
    budget.status = 'REVISED'
    budget.revision_no += 1
    budget.revision_reason = reason
    budget.approved_by_id = None
    budget.approved_at = None
    AuditService.log_action('REVISE', 'BUDGET', budget.id, f'Budget revision requested: {reason}', commit=False)
    db.session.commit()
    flash('Budget marked for revision and re-approval.', 'success')
    return redirect(url_for('budgets.index'))
