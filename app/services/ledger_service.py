import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import func

from app.extensions import db
from app.models.ledger import Account, Transaction
from app.models.mandal import FinancialYear
from app.services.audit_service import AuditService


class LedgerService:
    @staticmethod
    def _generate_txn_ref():
        timestamp = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        return f'TXN-{timestamp}'

    @staticmethod
    def _normalize_amount(amount):
        try:
            decimal_amount = Decimal(str(amount)).quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError('Amount must be a valid monetary value.')
        if decimal_amount <= Decimal('0.00'):
            raise ValueError('Amount must be greater than zero.')
        return decimal_amount

    @staticmethod
    def _lock_account(account_id):
        query = db.session.query(Account).filter(Account.id == account_id)
        try:
            bind = db.session.get_bind()
            if bind is not None and bind.dialect.name != 'sqlite':
                query = query.with_for_update()
        except Exception:
            pass
        account = query.first()
        if not account:
            raise ValueError('Invalid target Account ID.')
        if not account.is_active:
            raise ValueError('Target account is inactive.')
        return account

    @staticmethod
    def _ensure_not_duplicate(source_module, source_id, external_ref=None):
        if source_id is not None:
            existing = Transaction.query.filter(
                Transaction.source_module == source_module,
                Transaction.source_id == source_id,
                Transaction.is_reversed.is_(False),
            ).first()
            if existing is not None:
                raise ValueError('A ledger transaction already exists for this source record.')
        if external_ref:
            existing = Transaction.query.filter_by(external_ref=external_ref).first()
            if existing is not None:
                raise ValueError('A ledger transaction already exists for this external reference.')

    @staticmethod
    def _record(transaction_type, account_id, amount, description, source_module,
                source_id, created_by_id, payment_mode='CASH', external_ref=None,
                category_id=None, event_id=None, commit=True):
        decimal_amount = LedgerService._normalize_amount(amount)
        if not source_module:
            raise ValueError('source_module is required.')
        if not description:
            raise ValueError('description is required.')
        try:
            account = LedgerService._lock_account(account_id)
            LedgerService._ensure_not_duplicate(source_module, source_id, external_ref)
            transaction = Transaction(
                transaction_ref=LedgerService._generate_txn_ref(), event_id=event_id,
                account_id=account.id, category_id=category_id, transaction_type=transaction_type,
                amount=decimal_amount, payment_mode=payment_mode, external_ref=external_ref,
                description=description, source_module=source_module, source_id=source_id,
                created_by_id=created_by_id,
            )
            if transaction_type == 'INCOME':
                account.current_balance = (account.current_balance or Decimal('0.00')) + decimal_amount
            else:
                account.current_balance = (account.current_balance or Decimal('0.00')) - decimal_amount
            db.session.add(transaction)
            db.session.flush()
            AuditService.log_action(
                action='CREATE', entity_type='TRANSACTION', entity_id=transaction.id,
                description=f"Recorded {transaction_type} of ₹{decimal_amount} to account '{account.name}' ({transaction.transaction_ref})",
                commit=False,
            )
            if commit:
                db.session.commit()
            return transaction
        except Exception:
            if commit:
                db.session.rollback()
            raise

    @staticmethod
    def record_income(account_id, amount, description, source_module, source_id,
                      created_by_id, payment_mode='CASH', external_ref=None,
                      category_id=None, event_id=None, commit=True):
        return LedgerService._record('INCOME', account_id, amount, description, source_module, source_id,
                                     created_by_id, payment_mode, external_ref, category_id, event_id, commit)

    @staticmethod
    def record_expense(account_id, amount, description, source_module, source_id,
                       created_by_id, payment_mode='CASH', external_ref=None,
                       category_id=None, event_id=None, commit=True):
        return LedgerService._record('EXPENSE', account_id, amount, description, source_module, source_id,
                                     created_by_id, payment_mode, external_ref, category_id, event_id, commit)

    @staticmethod
    def reverse_transaction(transaction_id, reversed_by_user_id, reason):
        if not reason or not str(reason).strip():
            raise ValueError('A reversal reason is required.')
        try:
            txn_query = db.session.query(Transaction).filter(Transaction.id == transaction_id)
            try:
                bind = db.session.get_bind()
                if bind is not None and bind.dialect.name != 'sqlite':
                    txn_query = txn_query.with_for_update()
            except Exception:
                pass
            orig_txn = txn_query.first()
            if not orig_txn:
                raise ValueError('Transaction not found.')
            if orig_txn.is_reversed:
                raise ValueError('Transaction has already been reversed.')
            if orig_txn.transaction_type not in ('INCOME', 'EXPENSE'):
                raise ValueError('Only INCOME and EXPENSE transactions can be reversed.')
            account = LedgerService._lock_account(orig_txn.account_id)
            existing_reversal = Transaction.query.filter_by(external_ref=f'REVERSAL-OF-{orig_txn.transaction_ref}').first()
            if existing_reversal:
                raise ValueError('A reversal already exists for this transaction.')
            if orig_txn.transaction_type == 'INCOME':
                account.current_balance -= orig_txn.amount
            else:
                account.current_balance += orig_txn.amount
            reversal_txn = Transaction(
                transaction_ref=LedgerService._generate_txn_ref(), event_id=orig_txn.event_id,
                account_id=orig_txn.account_id, category_id=orig_txn.category_id, transaction_type='REVERSAL',
                amount=orig_txn.amount, payment_mode=orig_txn.payment_mode,
                external_ref=f'REVERSAL-OF-{orig_txn.transaction_ref}',
                description=f'Reversal of {orig_txn.transaction_ref}: {str(reason).strip()}',
                source_module=orig_txn.source_module, source_id=orig_txn.source_id,
                created_by_id=reversed_by_user_id,
            )
            orig_txn.is_reversed = True
            orig_txn.reversal_reason = str(reason).strip()
            db.session.add(reversal_txn)
            db.session.flush()
            orig_txn.reversed_by_txn_id = reversal_txn.id
            AuditService.log_action(
                action='REVERSE', entity_type='TRANSACTION', entity_id=orig_txn.id,
                description=f'Reversed transaction {orig_txn.transaction_ref} with {reversal_txn.transaction_ref}. Reason: {orig_txn.reversal_reason}',
                commit=False,
            )
            db.session.commit()
            return reversal_txn
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def get_ledger_summary(event_id=None):
        fy = FinancialYear.query.filter_by(is_active=True).first()
        opening_balance = fy.opening_balance if fy else Decimal('0.00')
        query = Transaction.query.filter_by(is_reversed=False)
        if event_id:
            query = query.filter_by(event_id=event_id)
        totals = query.with_entities(
            func.coalesce(func.sum(Transaction.amount).filter(Transaction.transaction_type == 'INCOME'), 0),
            func.coalesce(func.sum(Transaction.amount).filter(Transaction.transaction_type == 'EXPENSE'), 0),
        ).first()
        total_income = Decimal(str(totals[0])).quantize(Decimal('0.01'))
        total_expense = Decimal(str(totals[1])).quantize(Decimal('0.01'))
        return {
            'opening_balance': opening_balance,
            'total_income': total_income,
            'total_expense': total_expense,
            'current_balance': opening_balance + total_income - total_expense,
            'transaction_count': query.count(),
        }
