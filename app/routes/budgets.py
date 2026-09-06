from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.budget import Budget, BudgetCategory
from app.models.mandal import Event
from app.models.expense import ExpenseCategory
from app.services.budget_service import BudgetService
from app.extensions import db
from app.utils.decorators import permission_required

budgets_bp = Blueprint('budgets', __name__, url_prefix='/budgets')

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

    budget = Budget.query.filter_by(event_id=active_event.id).first()

    if request.method == 'POST':
        total_income_target = Decimal(request.form.get('total_income_target', '0.00'))
        total_expense_limit = Decimal(request.form.get('total_expense_limit', '0.00'))

        if not budget:
            budget = Budget(
                event_id=active_event.id,
                total_income_target=total_income_target,
                total_expense_limit=total_expense_limit,
                created_by_id=current_user.id
            )
            db.session.add(budget)
        else:
            budget.total_income_target = total_income_target
            budget.total_expense_limit = total_expense_limit

        db.session.commit()

        # Update category limits
        categories = ExpenseCategory.query.filter_by(is_active=True).all()
        for cat in categories:
            limit_val = request.form.get(f'cat_limit_{cat.id}')
            if limit_val is not None:
                bcat = BudgetCategory.query.filter_by(event_id=active_event.id, expense_category_id=cat.id).first()
                if not bcat:
                    bcat = BudgetCategory(
                        event_id=active_event.id,
                        expense_category_id=cat.id,
                        allocated_amount=Decimal(limit_val)
                    )
                    db.session.add(bcat)
                else:
                    bcat.allocated_amount = Decimal(limit_val)

        db.session.commit()
        BudgetService.recalculate_event_budget(active_event.id)
        flash('Budget configured successfully.', 'success')
        return redirect(url_for('budgets.index'))

    categories = ExpenseCategory.query.filter_by(is_active=True).all()
    bcat_map = {}
    if budget:
        bcats = BudgetCategory.query.filter_by(event_id=active_event.id).all()
        bcat_map = {bc.expense_category_id: bc.allocated_amount for bc in bcats}

    return render_template('budgets/manage.html', budget=budget, categories=categories, bcat_map=bcat_map, active_event=active_event)
