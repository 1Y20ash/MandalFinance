from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models.expense import Expense, ExpenseCategory
from app.models.vendor import Vendor
from app.models.ledger import Account
from app.models.mandal import Event
from app.services.expense_service import ExpenseService
from app.services.expense_category_service import ExpenseCategoryService
from app.utils.decorators import permission_required, admin_required
from app.extensions import limiter

expenses_bp = Blueprint('expenses', __name__, url_prefix='/expenses')


@expenses_bp.route('/')
@login_required
@permission_required('expense.view')
def list_expenses():
    page = max(request.args.get('page', 1, type=int), 1)
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    category_id = request.args.get('category_id', type=int)

    query = Expense.query
    if search_query:
        term = f'%{search_query}%'
        query = query.filter(
            (Expense.expense_ref.ilike(term))
            | (Expense.title.ilike(term))
            | (Expense.description.ilike(term))
            | (Expense.bill_number.ilike(term))
            | (Expense.payment_ref.ilike(term))
        )
    if status_filter:
        query = query.filter_by(status=status_filter)
    if category_id:
        query = query.filter_by(category_id=category_id)

    pagination = query.order_by(Expense.expense_date.desc(), Expense.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    categories = ExpenseCategory.query.filter_by(is_active=True).order_by(ExpenseCategory.name).all()
    return render_template(
        'expenses/list.html', pagination=pagination, search_query=search_query,
        status_filter=status_filter, categories=categories, category_id=category_id,
    )


@expenses_bp.route('/categories')
@login_required
@admin_required
def list_expense_categories():
    categories = ExpenseCategory.query.order_by(ExpenseCategory.is_active.desc(), ExpenseCategory.name.asc()).all()
    return render_template('expenses/categories.html', categories=categories)


@expenses_bp.route('/categories/create', methods=['POST'])
@login_required
@admin_required
@limiter.limit('30 per minute', methods=['POST'])
def create_expense_category():
    try:
        ExpenseCategoryService.create(
            request.form.get('name'), request.form.get('description'), current_user,
        )
        flash('Expense category created successfully.', 'success')
    except (ValueError, PermissionError) as exc:
        flash(str(exc), 'danger')
    except Exception:
        flash('Unable to create the expense category. No changes were saved.', 'danger')
    return redirect(url_for('expenses.list_expense_categories'))


@expenses_bp.route('/categories/<int:category_id>/edit', methods=['POST'])
@login_required
@admin_required
@limiter.limit('30 per minute', methods=['POST'])
def edit_expense_category(category_id):
    try:
        ExpenseCategoryService.update(
            category_id, request.form.get('name'), request.form.get('description'), current_user,
        )
        flash('Expense category updated successfully.', 'success')
    except (ValueError, PermissionError) as exc:
        flash(str(exc), 'danger')
    except Exception:
        flash('Unable to update the expense category. No changes were saved.', 'danger')
    return redirect(url_for('expenses.list_expense_categories'))


@expenses_bp.route('/categories/<int:category_id>/toggle', methods=['POST'])
@login_required
@admin_required
@limiter.limit('30 per minute', methods=['POST'])
def toggle_expense_category(category_id):
    category = ExpenseCategory.query.get_or_404(category_id)
    try:
        ExpenseCategoryService.set_active(category_id, not category.is_active, current_user)
        state = 'activated' if category.is_active else 'deactivated'
        flash(f'Expense category "{category.name}" {state}.', 'success')
    except (ValueError, PermissionError) as exc:
        flash(str(exc), 'danger')
    except Exception:
        flash('Unable to change the category status. No changes were saved.', 'danger')
    return redirect(url_for('expenses.list_expense_categories'))


@expenses_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('expense.create')
@limiter.limit('20 per minute', methods=['POST'])
def create_expense():
    if request.method == 'POST':
        event_id = request.form.get('event_id', type=int)
        category_id = request.form.get('category_id', type=int)
        vendor_id = request.form.get('vendor_id', type=int) or None
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        amount = request.form.get('amount')
        expense_date_str = request.form.get('expense_date')
        bill_number = request.form.get('bill_number', '').strip()
        bill_date_str = request.form.get('bill_date')

        try:
            expense_date = datetime.strptime(expense_date_str, '%Y-%m-%d').date() if expense_date_str else None
            bill_date = datetime.strptime(bill_date_str, '%Y-%m-%d').date() if bill_date_str else None
            expense = ExpenseService.submit_expense(
                event_id=event_id, category_id=category_id, title=title, description=description,
                amount=amount, expense_date=expense_date, created_by_user=current_user,
                vendor_id=vendor_id, bill_number=bill_number, bill_date=bill_date,
            )
            flash(f'Expense submitted successfully ({expense.expense_ref}) and pending approval.', 'success')
            return redirect(url_for('expenses.view_expense', expense_id=expense.id))
        except (ValueError, TypeError) as e:
            flash(f'Error submitting expense: {e}', 'danger')
        except Exception:
            flash('An unexpected error occurred while submitting the expense. No changes were saved.', 'danger')

    events = Event.query.filter_by(is_active=True).order_by(Event.year.desc(), Event.title).all()
    categories = ExpenseCategory.query.filter_by(is_active=True).order_by(ExpenseCategory.name).all()
    vendors = Vendor.query.filter_by(is_active=True).order_by(Vendor.name).all()
    return render_template('expenses/create.html', events=events, categories=categories, vendors=vendors)


@expenses_bp.route('/<int:expense_id>')
@login_required
@permission_required('expense.view')
def view_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
    return render_template('expenses/view.html', expense=expense, accounts=accounts)


@expenses_bp.route('/<int:expense_id>/approve', methods=['POST'])
@login_required
@permission_required('expense.approve')
@limiter.limit('30 per minute', methods=['POST'])
def approve_expense(expense_id):
    comments = request.form.get('comments', '').strip()
    try:
        ExpenseService.approve_expense(expense_id, current_user, comments=comments)
        flash('Expense approved successfully.', 'success')
    except Exception as e:
        flash(f'Approval failed: {e}', 'danger')
    return redirect(url_for('expenses.view_expense', expense_id=expense_id))


@expenses_bp.route('/<int:expense_id>/reject', methods=['POST'])
@login_required
@permission_required('expense.reject')
@limiter.limit('30 per minute', methods=['POST'])
def reject_expense(expense_id):
    reason = request.form.get('rejection_reason', '').strip()
    if not reason:
        flash('Rejection reason is required.', 'warning')
        return redirect(url_for('expenses.view_expense', expense_id=expense_id))
    try:
        ExpenseService.reject_expense(expense_id, current_user, rejection_reason=reason)
        flash('Expense rejected.', 'info')
    except Exception as e:
        flash(f'Rejection failed: {e}', 'danger')
    return redirect(url_for('expenses.view_expense', expense_id=expense_id))


@expenses_bp.route('/<int:expense_id>/pay', methods=['POST'])
@login_required
@permission_required('expense.pay')
@limiter.limit('20 per minute', methods=['POST'])
def pay_expense(expense_id):
    account_id = request.form.get('account_id', type=int)
    payment_mode = request.form.get('payment_mode', '').strip()
    payment_ref = request.form.get('payment_ref', '').strip()

    try:
        ExpenseService.pay_expense(
            expense_id, current_user, account_id, payment_mode, payment_ref=payment_ref
        )
        flash('Expense paid and recorded in the central financial ledger.', 'success')
    except Exception as e:
        flash(f'Payment processing failed: {e}', 'danger')
    return redirect(url_for('expenses.view_expense', expense_id=expense_id))
