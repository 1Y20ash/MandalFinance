from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.expense import Expense, ExpenseCategory
from app.models.vendor import Vendor
from app.models.ledger import Account
from app.models.mandal import Event
from app.services.expense_service import ExpenseService
from app.utils.decorators import permission_required

expenses_bp = Blueprint('expenses', __name__, url_prefix='/expenses')

@expenses_bp.route('/')
@login_required
@permission_required('expense.view')
def list_expenses():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '').strip()
    category_id = request.args.get('category_id', type=int)

    query = Expense.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if category_id:
        query = query.filter_by(category_id=category_id)

    pagination = query.order_by(Expense.created_at.desc()).paginate(page=page, per_page=15)
    categories = ExpenseCategory.query.filter_by(is_active=True).all()
    return render_template('expenses/list.html', pagination=pagination, status_filter=status_filter, categories=categories, category_id=category_id)


@expenses_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('expense.create')
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
            expense_date = datetime.strptime(expense_date_str, '%Y-%m-%d').date() if expense_date_str else datetime.utcnow().date()
            bill_date = datetime.strptime(bill_date_str, '%Y-%m-%d').date() if bill_date_str else None

            expense = ExpenseService.submit_expense(
                event_id=event_id,
                category_id=category_id,
                title=title,
                description=description,
                amount=amount,
                expense_date=expense_date,
                created_by_user=current_user,
                vendor_id=vendor_id,
                bill_number=bill_number,
                bill_date=bill_date
            )
            flash(f'Expense submitted successfully ({expense.expense_ref}) and pending approval.', 'success')
            return redirect(url_for('expenses.view_expense', expense_id=expense.id))
        except Exception as e:
            flash(f'Error submitting expense: {str(e)}', 'danger')

    events = Event.query.filter_by(is_active=True).all()
    categories = ExpenseCategory.query.filter_by(is_active=True).all()
    vendors = Vendor.query.filter_by(is_active=True).all()
    return render_template('expenses/create.html', events=events, categories=categories, vendors=vendors)


@expenses_bp.route('/<int:expense_id>')
@login_required
@permission_required('expense.view')
def view_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    accounts = Account.query.filter_by(is_active=True).all()
    return render_template('expenses/view.html', expense=expense, accounts=accounts)


@expenses_bp.route('/<int:expense_id>/approve', methods=['POST'])
@login_required
@permission_required('expense.approve')
def approve_expense(expense_id):
    comments = request.form.get('comments', '').strip()
    try:
        ExpenseService.approve_expense(expense_id, current_user, comments=comments)
        flash('Expense approved successfully.', 'success')
    except Exception as e:
        flash(f'Approval failed: {str(e)}', 'danger')
    return redirect(url_for('expenses.view_expense', expense_id=expense_id))


@expenses_bp.route('/<int:expense_id>/reject', methods=['POST'])
@login_required
@permission_required('expense.reject')
def reject_expense(expense_id):
    reason = request.form.get('rejection_reason', '').strip()
    if not reason:
        flash('Rejection reason is required.', 'warning')
        return redirect(url_for('expenses.view_expense', expense_id=expense_id))
    try:
        ExpenseService.reject_expense(expense_id, current_user, rejection_reason=reason)
        flash('Expense rejected.', 'info')
    except Exception as e:
        flash(f'Rejection failed: {str(e)}', 'danger')
    return redirect(url_for('expenses.view_expense', expense_id=expense_id))


@expenses_bp.route('/<int:expense_id>/pay', methods=['POST'])
@login_required
@permission_required('expense.pay')
def pay_expense(expense_id):
    account_id = request.form.get('account_id', type=int)
    payment_mode = request.form.get('payment_mode')
    payment_ref = request.form.get('payment_ref', '').strip()

    try:
        ExpenseService.pay_expense(expense_id, current_user, account_id, payment_mode, payment_ref=payment_ref)
        flash('Expense paid and recorded in central financial ledger.', 'success')
    except Exception as e:
        flash(f'Payment processing failed: {str(e)}', 'danger')
    return redirect(url_for('expenses.view_expense', expense_id=expense_id))
