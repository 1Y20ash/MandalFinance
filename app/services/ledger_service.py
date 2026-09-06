import datetime
from decimal import Decimal
from app.extensions import db
from app.models.ledger import Account, Transaction, TransactionCategory
from app.models.mandal import FinancialYear
from app.services.audit_service import AuditService

class LedgerService:
    @staticmethod
    def _generate_txn_ref():
        now_str = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        count = Transaction.query.count() + 1
        return f"TXN-{now_str}-{count:04d}"

    @staticmethod
    def record_income(account_id, amount, description, source_module, source_id, created_by_id, payment_mode='CASH', external_ref=None, category_id=None, event_id=None):
        """
        Records an INCOME transaction in the central ledger with Decimal precision and updates account balance.
        """
        decimal_amount = Decimal(str(amount))
        if decimal_amount <= Decimal('0.00'):
            raise ValueError("Income amount must be greater than zero.")

        account = db.session.get(Account, account_id)
        if not account:
            raise ValueError("Invalid target Account ID.")

        txn_ref = LedgerService._generate_txn_ref()
        transaction = Transaction(
            transaction_ref=txn_ref,
            event_id=event_id,
            account_id=account_id,
            category_id=category_id,
            transaction_type='INCOME',
            amount=decimal_amount,
            payment_mode=payment_mode,
            external_ref=external_ref,
            description=description,
            source_module=source_module,
            source_id=source_id,
            created_by_id=created_by_id
        )

        account.current_balance += decimal_amount
        db.session.add(transaction)
        db.session.commit()

        AuditService.log_action(
            action='CREATE',
            entity_type='TRANSACTION',
            entity_id=transaction.id,
            description=f"Recorded INCOME of ₹{decimal_amount} to account '{account.name}' ({txn_ref})"
        )

        return transaction

    @staticmethod
    def record_expense(account_id, amount, description, source_module, source_id, created_by_id, payment_mode='CASH', external_ref=None, category_id=None, event_id=None):
        """
        Records an EXPENSE transaction in the central ledger with Decimal precision and updates account balance.
        """
        decimal_amount = Decimal(str(amount))
        if decimal_amount <= Decimal('0.00'):
            raise ValueError("Expense amount must be greater than zero.")

        account = db.session.get(Account, account_id)
        if not account:
            raise ValueError("Invalid target Account ID.")

        txn_ref = LedgerService._generate_txn_ref()
        transaction = Transaction(
            transaction_ref=txn_ref,
            event_id=event_id,
            account_id=account_id,
            category_id=category_id,
            transaction_type='EXPENSE',
            amount=decimal_amount,
            payment_mode=payment_mode,
            external_ref=external_ref,
            description=description,
            source_module=source_module,
            source_id=source_id,
            created_by_id=created_by_id
        )

        account.current_balance -= decimal_amount
        db.session.add(transaction)
        db.session.commit()

        AuditService.log_action(
            action='CREATE',
            entity_type='TRANSACTION',
            entity_id=transaction.id,
            description=f"Recorded EXPENSE of ₹{decimal_amount} from account '{account.name}' ({txn_ref})"
        )

        return transaction

    @staticmethod
    def reverse_transaction(transaction_id, reversed_by_user_id, reason):
        """
        Reverses a finalized transaction by creating an offsetting REVERSAL transaction. Never deletes records.
        """
        orig_txn = db.session.get(Transaction, transaction_id)
        if not orig_txn:
            raise ValueError("Transaction not found.")
        if orig_txn.is_reversed:
            raise ValueError("Transaction has already been reversed.")

        account = db.session.get(Account, orig_txn.account_id)
        reversal_ref = LedgerService._generate_txn_ref()
        
        # Offsetting movement
        if orig_txn.transaction_type == 'INCOME':
            account.current_balance -= orig_txn.amount
        elif orig_txn.transaction_type == 'EXPENSE':
            account.current_balance += orig_txn.amount

        reversal_txn = Transaction(
            transaction_ref=reversal_ref,
            event_id=orig_txn.event_id,
            account_id=orig_txn.account_id,
            category_id=orig_txn.category_id,
            transaction_type='REVERSAL',
            amount=orig_txn.amount,
            payment_mode=orig_txn.payment_mode,
            external_ref=f"REVERSAL-OF-{orig_txn.transaction_ref}",
            description=f"Reversal of {orig_txn.transaction_ref}: {reason}",
            source_module=orig_txn.source_module,
            source_id=orig_txn.source_id,
            created_by_id=reversed_by_user_id
        )

        orig_txn.is_reversed = True
        orig_txn.reversal_reason = reason

        db.session.add(reversal_txn)
        db.session.commit()

        orig_txn.reversed_by_txn_id = reversal_txn.id
        db.session.commit()

        AuditService.log_action(
            action='REVERSE',
            entity_type='TRANSACTION',
            entity_id=orig_txn.id,
            description=f"Reversed transaction {orig_txn.transaction_ref} with Reversal Txn {reversal_ref}. Reason: {reason}"
        )

        return reversal_txn

    @staticmethod
    def get_ledger_summary(event_id=None):
        """
        Calculates Opening Balance + Total Income - Total Expenses = Current Balance.
        Returns dictionary of Decimal values.
        """
        fy = FinancialYear.query.filter_by(is_active=True).first()
        opening_balance = fy.opening_balance if fy else Decimal('0.00')

        query = Transaction.query.filter_by(is_reversed=False)
        if event_id:
            query = query.filter_by(event_id=event_id)

        all_txns = query.all()

        total_income = Decimal('0.00')
        total_expense = Decimal('0.00')

        for txn in all_txns:
            if txn.transaction_type == 'INCOME':
                total_income += txn.amount
            elif txn.transaction_type == 'EXPENSE':
                total_expense += txn.amount

        current_balance = opening_balance + total_income - total_expense

        return {
            'opening_balance': opening_balance,
            'total_income': total_income,
            'total_expense': total_expense,
            'current_balance': current_balance,
            'transaction_count': len(all_txns)
        }
