import datetime
from decimal import Decimal
from app.extensions import db
from app.models.expense import Expense, Approval
from app.models.vendor import Vendor
from app.services.ledger_service import LedgerService
from app.services.audit_service import AuditService

class ExpenseService:
    @staticmethod
    def _generate_expense_ref():
        year = datetime.datetime.utcnow().year
        count = Expense.query.count() + 1
        return f"EXP-{year}-{count:04d}"

    @staticmethod
    def submit_expense(event_id, category_id, title, description, amount, expense_date, created_by_user,
                       vendor_id=None, bill_number=None, bill_date=None):
        """
        Creates and submits a new expense for approval. Initial status: SUBMITTED.
        """
        decimal_amount = Decimal(str(amount))
        if decimal_amount <= Decimal('0.00'):
            raise ValueError("Expense amount must be greater than zero.")

        exp_ref = ExpenseService._generate_expense_ref()
        expense = Expense(
            expense_ref=exp_ref,
            event_id=event_id,
            category_id=category_id,
            vendor_id=vendor_id,
            title=title,
            description=description,
            amount=decimal_amount,
            expense_date=expense_date,
            bill_number=bill_number,
            bill_date=bill_date,
            status='SUBMITTED',
            created_by_id=created_by_user.id
        )

        db.session.add(expense)
        db.session.commit()

        # Update vendor pending balance if vendor assigned
        if vendor_id:
            vendor = db.session.get(Vendor, vendor_id)
            if vendor:
                vendor.pending_amount += decimal_amount
                db.session.commit()

        approval_log = Approval(
            expense_id=expense.id,
            approver_id=created_by_user.id,
            action='SUBMIT',
            previous_status='NEW',
            new_status='SUBMITTED',
            comments='Expense submitted for review and approval.'
        )
        db.session.add(approval_log)
        db.session.commit()

        AuditService.log_action(
            action='CREATE',
            entity_type='EXPENSE',
            entity_id=expense.id,
            description=f"Submitted expense {exp_ref} ('{title}') for ₹{decimal_amount}"
        )

        return expense

    @staticmethod
    def approve_expense(expense_id, approver_user, comments=None):
        """
        Approves an expense. Prevents unauthorized self-approval for non-admin users. Status transitions to APPROVED.
        """
        expense = db.session.get(Expense, expense_id)
        if not expense:
            raise ValueError("Expense not found.")

        if expense.status not in ('SUBMITTED', 'UNDER_REVIEW'):
            raise ValueError(f"Cannot approve expense with status '{expense.status}'.")

        # Prevent self-approval for non-admin users
        if expense.created_by_id == approver_user.id and not approver_user.is_admin:
            raise ValueError("Self-approval is not allowed. Another authorized reviewer must approve this expense.")

        prev_status = expense.status
        expense.status = 'APPROVED'
        expense.approved_by_id = approver_user.id
        expense.approval_date = datetime.datetime.utcnow()

        approval_log = Approval(
            expense_id=expense.id,
            approver_id=approver_user.id,
            action='APPROVE',
            previous_status=prev_status,
            new_status='APPROVED',
            comments=comments or 'Expense approved.'
        )
        db.session.add(approval_log)
        db.session.commit()

        AuditService.log_action(
            action='APPROVE',
            entity_type='EXPENSE',
            entity_id=expense.id,
            description=f"Approved expense {expense.expense_ref} of ₹{expense.amount}"
        )

        return expense

    @staticmethod
    def reject_expense(expense_id, reviewer_user, rejection_reason):
        """
        Rejects an expense with reason. Status transitions to REJECTED.
        """
        expense = db.session.get(Expense, expense_id)
        if not expense:
            raise ValueError("Expense not found.")

        if expense.status in ('PAID', 'REJECTED'):
            raise ValueError(f"Cannot reject expense in status '{expense.status}'.")

        prev_status = expense.status
        expense.status = 'REJECTED'
        expense.rejection_reason = rejection_reason

        # Revert vendor pending balance if vendor assigned
        if expense.vendor_id:
            vendor = Vendor.query.get(expense.vendor_id)
            if vendor:
                vendor.pending_amount = max(Decimal('0.00'), vendor.pending_amount - expense.amount)

        approval_log = Approval(
            expense_id=expense.id,
            approver_id=reviewer_user.id,
            action='REJECT',
            previous_status=prev_status,
            new_status='REJECTED',
            comments=f"Rejected: {rejection_reason}"
        )
        db.session.add(approval_log)
        db.session.commit()

        AuditService.log_action(
            action='REJECT',
            entity_type='EXPENSE',
            entity_id=expense.id,
            description=f"Rejected expense {expense.expense_ref}. Reason: {rejection_reason}"
        )

        return expense

    @staticmethod
    def pay_expense(expense_id, payer_user, account_id, payment_mode, payment_ref=None):
        """
        Disburses payment for an approved expense, posts transaction to Central Ledger, and updates vendor figures.
        """
        expense = db.session.get(Expense, expense_id)
        if not expense:
            raise ValueError("Expense not found.")

        if expense.status != 'APPROVED':
            raise ValueError("Expense must be in APPROVED status before payment.")

        expense.status = 'PAID'
        expense.account_id = account_id
        expense.payment_mode = payment_mode
        expense.payment_ref = payment_ref
        expense.payment_date = datetime.datetime.utcnow()
        expense.paid_by_id = payer_user.id

        # Record in Central Ledger
        txn = LedgerService.record_expense(
            account_id=account_id,
            amount=expense.amount,
            description=f"Payment for Expense {expense.expense_ref}: {expense.title}",
            source_module='EXPENSE',
            source_id=expense.id,
            created_by_id=payer_user.id,
            payment_mode=payment_mode,
            external_ref=payment_ref,
            category_id=expense.category_id,
            event_id=expense.event_id
        )

        expense.transaction_id = txn.id

        # Update vendor balances
        if expense.vendor_id:
            vendor = Vendor.query.get(expense.vendor_id)
            if vendor:
                vendor.total_paid += expense.amount
                vendor.pending_amount = max(Decimal('0.00'), vendor.pending_amount - expense.amount)

        approval_log = Approval(
            expense_id=expense.id,
            approver_id=payer_user.id,
            action='PAY',
            previous_status='APPROVED',
            new_status='PAID',
            comments=f"Disbursed ₹{expense.amount} via {payment_mode} (Ref: {payment_ref})"
        )
        db.session.add(approval_log)
        db.session.commit()

        AuditService.log_action(
            action='PAY',
            entity_type='EXPENSE',
            entity_id=expense.id,
            description=f"Paid expense {expense.expense_ref} of ₹{expense.amount} via {payment_mode}"
        )

        return expense
