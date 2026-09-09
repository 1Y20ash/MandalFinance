from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from app.extensions import db
from app.models.income import Donation
from app.models.ledger import TransactionCategory, Transaction
from app.services.audit_service import AuditService
from app.services.ledger_service import LedgerService
from app.services.financial_controls_service import FinancialControlsService


class DonationService:
    """Business logic for donations and their central-ledger postings."""
    OFFLINE_MODES = {'CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE'}

    @staticmethod
    def _generate_donation_number():
        return f"DON-{datetime.utcnow().year}-{uuid4().hex[:10].upper()}"

    @staticmethod
    def _generate_receipt_number():
        return f"REC-{datetime.utcnow().year}-{uuid4().hex[:10].upper()}"

    @staticmethod
    def _normalize_amount(amount):
        try:
            value = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError('Donation amount must be a valid number.')
        if value <= Decimal('0.00'):
            raise ValueError('Donation amount must be greater than zero.')
        return value

    @staticmethod
    def _validate_common(event_id, donor_name, payment_mode):
        if not event_id:
            raise ValueError('A target event is required.')
        if not donor_name or len(donor_name.strip()) < 2:
            raise ValueError('Donor name must contain at least 2 characters.')
        if payment_mode not in DonationService.OFFLINE_MODES:
            raise ValueError('Invalid offline donation payment mode.')

    @staticmethod
    def _donation_category_id():
        category = TransactionCategory.query.filter_by(
            name='Donations', category_type='income'
        ).first()
        if not category:
            category = TransactionCategory(
                name='Donations',
                category_type='income',
                description='Donation income',
            )
            db.session.add(category)
            db.session.flush()
        return category.id

    @staticmethod
    def record_offline_donation(
        event_id, donor_name, amount, payment_mode, account_id, created_by_id,
        donor_phone=None, donor_email=None, donor_address=None, pan_number=None,
        purpose='General Donation', transaction_ref=None, notes=None,
    ):
        DonationService._validate_common(event_id, donor_name, payment_mode)
        decimal_amount = DonationService._normalize_amount(amount)
        if payment_mode in {'UPI', 'BANK_TRANSFER', 'CHEQUE'} and not transaction_ref:
            raise ValueError('Transaction reference is required for this payment mode.')
        if transaction_ref and Transaction.query.filter_by(external_ref=transaction_ref).first():
            raise ValueError('This external payment reference is already recorded.')

        donation = Donation(
            donation_number=DonationService._generate_donation_number(),
            event_id=event_id,
            donor_name=donor_name.strip(),
            donor_phone=donor_phone or None,
            donor_email=donor_email or None,
            donor_address=donor_address or None,
            pan_number=pan_number or None,
            amount=decimal_amount,
            purpose=(purpose or 'General Donation').strip(),
            donation_type='OFFLINE',
            payment_mode=payment_mode,
            status='SUCCESS',
            transaction_ref=transaction_ref or None,
            receipt_number=DonationService._generate_receipt_number(),
            receipt_generated_at=datetime.utcnow(),
            notes=notes or None,
            created_by_id=created_by_id,
        )
        try:
            db.session.add(donation)
            db.session.flush()
            evidence = FinancialControlsService.check_evidence('DONATION', donation.id, decimal_amount)
            if not evidence['complete']:
                missing = sorted({c for failure in evidence['failures'] for c in failure['missing']})
                raise ValueError('Required evidence is missing before donation posting: ' + ', '.join(missing))
            LedgerService.record_income(
                account_id, decimal_amount,
                f"Donation {donation.donation_number} ({donation.receipt_number}) from {donation.donor_name}",
                'DONATION', donation.id, created_by_id,
                payment_mode=payment_mode,
                external_ref=transaction_ref,
                category_id=DonationService._donation_category_id(),
                event_id=event_id,
                commit=False,
            )
            AuditService.log_action(
                'CREATE', 'DONATION', donation.id,
                f"Recorded offline donation {donation.donation_number} of ₹{decimal_amount} for {donation.donor_name}",
                commit=False,
            )
            db.session.commit()
            return donation
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def confirm_online_donation(
        donation_id,
        gateway_payment_id,
        gateway_signature=None,
        account_id=None,
        verified_order_id=None,
        verified_amount_paise=None,
        verified_currency='INR',
        verified_status='captured',
        commit=True,
    ):
        donation = db.session.get(Donation, donation_id)
        if not donation:
            raise ValueError('Donation not found.')
        if donation.status == 'SUCCESS':
            return donation
        if donation.status in {'FAILED', 'CANCELLED'}:
            raise ValueError('A failed or cancelled donation cannot be confirmed.')
        if not gateway_payment_id or not verified_order_id:
            raise ValueError('Verified gateway payment identity is required.')
        if donation.gateway_order_id != verified_order_id:
            raise ValueError('Gateway payment does not belong to the stored donation order.')
        if verified_currency != 'INR':
            raise ValueError('Only INR payments can be recorded.')
        expected_paise = int(Decimal(str(donation.amount)) * 100)
        if verified_amount_paise != expected_paise:
            raise ValueError('Gateway payment amount does not match the donation amount.')
        if verified_status != 'captured':
            raise ValueError('Gateway payment is not captured.')
        if Transaction.query.filter_by(external_ref=gateway_payment_id).first():
            raise ValueError('This gateway payment is already recorded.')

        try:
            donation.status = 'SUCCESS'
            donation.gateway_payment_id = gateway_payment_id
            if gateway_signature:
                donation.gateway_signature = gateway_signature
            donation.receipt_number = DonationService._generate_receipt_number()
            donation.receipt_generated_at = datetime.utcnow()
            db.session.flush()

            evidence = FinancialControlsService.check_evidence('DONATION', donation.id, donation.amount)
            if not evidence['complete']:
                missing = sorted({c for failure in evidence['failures'] for c in failure['missing']})
                raise ValueError('Required evidence is missing before donation confirmation: ' + ', '.join(missing))

            LedgerService.record_income(
                account_id=account_id,
                amount=donation.amount,
                description=f"Online Donation {donation.donation_number} ({donation.receipt_number}) from {donation.donor_name}",
                source_module='DONATION',
                source_id=donation.id,
                created_by_id=donation.created_by_id,
                payment_mode='GATEWAY',
                external_ref=gateway_payment_id,
                category_id=DonationService._donation_category_id(),
                event_id=donation.event_id,
                commit=False,
            )
            AuditService.log_action(
                'VERIFY', 'DONATION', donation.id,
                f"Confirmed online donation {donation.donation_number} of ₹{donation.amount}",
                commit=False,
            )
            if commit:
                db.session.commit()
            return donation
        except Exception:
            db.session.rollback()
            raise
