from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models.income_entry import Income
from app.models.ledger import Account, TransactionCategory
from app.models.mandal import Event
from app.services.income_service import IncomeService
from app.utils.decorators import permission_required
from app.extensions import limiter

income_bp = Blueprint('income', __name__, url_prefix='/income')


@income_bp.route('/')
@login_required
@permission_required('income.view')
def list_income():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    category_id = request.args.get('category_id', type=int)
    payment_mode = request.args.get('payment_mode', '').strip()

    query = Income.query
    if search_query:
        term = f'%{search_query}%'
        query = query.filter((Income.income_ref.ilike(term)) | (Income.source_name.ilike(term)) | (Income.description.ilike(term)))
    if category_id:
        query = query.filter_by(category_id=category_id)
    if payment_mode:
        query = query.filter_by(payment_mode=payment_mode)

    pagination = query.order_by(Income.income_date.desc(), Income.created_at.desc()).paginate(page=page, per_page=15)
    categories = TransactionCategory.query.filter_by(category_type='income').order_by(TransactionCategory.name).all()
    return render_template('income/list.html', pagination=pagination, search_query=search_query,
                           categories=categories, category_id=category_id, payment_mode=payment_mode)


@income_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('income.create')
@limiter.limit('20 per minute', methods=['POST'])
def create_income():
    if request.method == 'POST':
        event_id = request.form.get('event_id', type=int)
        category_id = request.form.get('category_id', type=int)
        account_id = request.form.get('account_id', type=int)
        source_name = request.form.get('source_name', '').strip()
        description = request.form.get('description', '').strip()
        amount = request.form.get('amount')
        income_date_str = request.form.get('income_date')
        payment_mode = request.form.get('payment_mode', '').strip()
        transaction_ref = request.form.get('transaction_ref', '').strip()
        notes = request.form.get('notes', '').strip()

        try:
            income_date = datetime.strptime(income_date_str, '%Y-%m-%d').date() if income_date_str else datetime.utcnow().date()
            income = IncomeService.record_income(
                event_id=event_id, category_id=category_id, account_id=account_id,
                source_name=source_name, description=description, amount=amount,
                income_date=income_date, payment_mode=payment_mode,
                created_by_id=current_user.id, transaction_ref=transaction_ref, notes=notes,
            )
            flash(f'Income recorded successfully ({income.income_ref}) and posted to the central ledger.', 'success')
            return redirect(url_for('income.view_income', income_id=income.id))
        except Exception as e:
            flash(f'Error recording income: {e}', 'danger')

    events = Event.query.filter_by(is_active=True).all()
    categories = TransactionCategory.query.filter_by(category_type='income').order_by(TransactionCategory.name).all()
    accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
    return render_template('income/create.html', events=events, categories=categories, accounts=accounts)


@income_bp.route('/<int:income_id>')
@login_required
@permission_required('income.view')
def view_income(income_id):
    income = Income.query.get_or_404(income_id)
    return render_template('income/view.html', income=income)
