from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.models.ledger import Account
from app.services.account_balance_service import AccountBalanceService

account_balances_bp = Blueprint('account_balances', __name__, url_prefix='/finance-controls/accounts')


def finance_manage_allowed():
    return current_user.is_admin or current_user.has_permission('finance.manage')


@account_balances_bp.get('/reconciliation')
@login_required
def account_reconciliation():
    if not (current_user.is_admin or current_user.has_permission('finance.view')):
        return jsonify({'error': 'Financial permission required.'}), 403
    from app.services.ledger_service import LedgerService
    return jsonify([
        {
            'account_id': row['account'].id,
            'account_name': row['account'].name,
            'account_type': row['account'].account_type,
            'opening_balance': str(row['opening_balance']),
            'stored_balance': str(row['stored_balance']),
            'expected_balance': str(row['expected_balance']),
            'difference': str(row['difference']),
            'is_balanced': row['is_balanced'],
        }
        for row in LedgerService.get_account_reconciliation()
    ])


@account_balances_bp.post('/<int:account_id>/opening-balance')
@login_required
def adjust_opening_balance(account_id):
    if not finance_manage_allowed():
        return jsonify({'error': 'Financial permission required.'}), 403
    payload = request.get_json(silent=True) or request.form
    try:
        account = AccountBalanceService.adjust_opening_balance(
            account_id,
            payload.get('opening_balance'),
            current_user,
            payload.get('reason', ''),
        )
        return jsonify({
            'ok': True,
            'account_id': account.id,
            'account_name': account.name,
            'opening_balance': str(account.opening_balance),
            'current_balance': str(account.current_balance),
        })
    except (ValueError, TypeError) as exc:
        return jsonify({'error': str(exc)}), 400
