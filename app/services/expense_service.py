from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from app.extensions import db
from app.models.expense import Expense, Approval, ExpenseCategory
from app.models.vendor import Vendor
from app.models.ledger import Account
from app.models.mandal import Event
from app.services.audit_service import AuditService
from app.services.ledger_service import LedgerService
from app.services.financial_controls_service import FinancialControlsService


class ExpenseService:
    """Business logic for expenses; actual disbursement is posted to the central ledger."""

    PAYMENT_MODES = {'CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE'}
    SUBMIT_STATUSES = {'SUBMITTED'}

    @staticmethod
    def _generate_expense_ref():
        return f"EXP-{datetime.utcnow().year}-{uuid4().hex[:10].upper()}"

    @staticmethod
    def _normalize_amount(amount):
        try:
            value = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError('Expense amount must be a valid number.')
        if value <= Decimal('0.00'):
            raise ValueError('Expense amount must be greater than zero.')
        return value

    @staticmethod
    def _validate_submission(event_id, category_id, title, description, amount, expense_date,
                             created_by_user, vendor_id=None, bill_date=None):
        if not event_id:
            raise ValueError('A target event is required.')
        if not category_id:
            raise ValueError('An expense category is required.')
        if not title or len(title.strip()) < 2:
            raise ValueError('Expense title must contain at least 2 characters.')
        if not description or len(description.strip()) < 3:
            raise ValueError('Expense description must contain at least 3 characters.')
        if not expense_date:
            raise ValueError('Expense date is required.')
        if not created_by_user or not getattr(created_by_user, 'id', None):
            raise ValueError('A valid creator is required.')

        event = db.session.get(Event, event_id)
        if not event:
            raise ValueError('Target event was not found.')
        event.assert_editable()

        category = db.session.get(ExpenseCategory, category_id)
        if not category or not category.is_active:
            raise ValueError('Selected expense category is not active.')

        if vendor_id is not None:
            vendor = db.session.get(Vendor, vendor_id)
            if not vendor or not vendor.is_active:
                raise ValueError('Selected vendor is not active.')

        if bill_date and bill_date > expense_date:
            raise ValueError('Bill date cannot be later than the expense date.')

    @staticmethod
    def submit_expense(event_id, category_id, title, description, amount, expense_date, created_by_user,
                       vendor_id=None, bill_number=None, bill_date=None):
        """Create a submitted expense atomically; no money leaves an account until payment is posted."""
        decimal_amount = ExpenseService._normalize_amount(amount)
        ExpenseService._validate_submission(
            event_id, category_id, title, description, decimal_amount, expense_date,
            created_by_user, vendor_id, bill_date,
        )

        expense = Expense(
            expense_ref=ExpenseService._generate_expense_ref(),
            event_id=event_id,
            category_id=category_id,
            vendor_id=vendor_id,
            title=title.strip(),
            description=description.strip(),
            amount=decimal_amount,
            expense_date=expense_date,
            bill_number=bill_number.strip() if bill_number else None,
            bill_date=bill_date,
            status='SUBMITTED',
            created_by_id=created_by_user.id,
        )

        try:
            db.session.add(expense)
            db.session.flush()

            if vendor_id:
                vendor = db.session.get(Vendor, vendor_id)
                vendor.pending_amount += decimal_amount

            db.session.add(Approval(
                expense_id=expense.id,
                approver_id=created_by_user.id,
                action='SUBMIT',
                previous_status='NEW',
                new_status='SUBMITTED',
                comments='Expense submitted for review and approval.',
            ))
            AuditService.log_action(
                action='CREATE', entity_type='EXPENSE', entity_id=expense.id,
                description=f"Submitted expense {expense.expense_ref} ('{expense.title}') for ₹{decimal_amount}",
                commit=False,
            )
            db.session.commit()
            return expense
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def approve_expense(expense_id, approver_user, comments=None):
        expense = db.session.get(Expense, expense_id)
        if not expense:
            raise ValueError('Expense not found.')
        if expense.status not in ('SUBMITTED', 'UNDER_REVIEW'):
            raise ValueError(f"Cannot approve expense with status '{expense.status}'.")
        if expense.created_by_id == approver_user.id:
            raise ValueError('Self-approval is not allowed. Another authorized reviewer must approve this expense.')
        event = db.session.get(Event, expense.event_id)
        if not event:
            raise ValueError('Expense event was not found.')
        event.assert_editable()

        previous_status = expense.status
        try:
            expense.status = 'APPROVED'
            expense.approved_by_id = approver_user.id
            expense.approval_date = datetime.utcnow()
            db.session.add(Approval(
                expense_id=expense.id, approver_id=approver_user.id, action='APPROVE',
                previous_status=previous_status, new_status='APPROVED', comments=comments or 'Expense approved.',
            ))
            AuditService.log_action(
                action='APPROVE', entity_type='EXPENSE', entity_id=expense.id,
                description=f'Approved expense {expense.expense_ref} of ₹{expense.amount}', commit=False,
            )
            db.session.commit()
            return expense
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def reject_expense(expense_id, reviewer_user, rejection_reason):
        expense = db.session.get(Expense, expense_id)
        if not expense:
            raise ValueError('Expense not found.')
        if expense.status in ('PAID', 'REJECTED'):
            raise ValueError(f"Cannot reject expense in status '{expense.status}'.")
        if not rejection_reason or len(rejection_reason.strip()) < 3:
            raise ValueError('A meaningful rejection reason is required.')
        if expense.created_by_id == reviewer_user.id:
            raise ValueError('Self-review is not allowed. Another authorized reviewer must reject this expense.')
        event = db.session.get(Event, expense.event_id)
        if not event:
            raise ValueError('Expense event was not found.')
        event.assert_editable()

        previous_status = expense.status
        try:
            expense.status = 'REJECTED'
            expense.rejection_reason = rejection_reason.strip()
            if expense.vendor_id:
                vendor = db.session.get(Vendor, expense.vendor_id)
                if vendor:
                    vendor.pending_amount = max(Decimal('0.00'), vendor.pending_amount - expense.amount)
            db.session.add(Approval(
                expense_id=expense.id, approver_id=reviewer_user.id, action='REJECT',
                previous_status=previous_status, new_status='REJECTED',
                comments=f'Rejected: {rejection_reason.strip()}',
            ))
            AuditService.log_action(
                action='REJECT', entity_type='EXPENSE', entity_id=expense.id,
                description=f'Rejected expense {expense.expense_ref}. Reason: {rejection_reason.strip()}',
                commit=False,
            )
            db.session.commit()
            return expense
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def pay_expense(expense_id, payer_user, account_id, payment_mode, payment_ref=None):
        """Pay an approved expense atomically and post the disbursement to the central ledger."""
        expense = db.session.get(Expense, expense_id)
        if not expense:
            raise ValueError('Expense not found.')
        if expense.status != 'APPROVED':
            raise ValueError('Expense must be in APPROVED status before payment.')
        if payment_mode not in ExpenseService.PAYMENT_MODES:
            raise ValueError('Invalid expense payment mode.')
        if payment_mode != 'CASH' and not payment_ref:
            raise ValueError('Payment reference is required for this payment mode.')
        event = db.session.get(Event, expense.event_id)
        if not event:
            raise ValueError('Expense event was not found.')
        event.assert_editable()

        evidence = FinancialControlsService.check_evidence('EXPENSE', expense.id, expense.amount)
        if not evidence['complete']:
            missing = sorted({category for failure in evidence['failures'] for category in failure['missing']})
            raise ValueError(
                'Required evidence is missing before payment: ' + ', '.join(missing)
            )

        account = db.session.get(Account, account_id)
        if not account or not account.is_active:
            raise ValueError('Selected payment account is not active.')

        if payment_ref:
            duplicate = Expense.query.filter(
                Expense.payment_ref == payment_ref,
                Expense.id != expense.id,
            ).first()
            if duplicate:
                raise ValueError('An expense with this payment reference already exists.')

        try:
            txn = LedgerService.record_expense(
                account_id=account_id, amount=expense.amount,
                description=f'Payment for Expense {expense.expense_ref}: {expense.title}',
                source_module='EXPENSE', source_id=expense.id, created_by_id=payer_user.id,
                payment_mode=payment_mode, external_ref=payment_ref,
                category_id=None, event_id=expense.event_id, commit=False,
            )
            expense.status = 'PAID'
            expense.account_id = account_id
            expense.payment_mode = payment_mode
            expense.payment_ref = payment_ref or None
            expense.payment_date = datetime.utcnow()
            expense.paid_by_id = payer_user.id
            expense.transaction_id = txn.id

            if expense.vendor_id:
                vendor = db.session.get(Vendor, expense.vendor_id)
                if vendor:
                    vendor.total_paid += expense.amount
                    vendor.pending_amount = max(Decimal('0.00'), vendor.pending_amount - expense.amount)

            db.session.add(Approval(
                expense_id=expense.id, approver_id=payer_user.id, action='PAY',
                previous_status='APPROVED', new_status='PAID',
                comments=f'Disbursed ₹{expense.amount} via {payment_mode} (Ref: {payment_ref or "N/A"})',
            ))
            AuditService.log_action(
                action='PAY', entity_type='EXPENSE', entity_id=expense.id,
                description=f'Paid expense {expense.expense_ref} of ₹{expense.amount} via {payment_mode}',
                commit=False,
            )
            db.session.commit()
            return expense
        except Exception:
            db.session.rollback()
            raise
