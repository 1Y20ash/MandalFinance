import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from app.extensions import db
from app.models.ledger import Account, Transaction
from app.models.mandal import FinancialYear
from app.services.audit_service import AuditService

MONEY_ZERO = Decimal('0.00')


class LedgerService:
    @staticmethod
    def _generate_txn_ref():
        return f"TXN-{datetime.datetime.utcnow().year}-{uuid4().hex.upper()}"

    @staticmethod
    def _normalize_amount(amount):
        try:
            decimal_amount = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError('Amount must be a valid monetary value.')
        if decimal_amount <= MONEY_ZERO:
            raise ValueError('Amount must be greater than zero.')
        return decimal_amount

    @staticmethod
    def _to_money(value):
        if value is None:
            return MONEY_ZERO
        return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

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
                account.current_balance = LedgerService._to_money(account.current_balance) + decimal_amount
            elif transaction_type == 'EXPENSE':
                account.current_balance = LedgerService._to_money(account.current_balance) - decimal_amount
            else:
                raise ValueError('Unsupported ledger transaction type.')
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
    def reverse_transaction(transaction_id, reversed_by_user_id, reason, commit=True):
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
            reversal_ref = f'REVERSAL-OF-{orig_txn.transaction_ref}'
            if Transaction.query.filter_by(external_ref=reversal_ref).first():
                raise ValueError('A reversal already exists for this transaction.')

            if orig_txn.transaction_type == 'INCOME':
                account.current_balance = LedgerService._to_money(account.current_balance) - orig_txn.amount
            else:
                account.current_balance = LedgerService._to_money(account.current_balance) + orig_txn.amount

            reversal_txn = Transaction(
                transaction_ref=LedgerService._generate_txn_ref(), event_id=orig_txn.event_id,
                account_id=orig_txn.account_id, category_id=orig_txn.category_id,
                transaction_type='REVERSAL', amount=orig_txn.amount,
                payment_mode=orig_txn.payment_mode, external_ref=reversal_ref,
                description=f'Reversal of {orig_txn.transaction_ref}: {str(reason).strip()}',
                source_module='REVERSAL', source_id=None, created_by_id=reversed_by_user_id,
            )
            db.session.add(reversal_txn)
            db.session.flush()
            orig_txn.is_reversed = True
            orig_txn.reversal_reason = str(reason).strip()
            orig_txn.reversed_by_txn_id = reversal_txn.id
            db.session.flush()
            AuditService.log_action(
                action='REVERSE', entity_type='TRANSACTION', entity_id=orig_txn.id,
                description=f'Reversed transaction {orig_txn.transaction_ref} with {reversal_txn.transaction_ref}. Reason: {orig_txn.reversal_reason}',
                commit=False,
            )
            if commit:
                db.session.commit()
            return reversal_txn
        except Exception:
            if commit:
                db.session.rollback()
            raise

    @staticmethod
    def _effective_transaction_totals(query):
        income = MONEY_ZERO
        expense = MONEY_ZERO
        transactions = query.all()
        for txn in transactions:
            amount = LedgerService._to_money(txn.amount)
            if txn.transaction_type == 'INCOME':
                income += amount
            elif txn.transaction_type == 'EXPENSE':
                expense += amount
            elif txn.transaction_type == 'REVERSAL':
                original = Transaction.query.filter_by(reversed_by_txn_id=txn.id).first()
                if original and original.transaction_type == 'INCOME':
                    income -= amount
                elif original and original.transaction_type == 'EXPENSE':
                    expense -= amount
        return income, expense

    @staticmethod
    def get_ledger_summary(event_id=None):
        fy = FinancialYear.query.filter_by(is_active=True).first()
        opening_balance = LedgerService._to_money(fy.opening_balance if fy else MONEY_ZERO)
        query = Transaction.query
        if event_id:
            query = query.filter_by(event_id=event_id)
        total_income, total_expense = LedgerService._effective_transaction_totals(query)
        effective_count = query.filter(
            ((Transaction.transaction_type.in_(['INCOME', 'EXPENSE'])) & Transaction.is_reversed.is_(False)) |
            (Transaction.transaction_type == 'REVERSAL')
        ).count()
        return {
            'opening_balance': opening_balance,
            'total_income': total_income,
            'total_expense': total_expense,
            'current_balance': opening_balance + total_income - total_expense,
            'transaction_count': effective_count,
        }

    @staticmethod
    def get_account_reconciliation():
        accounts = Account.query.order_by(Account.is_active.desc(), Account.name.asc()).all()
        results = []
        for account in accounts:
            opening = LedgerService._to_money(account.opening_balance)
            query = Transaction.query.filter(Transaction.account_id == account.id)
            income, expense = LedgerService._effective_transaction_totals(query)
            expected = opening + income - expense
            stored = LedgerService._to_money(account.current_balance)
            difference = stored - expected
            results.append({
                'account': account, 'opening_balance': opening, 'income': income,
                'expense': expense, 'expected_balance': expected, 'stored_balance': stored,
                'difference': difference, 'is_balanced': difference == MONEY_ZERO,
            })
        return results

    @staticmethod
    def get_recent_transactions(limit=100, account_id=None, event_id=None, include_reversed=True):
        limit = max(1, min(int(limit), 500))
        query = Transaction.query
        if account_id:
            query = query.filter_by(account_id=account_id)
        if event_id:
            query = query.filter_by(event_id=event_id)
        if not include_reversed:
            query = query.filter_by(is_reversed=False)
        return query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).limit(limit).all()
