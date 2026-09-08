from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.extensions import db
from app.models.controls import ReconciliationRecord
from app.models.ledger import Account
from app.services.audit_service import AuditService


class AccountBalanceService:
    @staticmethod
    def adjust_opening_balance(account_id, new_opening_balance, user, reason):
        if not reason or not str(reason).strip():
            raise ValueError('A reason is required when adjusting an opening balance.')
        try:
            new_balance = Decimal(str(new_opening_balance)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError('Opening balance must be a valid monetary value.')
        if new_balance < Decimal('0.00'):
            raise ValueError('Opening balance cannot be negative.')

        query = db.session.query(Account).filter(Account.id == account_id)
        try:
            if db.session.get_bind().dialect.name != 'sqlite':
                query = query.with_for_update()
        except Exception:
            pass
        account = query.first()
        if not account:
            raise ValueError('Account not found.')
        if not account.is_active:
            raise ValueError('Inactive accounts cannot have their opening balance adjusted.')

        # A resolved reconciliation is an accountability checkpoint. Changing the
        # opening balance afterwards would invalidate that historical checkpoint.
        if ReconciliationRecord.query.filter_by(account_id=account.id, status='RESOLVED').first():
            raise ValueError('Opening balance cannot be changed after a reconciliation for this account has been resolved.')

        old_balance = Decimal(str(account.opening_balance or '0.00')).quantize(Decimal('0.01'))
        if new_balance == old_balance:
            raise ValueError('The new opening balance is the same as the current balance.')

        delta = new_balance - old_balance
        current = Decimal(str(account.current_balance or '0.00')).quantize(Decimal('0.01'))
        account.opening_balance = new_balance
        account.current_balance = current + delta
        db.session.flush()

        AuditService.log_action(
            'OPENING_BALANCE_ADJUST',
            'ACCOUNT',
            account.id,
            f"Adjusted account '{account.name}' opening balance from ₹{old_balance} to ₹{new_balance}. "
            f"Current balance changed by ₹{delta}. Reason: {str(reason).strip()}",
            commit=False,
        )
        db.session.commit()
        return account
