from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from app.extensions import db
from app.models.income_entry import Income
from app.models.ledger import TransactionCategory
from app.services.audit_service import AuditService
from app.services.ledger_service import LedgerService


class IncomeService:
    """Atomic business logic for non-donation income and central-ledger posting."""

    PAYMENT_MODES = {'CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE'}

    @staticmethod
    def _generate_income_ref():
        return f"INC-{datetime.utcnow().year}-{uuid4().hex[:10].upper()}"

    @staticmethod
    def _normalize_amount(amount):
        try:
            value = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError('Income amount must be a valid number.')
        if value <= Decimal('0.00'):
            raise ValueError('Income amount must be greater than zero.')
        return value

    @staticmethod
    def _validate(event_id, category_id, account_id, source_name, description, payment_mode, transaction_ref):
        if not event_id:
            raise ValueError('A target event is required.')
        if not category_id:
            raise ValueError('An income category is required.')
        if not account_id:
            raise ValueError('A receiving account is required.')
        if not source_name or len(source_name.strip()) < 2:
            raise ValueError('Income source must contain at least 2 characters.')
        if not description or len(description.strip()) < 3:
            raise ValueError('Income description must contain at least 3 characters.')
        if payment_mode not in IncomeService.PAYMENT_MODES:
            raise ValueError('Invalid income payment mode.')
        if payment_mode != 'CASH' and not transaction_ref:
            raise ValueError('Transaction reference is required for this payment mode.')

        category = db.session.get(TransactionCategory, category_id)
        if not category or category.category_type != 'income':
            raise ValueError('Selected category must be an active income category.')

    @staticmethod
    def record_income(event_id, category_id, account_id, source_name, description, amount, income_date,
                      payment_mode, created_by_id, transaction_ref=None, notes=None):
        decimal_amount = IncomeService._normalize_amount(amount)
        IncomeService._validate(event_id, category_id, account_id, source_name, description,
                                payment_mode, transaction_ref)

        if transaction_ref:
            duplicate = Income.query.filter_by(transaction_ref=transaction_ref).first()
            if duplicate:
                raise ValueError('An income entry with this transaction reference already exists.')

        income_ref = IncomeService._generate_income_ref()

        try:
            # The income row requires transaction_id, while the ledger transaction
            # needs the income row's ID as source_id. Create the ledger row first,
            # then create the income row already linked to that transaction. Once
            # the income gets its ID, backfill txn.source_id before the atomic commit.
            txn = LedgerService.record_income(
                account_id=account_id, amount=decimal_amount,
                description=f"Income {income_ref}: {source_name.strip()}",
                source_module='INCOME', source_id=None, created_by_id=created_by_id,
                payment_mode=payment_mode, external_ref=transaction_ref,
                category_id=category_id, event_id=event_id, commit=False,
            )

            income = Income(
                income_ref=income_ref, event_id=event_id, category_id=category_id,
                account_id=account_id, source_name=source_name.strip(), description=description.strip(),
                amount=decimal_amount, income_date=income_date, payment_mode=payment_mode,
                transaction_ref=transaction_ref or None, notes=notes or None,
                transaction_id=txn.id, created_by_id=created_by_id,
            )
            db.session.add(income)
            db.session.flush()

            txn.source_id = income.id

            AuditService.log_action(
                action='CREATE', entity_type='INCOME', entity_id=income.id,
                description=f"Recorded income {income.income_ref} of ₹{decimal_amount} from {income.source_name}",
                commit=False,
            )
            db.session.commit()
            return income
        except Exception:
            db.session.rollback()
            raise
