import csv
import io

from flask import Blueprint, render_template, request, make_response
from flask_login import login_required

from app.services.ledger_service import LedgerService
from app.models.income import Donation, Sponsorship, MemberContribution
from app.models.expense import Expense
from app.models.ledger import Transaction, Account
from app.models.mandal import Event
from app.utils.decorators import permission_required

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


def _active_event_id():
    event = Event.query.filter_by(is_active=True).first()
    return event.id if event else None


@reports_bp.route('/')
@login_required
@permission_required('report.view')
def index():
    active_event = Event.query.filter_by(is_active=True).first()
    event_id = active_event.id if active_event else None
    summary = LedgerService.get_ledger_summary(event_id=event_id)

    donation_query = Donation.query.filter_by(status='SUCCESS')
    sponsorship_query = Sponsorship.query
    expense_query = Expense.query.filter_by(status='PAID')
    if event_id:
        donation_query = donation_query.filter(Donation.event_id == event_id)
        sponsorship_query = sponsorship_query.filter(Sponsorship.event_id == event_id)
        expense_query = expense_query.filter(Expense.event_id == event_id)

    return render_template('reports/index.html', summary=summary,
        donations=donation_query.all(), sponsorships=sponsorship_query.all(),
        expenses=expense_query.all(), active_event=active_event)


@reports_bp.route('/reconciliation')
@login_required
@permission_required('report.view')
def reconciliation():
    account_id = request.args.get('account_id', type=int)
    accounts = Account.query.order_by(Account.is_active.desc(), Account.name.asc()).all()
    rows = LedgerService.get_account_reconciliation()
    if account_id:
        rows = [row for row in rows if row['account'].id == account_id]
    transactions = LedgerService.get_recent_transactions(limit=100, account_id=account_id, include_reversed=True)
    return render_template('reports/reconciliation.html', rows=rows, transactions=transactions,
        accounts=accounts, selected_account_id=account_id)


@reports_bp.route('/export/csv/<report_type>')
@login_required
@permission_required('report.export')
def export_csv(report_type):
    output = io.StringIO()
    writer = csv.writer(output)
    event_id = _active_event_id()

    if report_type == 'donations':
        writer.writerow(['Receipt No', 'Donation No', 'Donor Name', 'Amount', 'Payment Mode', 'Purpose', 'Status', 'Date'])
        query = Donation.query
        if event_id:
            query = query.filter(Donation.event_id == event_id)
        for d in query.all():
            writer.writerow([d.receipt_number or '', d.donation_number, d.donor_name, d.amount,
                d.payment_mode, d.purpose, d.status, d.created_at.strftime('%Y-%m-%d')])
        filename = 'Donations_Report.csv'

    elif report_type == 'expenses':
        writer.writerow(['Expense Ref', 'Title', 'Category', 'Vendor', 'Amount', 'Status', 'Expense Date', 'Bill No'])
        query = Expense.query
        if event_id:
            query = query.filter(Expense.event_id == event_id)
        for e in query.all():
            writer.writerow([e.expense_ref, e.title, e.category.name if e.category else '',
                e.vendor.name if e.vendor else '', e.amount, e.status,
                e.expense_date.strftime('%Y-%m-%d'), e.bill_number or ''])
        filename = 'Expenses_Report.csv'

    elif report_type == 'ledger':
        writer.writerow(['Txn Ref', 'Type', 'Amount', 'Payment Mode', 'Description', 'Module', 'Source ID', 'Account', 'External Ref', 'Reversed', 'Date'])
        query = Transaction.query
        if event_id:
            query = query.filter(Transaction.event_id == event_id)
        for t in query.order_by(Transaction.transaction_date.desc()).all():
            writer.writerow([t.transaction_ref, t.transaction_type, t.amount, t.payment_mode,
                t.description, t.source_module, t.source_id, t.account.name if t.account else '',
                t.external_ref or '', 'YES' if t.is_reversed else 'NO',
                t.transaction_date.strftime('%Y-%m-%d %H:%M')])
        filename = 'Central_Ledger_Report.csv'

    elif report_type == 'reconciliation':
        writer.writerow(['Account', 'Type', 'Opening Balance', 'Ledger Income', 'Ledger Expense', 'Expected Balance', 'Stored Balance', 'Difference', 'Balanced', 'Active'])
        for row in LedgerService.get_account_reconciliation():
            account = row['account']
            writer.writerow([account.name, account.account_type, row['opening_balance'], row['income'],
                row['expense'], row['expected_balance'], row['stored_balance'], row['difference'],
                'YES' if row['is_balanced'] else 'NO', 'YES' if account.is_active else 'NO'])
        filename = 'Ledger_Reconciliation_Report.csv'
    else:
        return 'Invalid report type', 400

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response
